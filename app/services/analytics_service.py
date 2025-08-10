import logging
import re
from typing import List, Optional, Dict, Tuple, Any
from collections import Counter
from datetime import datetime
from app.models.analysis import AnalyticsRequest, AnalyticsResponse, ConsultantInfo, AnalysisMetadata
from app.services.dummy_data_service import DummyDataService
# from app.services.rag_service import RAGService

logger = logging.getLogger(__name__)

class AnalyticsService:
    """
    論点・質問事項と相談先の分析サービス
    
    RAG相当の推論機能を実装（ダミーデータベース）
    将来的にRAGシステムに差し替え予定
    """
    
    def __init__(self):
    # ダミーデータサービスのみ使用
        self.dummy_service = DummyDataService()

        # RAG は無効化
        self.rag_service = None
        self.use_rag = False
        logger.info("RAG is disabled for deployment")
    
    async def analyze_consultation(self, request: AnalyticsRequest) -> AnalyticsResponse:
        """
        本格的なRAGまたはRAG風推論による相談内容分析
        
        Args:
            request: 分析リクエスト
            
        Returns:
            AnalyticsResponse: 分析結果
        """
        try:
            logger.info(f"🚀 分析開始: テキスト長 {len(request.text)}, ファイル数 {len(request.files_content or [])}")
            
            # 入力検証
            if not self._validate_input(request):
                raise ValueError("相談内容またはファイルを入力してください")
            
            # 🆕 RAGサービス利用可能な場合
            if self.use_rag and self.rag_service:
                logger.info("🧠 本格的なRAGシステムで分析実行")
                rag_result = await self.rag_service.analyze_with_rag(
                    text=request.text,
                    files_content=request.files_content or []
                )
                return self._convert_rag_result_to_response(rag_result)
            
            # フォールバック: 従来のRAG風推論
            logger.info("🔄 フォールバック: RAG風推論で分析実行")
            
            # 🔍 Step 1: テキスト前処理と特徴抽出
            processed_data = self._preprocess_and_extract_features(request)
            
            # 🧠 Step 2: RAG風多段階推論
            reasoning_result = await self._rag_reasoning_pipeline(processed_data)
            
            # 📊 Step 3: 信頼度の動的計算
            confidence_score = self._calculate_dynamic_confidence(processed_data, reasoning_result)
            
            # 📝 Step 4: 推論過程の記録
            reasoning_trace = self._generate_reasoning_trace(processed_data, reasoning_result)
            
            # 🎯 Step 5: 最終レスポンス構築
            response = self._build_final_response(
                reasoning_result, 
                confidence_score, 
                reasoning_trace
            )
            
            logger.info(f"✅ 分析完了: 論点{len(response.questions)}件, 相談先{len(response.consultants)}名")
            return response
            
        except ValueError as e:
            logger.warning(f"❌ Analytics入力エラー: {e}")
            raise
        except Exception as e:
            logger.error(f"💥 Analytics推論エラー: {e}")
            raise Exception("分析処理中にエラーが発生しました")
    
    def _convert_rag_result_to_response(self, rag_result: Dict[str, Any]) -> AnalyticsResponse:
        """RAG結果をAnalyticsResponseに変換"""
        try:
            consultants = [
                ConsultantInfo(
                    name=consultant["name"],
                    department=consultant["department"],
                    expertise=consultant["expertise"]
                )
                for consultant in rag_result.get("consultants", [])
            ]
            
            metadata = AnalysisMetadata(
                confidence=rag_result["analysis_metadata"]["confidence"],
                generated_at=rag_result["analysis_metadata"]["generated_at"],
                used_dummy_data=rag_result["analysis_metadata"].get("used_dummy_data", True),
                matched_regulations=rag_result["analysis_metadata"].get("matched_regulations", []),
                fallback=rag_result["analysis_metadata"].get("fallback", False)
            )
            
            return AnalyticsResponse(
                summary=rag_result["summary"],
                questions=rag_result["questions"],
                consultants=consultants,
                analysis_metadata=metadata
            )
            
        except Exception as e:
            logger.error(f"❌ RAG結果変換エラー: {e}")
            # 最小限のフォールバック
            return AnalyticsResponse(
                summary="企画案について法令適合性の確認が必要です。",
                questions=["関連法令の適用範囲確認", "必要な許認可の特定"],
                consultants=[
                    ConsultantInfo(
                        name="田中 法務",
                        department="法務部",
                        expertise="酒税法・食品衛生法"
                    )
                ],
                analysis_metadata=AnalysisMetadata(
                    confidence=0.6,
                    generated_at=datetime.now().isoformat(),
                    used_dummy_data=True,
                    matched_regulations=[],
                    fallback=True
                )
            )
    
    def _validate_input(self, request: AnalyticsRequest) -> bool:
        """入力の詳細バリデーション"""
        has_text = request.text and request.text.strip()
        has_files = request.files_content and any(content.strip() for content in request.files_content)
        
        if not has_text and not has_files:
            return False
        
        # テキスト長制限チェック
        total_text_length = len(request.text or "")
        if request.files_content:
            total_text_length += sum(len(content) for content in request.files_content)
        
        if total_text_length > 50000:  # 50KB制限
            logger.warning(f"⚠️  総テキスト長が制限を超えています: {total_text_length} chars")
            return False
        
        return True
    
    def _preprocess_and_extract_features(self, request: AnalyticsRequest) -> Dict[str, Any]:
        """RAG風前処理と特徴抽出"""
        logger.info("🔍 テキスト前処理と特徴抽出開始")
        
        # テキスト統合
        combined_text = self._combine_text_sources(request.text, request.files_content or [])
        
        # キーワード抽出
        keywords = self._extract_keywords(combined_text)
        
        # エンティティ抽出（簡易版）
        entities = self._extract_entities(combined_text)
        
        # 意図分類
        intent_category = self._classify_intent(combined_text, keywords)
        
        # 複雑度評価
        complexity_score = self._assess_content_complexity(combined_text)
        
        processed_data = {
            "original_text": request.text,
            "files_content": request.files_content or [],
            "combined_text": combined_text,
            "keywords": keywords,
            "entities": entities,
            "intent_category": intent_category,
            "complexity_score": complexity_score,
            "text_length": len(combined_text),
            "file_count": len(request.files_content or [])
        }
        
        logger.info(f"✅ 特徴抽出完了: キーワード{len(keywords)}個, エンティティ{len(entities)}個, 複雑度{complexity_score:.2f}")
        return processed_data
    
    def _combine_text_sources(self, text: str, files_content: List[str]) -> str:
        """複数の情報源を重み付けして統合"""
        combined = ""
        
        # メインテキスト（重み: 1.0）
        if text and text.strip():
            combined += text.strip()
        
        # ファイル内容（重み: 0.8）
        if files_content:
            for i, content in enumerate(files_content):
                if content.strip():
                    combined += f"\n\n[資料 {i+1}]\n{content.strip()}"
        
        return combined
    
    def _extract_keywords(self, text: str) -> List[str]:
        """重要キーワードの抽出"""
        # 業界特化キーワード辞書
        industry_keywords = {
            "酒類": ["酒", "アルコール", "醸造", "蒸留", "発酵", "度数"],
            "食品": ["食品", "飲料", "製造", "加工", "保存", "賞味期限"],
            "法令": ["法律", "規制", "免許", "許可", "届出", "認可"],
            "マーケティング": ["広告", "宣伝", "表示", "ラベル", "訴求", "効果"],
            "開発": ["新商品", "開発", "企画", "設計", "試作", "評価"],
            "品質": ["品質", "安全", "検査", "基準", "管理", "保証"]
        }
        
        text_lower = text.lower()
        found_keywords = []
        
        for category, keywords in industry_keywords.items():
            for keyword in keywords:
                if keyword in text_lower:
                    found_keywords.append(f"{category}:{keyword}")
        
        # 追加的なキーワード抽出（頻出単語）
        words = re.findall(r'\b[ぁ-んァ-ヶー\w]+\b', text)
        word_freq = Counter(words)
        
        # 頻出上位キーワードを追加
        for word, freq in word_freq.most_common(10):
            if len(word) > 1 and freq > 1:
                found_keywords.append(f"頻出:{word}")
        
        return found_keywords[:20]  # 最大20個まで
    
    def _extract_entities(self, text: str) -> Dict[str, List[str]]:
        """エンティティ抽出（簡易版）"""
        entities = {
            "products": [],
            "target_audience": [],
            "regulations": [],
            "departments": [],
            "timeframes": []
        }
        
        # 商品・サービス
        product_patterns = [
            r'新[商品|製品|サービス]',
            r'[低|高|無]アルコール[商品|飲料]?',
            r'機能性[表示]?食品',
            r'健康[飲料|食品]'
        ]
        
        for pattern in product_patterns:
            matches = re.findall(pattern, text)
            entities["products"].extend(matches)
        
        # ターゲット層
        target_patterns = [
            r'\d+代[の]?[男性|女性|学生|社会人]',
            r'[若年|中年|高齢][層|者]',
            r'健康志向[の]?[消費者|顧客]'
        ]
        
        for pattern in target_patterns:
            matches = re.findall(pattern, text)
            entities["target_audience"].extend(matches)
        
        return entities
    
    def _classify_intent(self, text: str, keywords: List[str]) -> str:
        """相談意図の分類"""
        intent_scores = {
            "新商品開発": 0,
            "法令確認": 0,
            "マーケティング戦略": 0,
            "品質管理": 0,
            "海外展開": 0
        }
        
        # キーワードベースのスコアリング
        for keyword in keywords:
            if any(x in keyword for x in ["開発", "新商品", "企画"]):
                intent_scores["新商品開発"] += 1
            if any(x in keyword for x in ["法律", "規制", "免許"]):
                intent_scores["法令確認"] += 1
            if any(x in keyword for x in ["広告", "マーケティング", "宣伝"]):
                intent_scores["マーケティング戦略"] += 1
            if any(x in keyword for x in ["品質", "安全", "検査"]):
                intent_scores["品質管理"] += 1
            if any(x in keyword for x in ["海外", "輸出", "国際"]):
                intent_scores["海外展開"] += 1
        
        # 最高スコアの意図を返す
        return max(intent_scores.items(), key=lambda x: x[1])[0]
    
    def _assess_content_complexity(self, text: str) -> float:
        """内容の複雑度評価"""
        factors = {
            "length": min(len(text) / 1000, 1.0),  # テキスト長
            "vocabulary": len(set(text.split())) / max(len(text.split()), 1),  # 語彙の多様性
            "technical_terms": len([w for w in text.split() if len(w) > 6]) / max(len(text.split()), 1)  # 専門用語の割合
        }
        
        # 重み付け平均
        complexity = (
            factors["length"] * 0.4 +
            factors["vocabulary"] * 0.3 +
            factors["technical_terms"] * 0.3
        )
        
        return min(complexity, 1.0)
    
    async def _rag_reasoning_pipeline(self, processed_data: Dict[str, Any]) -> Dict[str, Any]:
        """RAG風多段階推論パイプライン"""
        logger.info("🧠 RAG推論パイプライン開始")
        
        # Step 1: 関連規制の特定
        relevant_regulations = self._identify_relevant_regulations(processed_data)
        
        # Step 2: 論点の構造化生成
        structured_questions = self._generate_structured_questions(processed_data, relevant_regulations)
        
        # Step 3: 最適相談先の選定
        optimal_consultants = self._select_optimal_consultants(processed_data, relevant_regulations)
        
        # Step 4: コンテキスト統合
        integrated_context = self._integrate_context(processed_data, relevant_regulations, structured_questions)
        
        # Step 5: 品質評価
        quality_metrics = self._evaluate_reasoning_quality(structured_questions, optimal_consultants)
        
        reasoning_result = {
            "regulations": relevant_regulations,
            "questions": structured_questions,
            "consultants": optimal_consultants,
            "context": integrated_context,
            "quality_metrics": quality_metrics
        }
        
        logger.info("✅ RAG推論パイプライン完了")
        return reasoning_result
    
    def _identify_relevant_regulations(self, processed_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """関連規制の高精度特定"""
        # ダミーデータから基本的な分析を取得
        base_analysis = self.dummy_service.analyze_consultation_content(
            text=processed_data["original_text"],
            files_content=processed_data["files_content"]
        )
        
        # 追加的な推論で精度向上
        enhanced_regulations = []
        for reg in base_analysis["analysis_metadata"].get("matched_regulations", []):
            reg_info = {
                "name": reg,
                "relevance_score": self._calculate_regulation_relevance(reg, processed_data),
                "key_points": self._get_regulation_key_points(reg, processed_data)
            }
            enhanced_regulations.append(reg_info)
        
        # 関連度でソート
        enhanced_regulations.sort(key=lambda x: x["relevance_score"], reverse=True)
        return enhanced_regulations[:3]  # 上位3つ
    
    def _calculate_regulation_relevance(self, regulation: str, processed_data: Dict[str, Any]) -> float:
        """規制の関連度計算"""
        relevance_mapping = {
            "酒税法": ["酒", "アルコール", "醸造", "度数", "製造"],
            "食品衛生法": ["食品", "安全", "衛生", "製造", "品質"],
            "景品表示法": ["広告", "表示", "マーケティング", "効果"],
            "薬機法": ["健康", "機能性", "効能", "医薬"]
        }
        
        keywords = relevance_mapping.get(regulation, [])
        text_lower = processed_data["combined_text"].lower()
        
        matches = sum(1 for keyword in keywords if keyword in text_lower)
        return matches / len(keywords) if keywords else 0.0
    
    def _get_regulation_key_points(self, regulation: str, processed_data: Dict[str, Any]) -> List[str]:
        """規制の重要ポイント抽出"""
        # ダミーデータから基本ポイントを取得し、コンテキストに応じて調整
        regulation_data = next(
            (reg for reg in self.dummy_service.dummy_regulations if reg["category"] == regulation),
            None
        )
        
        if not regulation_data:
            return []
        
        # コンテキストに応じてポイントを調整
        adjusted_points = []
        for point in regulation_data["points"]:
            # 簡易的な関連度チェック
            if any(keyword in processed_data["combined_text"].lower() 
                   for keyword in point.lower().split()):
                adjusted_points.append(point)
        
        return adjusted_points or regulation_data["points"][:2]  # 最低2つは保証
    
    def _generate_structured_questions(self, processed_data: Dict[str, Any], regulations: List[Dict]) -> List[str]:
        """構造化された質問生成"""
        questions = []
        
        # 規制ベースの質問
        for reg in regulations:
            for point in reg["key_points"]:
                context_question = f"{point}について、{processed_data['intent_category']}の観点から具体的な対応方針"
                questions.append(context_question)
        
        # 意図ベースの追加質問
        intent_specific_questions = self._generate_intent_specific_questions(processed_data)
        questions.extend(intent_specific_questions)
        
        # 重複排除と優先順位付け
        unique_questions = list(dict.fromkeys(questions))
        return unique_questions[:5]  # 最大5つ
    
    def _generate_intent_specific_questions(self, processed_data: Dict[str, Any]) -> List[str]:
        """意図別特化質問"""
        intent = processed_data["intent_category"]
        
        intent_questions = {
            "新商品開発": [
                "商品コンセプトの法的実現可能性の評価",
                "製造プロセスにおける規制対応の具体的手順"
            ],
            "法令確認": [
                "該当法令の詳細な適用範囲の確認",
                "必要な申請・届出手続きのタイムライン"
            ],
            "マーケティング戦略": [
                "広告表現の法的リスクアセスメント",
                "ターゲット訴求における規制制約の整理"
            ]
        }
        
        return intent_questions.get(intent, [])
    
    def _select_optimal_consultants(self, processed_data: Dict[str, Any], regulations: List[Dict]) -> List[Dict]:
        """最適相談先の高精度選定"""
        # 基本的な相談先選定
        base_analysis = self.dummy_service.analyze_consultation_content(
            text=processed_data["original_text"],
            files_content=processed_data["files_content"]
        )
        
        base_consultants = base_analysis["consultants"]
        
        # 追加的な最適化
        optimized_consultants = []
        for consultant in base_consultants:
            consultant_score = self._calculate_consultant_match_score(
                consultant, processed_data, regulations
            )
            consultant["match_score"] = consultant_score
            optimized_consultants.append(consultant)
        
        # マッチスコアでソート
        optimized_consultants.sort(key=lambda x: x.get("match_score", 0), reverse=True)
        return optimized_consultants[:3]  # 上位3名
    
    def _calculate_consultant_match_score(self, consultant: Dict, processed_data: Dict, regulations: List[Dict]) -> float:
        """相談先マッチスコア計算"""
        score = 0.0
        
        # 専門分野の一致度
        expertise_keywords = consultant["expertise"].lower().split("・")
        for reg in regulations:
            if any(keyword in reg["name"].lower() for keyword in expertise_keywords):
                score += reg["relevance_score"] * 0.4
        
        # 意図カテゴリとの一致度
        intent = processed_data["intent_category"]
        department_intent_mapping = {
            "法務部": ["法令確認"],
            "マーケティング部": ["マーケティング戦略"],
            "商品開発部": ["新商品開発"],
            "品質保証部": ["品質管理"]
        }
        
        if intent in department_intent_mapping.get(consultant["department"], []):
            score += 0.3
        
        return min(score, 1.0)
    
    def _integrate_context(self, processed_data: Dict, regulations: List[Dict], questions: List[str]) -> Dict[str, Any]:
        """コンテキスト統合"""
        return {
            "primary_regulations": [reg["name"] for reg in regulations],
            "content_complexity": processed_data["complexity_score"],
            "question_count": len(questions),
            "has_file_content": len(processed_data["files_content"]) > 0,
            "intent_confidence": 0.8  # 意図分類の信頼度
        }
    
    def _evaluate_reasoning_quality(self, questions: List[str], consultants: List[Dict]) -> Dict[str, float]:
        """推論品質の評価"""
        return {
            "question_diversity": len(set(q[:20] for q in questions)) / max(len(questions), 1),
            "consultant_coverage": len(set(c["department"] for c in consultants)) / max(len(consultants), 1),
            "overall_completeness": min((len(questions) + len(consultants)) / 8, 1.0)
        }
    
    def _calculate_dynamic_confidence(self, processed_data: Dict, reasoning_result: Dict) -> float:
        """動的信頼度計算"""
        confidence_factors = {
            "keyword_coverage": len(processed_data["keywords"]) / 10,  # キーワード網羅度
            "regulation_relevance": sum(reg["relevance_score"] for reg in reasoning_result["regulations"]) / len(reasoning_result["regulations"]),
            "consultant_match": sum(c.get("match_score", 0) for c in reasoning_result["consultants"]) / len(reasoning_result["consultants"]),
            "content_quality": processed_data["complexity_score"],
            "reasoning_quality": reasoning_result["quality_metrics"]["overall_completeness"]
        }
        
        # 重み付け計算
        weighted_confidence = sum(
            confidence_factors[factor] * weight 
            for factor, weight in self.confidence_weights.items() 
            if factor in confidence_factors
        )
        
        return min(max(weighted_confidence, 0.0), 1.0)
    
    def _generate_reasoning_trace(self, processed_data: Dict, reasoning_result: Dict) -> Dict[str, Any]:
        """推論過程の記録"""
        return {
            "input_analysis": {
                "text_length": processed_data["text_length"],
                "keywords_found": len(processed_data["keywords"]),
                "intent_detected": processed_data["intent_category"]
            },
            "regulation_matching": {
                "regulations_identified": len(reasoning_result["regulations"]),
                "max_relevance_score": max((reg["relevance_score"] for reg in reasoning_result["regulations"]), default=0)
            },
            "consultant_selection": {
                "consultants_evaluated": len(reasoning_result["consultants"]),
                "selection_criteria": "relevance_score + department_match + expertise_alignment"
            },
            "reasoning_path": f"Intent({processed_data['intent_category']}) → Regulations({len(reasoning_result['regulations'])}) → Questions({len(reasoning_result['questions'])}) → Consultants({len(reasoning_result['consultants'])})"
        }
    
    def _build_final_response(self, reasoning_result: Dict, confidence_score: float, reasoning_trace: Dict) -> AnalyticsResponse:
        """最終レスポンス構築"""
        # サマリー生成（より詳細な推論ベース）
        regulations_text = "、".join(reg["name"] for reg in reasoning_result["regulations"])
        summary = f"提出された企画案について、{regulations_text}の観点から詳細な検討が必要です。特に{reasoning_result['context']['primary_regulations'][0]}への対応が重要と判断されます。"
        
        return AnalyticsResponse(
            summary=summary,
            questions=reasoning_result["questions"],
            consultants=[
                ConsultantInfo(
                    name=consultant["name"],
                    department=consultant["department"],
                    expertise=consultant["expertise"]
                )
                for consultant in reasoning_result["consultants"]
            ],
            analysis_metadata=AnalysisMetadata(
                confidence=confidence_score,
                generated_at=datetime.now().isoformat(),
                used_dummy_data=True,
                matched_regulations=reasoning_result["context"]["primary_regulations"],
                fallback=False
            )
        )
    
    async def get_dummy_data_info(self) -> dict:
        """
        ダミーデータの情報を取得（デバッグ用）
        
        🚨 本番環境では削除予定
        """
        base_info = self.dummy_service.get_dummy_data_info()
        base_info.update({
            "rag_features": {
                "multi_stage_reasoning": True,
                "dynamic_confidence": True,
                "context_integration": True,
                "reasoning_trace": True
            },
            "enhancement_level": "RAG-equivalent"
        })
        return base_info