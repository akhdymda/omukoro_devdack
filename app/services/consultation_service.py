from openai import AsyncOpenAI
import json
import hashlib
from typing import List, Dict, Any, Optional
from app.config import settings
from app.services.cosmos_service import CosmosService
import logging

logger = logging.getLogger(__name__)

class ConsultationService:
    """相談分析と法令検索を統合したサービス"""
    
    def __init__(self):
        self.cosmos_service = CosmosService()
        
        # OpenAI クライアントを初期化
        api_key = settings.openai_api_key
        if api_key:
            self.openai_client = AsyncOpenAI(api_key=api_key)
        else:
            self.openai_client = None
            logger.warning("OpenAI API key is not set")
    
    async def generate_suggestions(self, text: str) -> Dict[str, Any]:
        """相談内容から提案を生成"""
        try:
            # 1. 法令検索
            regulations = self.cosmos_service.search_regulations(text, limit=5)
            
            # 2. OpenAI APIを使用した分析
            analysis_result = await self._analyze_with_openai(text, regulations)
            
            # 3. 結果を統合
            consultation_id = self._generate_consultation_id(text)
            
            # フロントエンドが期待する形式に変換
            result = {
                "consultation_id": consultation_id,
                "suggested_questions": self._extract_questions_from_analysis(analysis_result["analysis"]),
                "action_items": self._extract_action_items_from_analysis(analysis_result["analysis"]),
                "relevant_regulations": self._format_regulations_for_frontend(regulations),
                "analysis": analysis_result["analysis"]
            }
            
            logger.info(f"相談分析完了: ID={consultation_id}, 法令数={len(regulations)}")
            return result
            
        except Exception as e:
            logger.error(f"相談分析エラー: {e}")
            raise
    
    async def get_consultation_detail(self, consultation_id: str) -> Dict[str, Any]:
        """相談詳細を取得"""
        try:
            # 実際の実装では、データベースから相談内容を取得する
            # 現在はダミーデータを返す
            return {
                "consultation_id": consultation_id,
                "title": "相談内容",
                "content": "相談の詳細内容",
                "created_at": "2025-08-12T22:00:00Z",
                "status": "analyzed"
            }
        except Exception as e:
            logger.error(f"相談詳細取得エラー: {e}")
            raise
    
    async def get_consultation_regulations(self, consultation_id: str) -> List[Dict[str, Any]]:
        """相談に関連する法令を取得"""
        try:
            # 実際の実装では、consultation_idに関連する法令を取得する
            # 現在はダミーデータを返す
            return [
                {
                    "id": "reg_001",
                    "text": "法令の内容...",
                    "prefLabel": "酒税法",
                    "relevance_score": 0.85
                }
            ]
        except Exception as e:
            logger.error(f"相談法令取得エラー: {e}")
            raise
    
    async def _analyze_with_openai(self, text: str, regulations: List[Dict[str, Any]]) -> Dict[str, Any]:
        """OpenAI APIを使用して相談内容を分析"""
        if not self.openai_client:
            # OpenAI API keyが設定されていない場合はダミー分析を返す
            return {
                "analysis": f"相談内容「{text[:100]}...」について分析しました。\n\n主要な論点:\n- 内容の詳細化が必要\n- 具体的な数値の提示\n- リスク分析の追加\n\n次のステップ:\n- 詳細な調査\n- 専門家への相談\n- 計画の具体化",
                "regulations_count": len(regulations),
                "model_used": "dummy"
            }
        
        try:
            # 法令情報をテキストに変換
            regulations_text = "\n".join([
                f"- {reg['prefLabel']}: {reg['text']}"
                for reg in regulations
            ])
            
            prompt = f"""
以下の相談内容を分析し、主要な論点と提案を提供してください。

相談内容:
{text}

関連法令:
{regulations_text}

以下の形式で回答してください:
1. 主要な論点（3-5個）
2. 確認すべき事項（3-5個）
3. 次のステップ（3-5個）
4. リスク要因（2-3個）
5. 推奨される相談先（2-3個）
"""
            
            response = await self.openai_client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "あなたは法律とビジネスの専門家です。相談内容を分析して、具体的で実用的なアドバイスを提供してください。"},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=1000,
                temperature=0.7
            )
            
            analysis_text = response.choices[0].message.content
            
            # 分析結果を構造化
            return {
                "analysis": analysis_text,
                "regulations_count": len(regulations),
                "model_used": "gpt-3.5-turbo"
            }
            
        except Exception as e:
            logger.error(f"OpenAI API分析エラー: {e}")
            return {"error": f"分析中にエラーが発生しました: {str(e)}"}
    
    def _generate_consultation_id(self, text: str) -> str:
        """相談IDを生成"""
        # テキストのハッシュからIDを生成
        hash_object = hashlib.md5(text.encode())
        return f"consultation_{hash_object.hexdigest()[:8]}"
    
    def _extract_questions_from_analysis(self, analysis_text: str) -> List[str]:
        """分析テキストから質問事項を抽出"""
        questions = []
        lines = analysis_text.split('\n')
        in_questions_section = False
        
        for line in lines:
            if '確認すべき事項:' in line or '2.' in line:
                in_questions_section = True
                continue
            elif in_questions_section and (line.startswith('3.') or line.startswith('次のステップ:')):
                break
            elif in_questions_section and line.strip().startswith('-') and line.strip() != '-':
                question = line.strip()[1:].strip()
                if question:
                    questions.append(question)
        
        # デフォルトの質問を追加
        if not questions:
            questions = [
                "酒税法の基本的な要件は何ですか？",
                "許可申請の手続きはどのようなものですか？",
                "更新手続きの期限はいつですか？"
            ]
        
        return questions[:5]  # 最大5件
    
    def _extract_action_items_from_analysis(self, analysis_text: str) -> str:
        """分析テキストから次の行動を抽出"""
        action_items = []
        lines = analysis_text.split('\n')
        in_actions_section = False
        
        for line in lines:
            if '次のステップ:' in line or '3.' in line:
                in_actions_section = True
                continue
            elif in_actions_section and (line.startswith('4.') or line.startswith('リスク要因:')):
                break
            elif in_actions_section and line.strip().startswith('-') and line.strip() != '-':
                action = line.strip()[1:].strip()
                if action:
                    action_items.append(action)
        
        # デフォルトの行動を追加
        if not action_items:
            action_items = [
                "酒税法の詳細調査を開始する",
                "専門家への相談を予約する",
                "必要な書類を準備する"
            ]
        
        return '\n'.join(action_items)
    
    def _format_regulations_for_frontend(self, regulations: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """フロントエンド用に法令データをフォーマット"""
        formatted_regulations = []
        for reg in regulations:
            formatted_regulations.append({
                "chunk_id": reg["id"],
                "prefLabel": reg["prefLabel"],
                "section_label": reg["prefLabel"],
                "text": reg["text"],
                "score": reg["score"]
            })
        return formatted_regulations
    
    def get_health_status(self) -> Dict[str, Any]:
        """ヘルスチェック用の状態を取得"""
        cosmos_status = self.cosmos_service.get_health_status()
        return {
            "service": "consultation",
            "openai_configured": self.openai_client is not None,
            "cosmos": cosmos_status
        }
