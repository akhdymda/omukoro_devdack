import openai
import logging
from typing import List, Dict, Tuple
from app.config import settings
import asyncio

logger = logging.getLogger(__name__)

class SimilarityService:
    """要約テキストの類似度計算サービス"""
    
    def __init__(self):
        self.client = openai.AsyncOpenAI(api_key=settings.openai_api_key)
    
    async def find_similar_cases(
        self, 
        new_summary: str, 
        past_summaries: List[Dict[str, str]], 
        limit: int = 2
    ) -> List[Dict[str, any]]:
        """
        新規要約と過去の要約を比較し、類似度の高い案件を返却
        
        Args:
            new_summary: 新規生成された要約
            past_summaries: 過去の要約リスト [{"id": "xxx", "summary": "xxx", "title": "xxx", "created_at": "xxx"}]
            limit: 返却件数（デフォルト: 2）
            
        Returns:
            類似度の高い案件のリスト（類似度スコア付き）
        """
        if not past_summaries:
            return []
        
        try:
            # 類似度計算のためのプロンプトを作成
            prompt = self._create_similarity_prompt(new_summary, past_summaries)
            
            # OpenAI APIで類似度計算
            response = await self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {
                        "role": "system",
                        "content": "あなたは酒税法に関する相談案件の類似度を判定する専門家です。新規の要約と過去の要約を比較し、内容の類似性を0-100のスコアで評価してください。"
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                temperature=0.1,
                max_tokens=1000
            )
            
            # レスポンスをパース
            similar_cases = self._parse_similarity_response(response.choices[0].message.content, past_summaries)
            
            # 類似度スコアでソートし、上位N件を返却
            similar_cases.sort(key=lambda x: x['similarity_score'], reverse=True)
            return similar_cases[:limit]
            
        except Exception as e:
            logger.error(f"類似度計算エラー: {e}")
            # エラー時は単純なキーワードマッチングでフォールバック
            return self._fallback_similarity_search(new_summary, past_summaries, limit)
    
    def _create_similarity_prompt(self, new_summary: str, past_summaries: List[Dict[str, str]]) -> str:
        """類似度計算用のプロンプトを作成"""
        prompt = f"""
新規の要約: {new_summary}

以下の過去の要約と比較し、内容の類似性を0-100のスコアで評価してください。
各要約について、以下の形式で回答してください：

ID: [要約のID]
類似度スコア: [0-100の数値]
理由: [類似性の理由を簡潔に説明]

過去の要約:
"""
        
        for i, summary_data in enumerate(past_summaries, 1):
            prompt += f"""
{i}. ID: {summary_data['id']}
   要約: {summary_data['summary']}
   タイトル: {summary_data['title']}
"""
        
        prompt += """
回答は以下の形式でお願いします：
ID: xxx
類似度スコア: xx
理由: xxx

ID: xxx
類似度スコア: xx
理由: xxx
"""
        
        return prompt
    
    def _parse_similarity_response(self, response_text: str, past_summaries: List[Dict[str, str]]) -> List[Dict[str, any]]:
        """OpenAI APIのレスポンスをパース"""
        similar_cases = []
        
        try:
            # レスポンスを行ごとに分割
            lines = response_text.strip().split('\n')
            current_case = {}
            
            for line in lines:
                line = line.strip()
                if line.startswith('ID:'):
                    if current_case:
                        similar_cases.append(current_case)
                    current_case = {'id': line.replace('ID:', '').strip()}
                elif line.startswith('類似度スコア:'):
                    score_text = line.replace('類似度スコア:', '').strip()
                    try:
                        current_case['similarity_score'] = int(score_text)
                    except ValueError:
                        current_case['similarity_score'] = 0
                elif line.startswith('理由:'):
                    current_case['reason'] = line.replace('理由:', '').strip()
            
            # 最後の案件を追加
            if current_case:
                similar_cases.append(current_case)
            
            # 過去の要約データと結合
            for case in similar_cases:
                case_id = case['id']
                for summary_data in past_summaries:
                    if summary_data['id'] == case_id:
                        case.update({
                            'title': summary_data['title'],
                            'summary': summary_data['summary'],
                            'created_at': summary_data['created_at']
                        })
                        break
            
        except Exception as e:
            logger.error(f"レスポンスパースエラー: {e}")
            # パースに失敗した場合は空のリストを返す
            return []
        
        return similar_cases
    
    def _fallback_similarity_search(self, new_summary: str, past_summaries: List[Dict[str, str]], limit: int) -> List[Dict[str, any]]:
        """フォールバック用の単純なキーワードマッチング"""
        logger.info("フォールバック: キーワードマッチングによる類似度計算")
        
        # 新規要約からキーワードを抽出（簡単な単語分割）
        new_keywords = set(new_summary.lower().split())
        
        scored_cases = []
        for summary_data in past_summaries:
            # 過去の要約からキーワードを抽出
            past_keywords = set(summary_data['summary'].lower().split())
            
            # 共通キーワード数を計算
            common_keywords = len(new_keywords.intersection(past_keywords))
            total_keywords = len(new_keywords.union(past_keywords))
            
            # 類似度スコアを計算（0-100）
            similarity_score = int((common_keywords / total_keywords) * 100) if total_keywords > 0 else 0
            
            scored_cases.append({
                'id': summary_data['id'],
                'title': summary_data['title'],
                'summary': summary_data['summary'],
                'created_at': summary_data['created_at'],
                'similarity_score': similarity_score,
                'reason': f"共通キーワード数: {common_keywords}"
            })
        
        # 類似度スコアでソート
        scored_cases.sort(key=lambda x: x['similarity_score'], reverse=True)
        return scored_cases[:limit]
