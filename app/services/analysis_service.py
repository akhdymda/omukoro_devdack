from openai import AsyncOpenAI
import json
import hashlib
from typing import Optional
from app.config import settings
from app.models.analysis import AnalysisRequest, AnalysisResponse
from app.utils.rule_analyzer import RuleBasedAnalyzer
from app.services.cache_service import CacheService
from dotenv import load_dotenv
import os

load_dotenv()

class AnalysisService:
    """
    テキスト分析サービス
    ルールベース分析とAI分析を組み合わせて、入力内容の充実度を判定
    """
    
    def __init__(self):
        self.rule_analyzer = RuleBasedAnalyzer()
        self.cache_service = CacheService()
        
        # OpenAI クライアントを初期化
        api_key = os.getenv("OPENAI_API_KEY") or settings.openai_api_key
        if api_key:
            self.openai_client = AsyncOpenAI(api_key=api_key)
        else:
            self.openai_client = None
            print("Warning: OpenAI API key is not set")
    
    async def analyze_input_completeness(self, request: AnalysisRequest) -> AnalysisResponse:
        """
        入力内容の充実度を分析する
        
        Args:
            request: 分析リクエスト
            
        Returns:
            AnalysisResponse: 分析結果
        """
        # 入力統合・正規化
        base_text = (request.text or "").strip()
        doc_text = (request.docText or "").strip()
        normalized_text = (base_text + ("\n\n" + doc_text if doc_text else "")).strip()
        # 長文はクリップ（仕様: 約6000文字）
        if len(normalized_text) > 6000:
            normalized_text = normalized_text[:6000]
        
        # 空のテキストの場合
        if not normalized_text:
            return AnalysisResponse(
                completeness=1,
                suggestions=["相談内容を入力してください"],
                confidence=1.0
            )
        
        # キャッシュから結果を取得を試行
        cached_result = await self._get_cached_result(normalized_text)
        if cached_result:
            return cached_result
        
        # 1. ルールベース分析（高速判定）
        rule_result = self.rule_analyzer.analyze_text(normalized_text)
        
        # 2. AI分析（詳細判定）
        ai_result = await self._ai_analysis(normalized_text, rule_result)
        
        # 3. 結果を統合
        final_result = self._combine_results(rule_result, ai_result)
        
        # 4. 結果をキャッシュ
        await self._cache_result(normalized_text, final_result)
        
        return final_result
    
    async def _ai_analysis(self, text: str, rule_result) -> Optional[dict]:
        """
        OpenAI APIを使用した詳細分析
        
        Args:
            text: 分析対象のテキスト
            rule_result: ルールベース分析の結果
            
        Returns:
            dict: AI分析結果
        """
        if not self.openai_client:
            return None
        
        try:
            # プロンプトを構築
            prompt = self._build_analysis_prompt(text, rule_result)
            
            response = await self.openai_client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "あなたはビジネス企画の分析専門家です。与えられた企画案について、情報の充実度を客観的に評価してください。"},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=400,
                temperature=0.3,
                timeout=10  # 10秒タイムアウト
            )
            
            # JSONレスポンスをパース
            content = response.choices[0].message.content
            return json.loads(content)
            
        except json.JSONDecodeError as e:
            print(f"AI analysis JSON parse error: {e}")
            return None
        except Exception as e:
            print(f"AI analysis error: {e}")
            return None
    
    def _build_analysis_prompt(self, text: str, rule_result) -> str:
        """
        AI分析用のプロンプトを構築
        
        Args:
            text: 分析対象のテキスト
            rule_result: ルールベース分析結果
            
        Returns:
            str: 構築されたプロンプト
        """
        prompt = f"""
以下のビジネス企画案について、情報の充実度を3段階（0:不足、1:中程度、2:詳細）で評価してください。

企画案：
{text}

ルールベース分析結果：
- 見つかったカテゴリ: {', '.join(rule_result.found_categories)}
- 不足カテゴリ: {', '.join(rule_result.missing_categories)}
- 基本スコア: {rule_result.score}

評価基準：
1. 商品/サービス内容の具体性
2. ターゲット顧客の明確性  
3. スケジュール・時期の明確性
4. 目的・目標の明確性
5. 実現可能性の検討

必ずJSON形式で回答してください：
{{
    "completeness": 0-2の整数,
    "suggestions": ["改善提案1", "改善提案2", "改善提案3"],
    "reasoning": "判定理由（100文字以内）",
    "confidence": 0.0-1.0の信頼度
}}
"""
        return prompt
    
    def _combine_results(self, rule_result, ai_result: Optional[dict]) -> AnalysisResponse:
        """
        ルールベース分析とAI分析の結果を統合
        
        Args:
            rule_result: ルールベース分析結果
            ai_result: AI分析結果（Noneの場合あり）
            
        Returns:
            AnalysisResponse: 統合された分析結果
        """
        # 0-2のスコアやAI結果を0-1のスコアに正規化し、5段階にマップ
        if ai_result:
            ai_comp_raw = ai_result.get("completeness", 0)
            # 既存プロンプトは0-2で返す想定。安全側で0-2→0-1へスケール。
            ai_score_01 = max(0.0, min(1.0, ai_comp_raw / 2))
            rule_score_01 = max(0.0, min(1.0, rule_result.score / 2))
            confidence = float(ai_result.get("confidence", 0.8))
            # 加重和: ルール6割、AI4割 + 信頼度微調整
            base_score = 0.6 * rule_score_01 + 0.4 * ai_score_01
            s = max(0.0, min(1.0, base_score * (0.8 + 0.2 * confidence)))
            suggestions = ai_result.get("suggestions", rule_result.missing_elements)
            reasoning = ai_result.get("reasoning")
        else:
            rule_score_01 = max(0.0, min(1.0, rule_result.score / 2))
            s = rule_score_01
            confidence = 0.7
            suggestions = self.rule_analyzer.get_improvement_suggestions(rule_result)
            reasoning = None

        # 0-1 → 1-5 段階
        if s < 0.20:
            completeness = 1
        elif s < 0.40:
            completeness = 2
        elif s < 0.60:
            completeness = 3
        elif s < 0.80:
            completeness = 4
        else:
            completeness = 5
        
        return AnalysisResponse(
            completeness=completeness,
            suggestions=suggestions[:5],  # 最大5つまで
            confidence=confidence,
            reasoning=reasoning
        )
    
    async def _get_cached_result(self, text: str) -> Optional[AnalysisResponse]:
        """
        キャッシュから分析結果を取得
        
        Args:
            text: 分析対象のテキスト
            
        Returns:
            AnalysisResponse: キャッシュされた結果（存在しない場合はNone）
        """
        cache_key = self._generate_cache_key(text)
        return await self.cache_service.get(cache_key)
    
    async def _cache_result(self, text: str, result: AnalysisResponse) -> None:
        """
        分析結果をキャッシュ
        
        Args:
            text: 分析対象のテキスト
            result: 分析結果
        """
        cache_key = self._generate_cache_key(text)
        await self.cache_service.set(cache_key, result, expire_seconds=3600)  # 1時間キャッシュ
    
    def _generate_cache_key(self, text: str) -> str:
        """
        テキストからキャッシュキーを生成
        
        Args:
            text: テキスト
            
        Returns:
            str: キャッシュキー
        """
        text_hash = hashlib.sha256(text.encode('utf-8')).hexdigest()
        return f"analysis:{text_hash}"