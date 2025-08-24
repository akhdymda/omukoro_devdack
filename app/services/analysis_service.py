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
import logging

logger = logging.getLogger(__name__)
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
            logger.warning("OpenAI API key is not set")
    
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
            # OpenAI API keyが設定されていない場合はダミー分析を返す
            return {
                "ai_score": 3,
                "ai_suggestions": ["AI分析機能を使用するにはOpenAI API keyの設定が必要です"],
                "confidence": 0.6
            }
        
        try:
            # プロンプトを構築
            prompt = self._build_analysis_prompt(text, rule_result)
            
            response = await self.openai_client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "あなたはサッポロビール株式会社のビジネス企画を支援する、リアルタイム入力分析のAI判定モジュールです。入力文の充実度を1〜5で素早く見立て、足りない点を端的に指摘します。評価の中心は次の5項目: 1) 商品・サービス内容, 2) ターゲット顧客, 3) スケジュール・時期, 4) 目的・目標の明確性。文章の論理性と具体性も加味してください。口調は少し砕けた日本語で、簡潔に。"},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=500,
                temperature=0.3
            )
            
            ai_response = response.choices[0].message.content
            
            # AI応答を解析
            return self._parse_ai_response(ai_response)
            
        except Exception as e:
            logger.error(f"AI分析エラー: {e}")
            return None
    
    def _build_analysis_prompt(self, text: str, rule_result) -> str:
        """分析用プロンプトを構築"""
        return f"""
        以下の入力文の充実度を評価し、不足情報を特定して改善提案を生成してください。

        【入力文】
        {text}

        【ルールベース分析(参考)】
        - 推定充実度: {rule_result.get('completeness', 'N/A')}/5
        - 主な不足点: {', '.join(rule_result.get('suggestions', []))}

        【評価観点】
        - 基本情報の有無: 商品・サービス / ターゲット顧客 / スケジュール・時期 / 目的・目標
        - AI観点: 文章の論理構造の整合性、情報の具体性

        【出力スタイル（厳守）】
        - 一行サマリを先頭に。少し砕けた日本語で端的に（例: 「全体は悪くないけど、ターゲットと予算が曖昧かも」）。
        - 続けて短い箇条書きで2〜3件の提案（例: 「ターゲット層の年代・属性を一言で」「概算予算のレンジ」「実施時期（月）」）。
        - 合計200字以内。前置きや引用・記号は不要。JSONは出力しない。
        """

    def _parse_ai_response(self, ai_response: str) -> dict:
        """AI応答を解析"""
        try:
            # 簡単な解析（実際の実装ではより詳細な解析が必要）
            return {
                "ai_score": 3,  # デフォルト値
                "ai_suggestions": [ai_response[:200] + "..." if len(ai_response) > 200 else ai_response],
                "confidence": 0.8
            }
        except Exception as e:
            logger.error(f"AI応答解析エラー: {e}")
            return {
                "ai_score": 3,
                "ai_suggestions": ["AI分析でエラーが発生しました"],
                "confidence": 0.5
            }
    
    def _combine_results(self, rule_result, ai_result) -> AnalysisResponse:
        """ルールベース分析とAI分析の結果を統合"""
        # 充実度スコアを統合
        rule_score = rule_result.get('completeness', 3)
        ai_score = ai_result.get('ai_score', 3) if ai_result else 3
        
        # 重み付き平均（ルールベース: 0.7, AI: 0.3）
        combined_score = rule_score * 0.8 + ai_score * 0.2
        final_score = max(2, int(round(combined_score)))
        
        # 提案を統合
        suggestions = []
        if ai_result and ai_result.get('ai_suggestions'):
            suggestions.extend(ai_result['ai_suggestions'])

        # より寛容な基準での追加提案
        if final_score < 4:
            if 'ターゲット' not in (rule_result.get('suggestions', [])[0] if rule_result.get('suggestions') else ''):
                suggestions.append("ターゲット層をもう少し具体化できそうです")
        
        # 信頼度を統合
        confidence = min(1.0, rule_result.get('confidence', 0.8) * 0.8 + 
                        (ai_result.get('confidence', 0.5) if ai_result else 0.5) * 0.2)
        
        return AnalysisResponse(
            completeness=final_score,
            suggestions=suggestions[:5],  # 最大5件
            confidence=confidence
        )
    
    def _get_cache_key(self, text: str) -> str:
        """テキストからキャッシュキーを生成"""
        hash_object = hashlib.sha256(text.encode())
        return f"analysis_result:{hash_object.hexdigest()}"
    
    async def _get_cached_result(self, text: str) -> Optional[AnalysisResponse]:
        """キャッシュから結果を取得"""
        try:
            cache_key = self._get_cache_key(text)
            return await self.cache_service.get(cache_key)
        except Exception as e:
            logger.error(f"キャッシュ取得エラー: {e}")
            return None
    
    async def _cache_result(self, text: str, result: AnalysisResponse):
        """結果をキャッシュに保存"""
        try:
            cache_key = self._get_cache_key(text)
            await self.cache_service.set(cache_key, result)
        except Exception as e:
            logger.error(f"キャッシュ保存エラー: {e}")
