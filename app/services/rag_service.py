import logging
import numpy as np
from typing import List, Dict, Any, Tuple
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity
from openai import AsyncOpenAI
import json
import os
from datetime import datetime
from app.services.dummy_data_service import DummyDataService

logger = logging.getLogger(__name__)

class RAGService:
    """
    本格的なRAGシステム実装
    
    - ベクトル化による類似度検索
    - OpenAI APIとの統合
    - 相談先と質問事項の関連付け
    """
    
    def __init__(self):
        # ベクトル化モデルの初期化
        try:
            self.embedding_model = SentenceTransformer('all-MiniLM-L6-v2')
            logger.info("✅ SentenceTransformer model loaded successfully")
        except Exception as e:
            logger.error(f"❌ Failed to load embedding model: {e}")
            self.embedding_model = None
        
        # OpenAI クライアント初期化
        api_key = os.getenv("OPENAI_API_KEY")
        if api_key:
            self.openai_client = AsyncOpenAI(api_key=api_key)
            logger.info("✅ OpenAI client initialized")
        else:
            self.openai_client = None
            logger.warning("⚠️ OpenAI API key not found")
        
        # ダミーデータサービス（知識ベース）
        self.dummy_service = DummyDataService()
        
        # 知識ベースのベクトル化
        self.knowledge_vectors = None
        self.knowledge_items = []
        self._initialize_knowledge_base()
    
    def _initialize_knowledge_base(self):
        """知識ベース（ダミーデータ）のベクトル化"""
        try:
            logger.info("🧠 知識ベースをベクトル化中...")
            
            # ダミーデータから知識項目を抽出
            self.knowledge_items = []
            
            # 規制・法令情報
            for regulation in self.dummy_service.dummy_regulations:
                for point in regulation["points"]:
                    self.knowledge_items.append({
                        "type": "regulation",
                        "category": regulation["category"],
                        "content": point,
                        "related_consultants": self._get_related_consultants(regulation["category"])
                    })
            
            # 過去事例情報
            for case in self.dummy_service.dummy_cases:
                for question in case["common_questions"]:
                    self.knowledge_items.append({
                        "type": "case",
                        "keywords": case["keywords"],
                        "content": question,
                        "related_consultants": self._get_consultants_by_keywords(case["keywords"])
                    })
            
            # 相談先情報
            for consultant in self.dummy_service.dummy_consultants:
                expertise_text = f"{consultant['department']}の{consultant['expertise']}に関する専門知識"
                self.knowledge_items.append({
                    "type": "consultant",
                    "content": expertise_text,
                    "consultant_info": consultant,
                    "related_consultants": [consultant]
                })
            
            # ベクトル化実行
            if self.embedding_model:
                contents = [item["content"] for item in self.knowledge_items]
                self.knowledge_vectors = self.embedding_model.encode(contents)
                logger.info(f"✅ {len(self.knowledge_items)}件の知識項目をベクトル化完了")
            else:
                logger.warning("⚠️ ベクトル化モデルが利用できません")
                
        except Exception as e:
            logger.error(f"❌ 知識ベース初期化エラー: {e}")
    
    def _get_related_consultants(self, regulation_category: str) -> List[Dict]:
        """規制カテゴリに関連する相談先を取得"""
        mapping = {
            "酒税法": ["田中 法務"],
            "食品衛生法": ["田中 法務", "佐藤 品質"],
            "景品表示法": ["山田 マーケ"],
            "薬機法": ["田中 法務", "山田 マーケ"]
        }
        
        consultant_names = mapping.get(regulation_category, [])
        consultants = []
        
        for name in consultant_names:
            consultant = next(
                (c for c in self.dummy_service.dummy_consultants if c["name"] == name),
                None
            )
            if consultant:
                consultants.append(consultant)
        
        return consultants
    
    def _get_consultants_by_keywords(self, keywords: List[str]) -> List[Dict]:
        """キーワードに基づいて相談先を推定"""
        consultant_mapping = {
            "新商品": "鈴木 開発",
            "アルコール": "田中 法務",
            "健康": "山田 マーケ",
            "海外": "高橋 営業"
        }
        
        consultants = []
        for keyword in keywords:
            name = consultant_mapping.get(keyword)
            if name:
                consultant = next(
                    (c for c in self.dummy_service.dummy_consultants if c["name"] == name),
                    None
                )
                if consultant and consultant not in consultants:
                    consultants.append(consultant)
        
        return consultants[:2]  # 最大2名
    
    async def analyze_with_rag(self, text: str, files_content: List[str] = None) -> Dict[str, Any]:
        """
        RAGを使用した高度な分析処理
        
        Args:
            text: 入力テキスト
            files_content: ファイルから抽出されたテキスト
            
        Returns:
            Dict: RAG分析結果
        """
        try:
            logger.info("🚀 RAG分析を開始")
            
            # Step 1: 入力テキストの統合と前処理
            combined_text = self._combine_input_texts(text, files_content or [])
            
            # Step 2: 入力テキストのベクトル化
            query_vector = self._vectorize_query(combined_text)
            
            # Step 3: 類似度検索で関連知識を取得
            relevant_knowledge = self._search_similar_knowledge(query_vector, top_k=5)
            
            # Step 4: LLMを使用した論点整理
            llm_analysis = await self._llm_reasoning(combined_text, relevant_knowledge)
            
            # Step 5: 相談先と質問の関連付け
            structured_result = self._structure_result_with_consultants(llm_analysis, relevant_knowledge)
            
            logger.info("✅ RAG分析完了")
            return structured_result
            
        except Exception as e:
            logger.error(f"❌ RAG分析エラー: {e}")
            # フォールバック：従来のダミーデータ分析
            return self.dummy_service.analyze_consultation_content(text, files_content)
    
    def _combine_input_texts(self, text: str, files_content: List[str]) -> str:
        """入力テキストとファイル内容を統合"""
        combined = text.strip()
        
        if files_content:
            for i, content in enumerate(files_content):
                if content.strip():
                    combined += f"\n\n[添付資料 {i+1}]\n{content.strip()}"
        
        return combined
    
    def _vectorize_query(self, text: str) -> np.ndarray:
        """クエリテキストをベクトル化"""
        if not self.embedding_model:
            return np.array([])
        
        try:
            vector = self.embedding_model.encode([text])
            return vector[0]
        except Exception as e:
            logger.error(f"❌ ベクトル化エラー: {e}")
            return np.array([])
    
    def _search_similar_knowledge(self, query_vector: np.ndarray, top_k: int = 5) -> List[Dict]:
        """類似度検索で関連知識を取得"""
        if self.knowledge_vectors is None or len(query_vector) == 0:
            logger.warning("⚠️ ベクトル検索が利用できません。ランダム選択します。")
            return self.knowledge_items[:top_k]
        
        try:
            # コサイン類似度計算
            similarities = cosine_similarity([query_vector], self.knowledge_vectors)[0]
            
            # 類似度の高い順にソート
            top_indices = np.argsort(similarities)[::-1][:top_k]
            
            relevant_items = []
            for idx in top_indices:
                item = self.knowledge_items[idx].copy()
                item["similarity_score"] = float(similarities[idx])
                relevant_items.append(item)
            
            logger.info(f"🔍 類似度検索完了: {len(relevant_items)}件の関連知識を取得")
            return relevant_items
            
        except Exception as e:
            logger.error(f"❌ 類似度検索エラー: {e}")
            return self.knowledge_items[:top_k]
    
    async def _llm_reasoning(self, query_text: str, relevant_knowledge: List[Dict]) -> Dict[str, Any]:
        """LLMを使用した論点整理"""
        if not self.openai_client:
            logger.warning("⚠️ OpenAI APIが利用できません")
            return self._fallback_reasoning(query_text, relevant_knowledge)
        
        try:
            # 関連知識をプロンプトに組み込み
            knowledge_context = self._build_knowledge_context(relevant_knowledge)
            
            system_prompt = """あなたは酒類業界の法務・規制の専門家です。
相談内容に対して、関連する法令・規制を参照し、具体的な論点を整理してください。
必ずJSON形式で回答してください。"""

            user_prompt = f"""
【相談内容】
{query_text}

【参考知識】
{knowledge_context}

以下の形式でJSON回答してください：
{{
    "summary": "相談内容の要約（50文字程度）",
    "questions": [
        {{
            "question": "具体的な質問や論点",
            "category": "関連する規制カテゴリ",
            "priority": "high/medium/low",
            "related_knowledge_ids": [参考にした知識のインデックス]
        }}
    ],
    "confidence": 0.0-1.0の信頼度,
    "reasoning": "判定理由（100文字以内）"
}}
"""
            
            response = await self.openai_client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                max_tokens=800,
                temperature=0.3,
                timeout=15
            )
            
            content = response.choices[0].message.content
            llm_result = json.loads(content)
            
            logger.info("✅ LLM論点整理完了")
            return llm_result
            
        except Exception as e:
            logger.error(f"❌ LLM推論エラー: {e}")
            return self._fallback_reasoning(query_text, relevant_knowledge)
    
    def _build_knowledge_context(self, relevant_knowledge: List[Dict]) -> str:
        """関連知識をプロンプト用のテキストに構築"""
        context_parts = []
        
        for i, item in enumerate(relevant_knowledge):
            similarity = item.get("similarity_score", 0)
            content_type = item["type"]
            content = item["content"]
            
            if content_type == "regulation":
                category = item["category"]
                context_parts.append(f"[{i}] 【{category}】{content} (関連度: {similarity:.2f})")
            elif content_type == "case":
                keywords = ", ".join(item["keywords"])
                context_parts.append(f"[{i}] 【過去事例: {keywords}】{content} (関連度: {similarity:.2f})")
            elif content_type == "consultant":
                context_parts.append(f"[{i}] 【専門知識】{content} (関連度: {similarity:.2f})")
        
        return "\n".join(context_parts)
    
    def _fallback_reasoning(self, query_text: str, relevant_knowledge: List[Dict]) -> Dict[str, Any]:
        """LLM利用不可時のフォールバック推論"""
        questions = []
        categories = set()
        
        # 関連知識から質問を生成
        for item in relevant_knowledge[:3]:
            if item["type"] == "regulation":
                question = f"{item['category']}における{item['content']}について"
                questions.append({
                    "question": question,
                    "category": item["category"],
                    "priority": "medium",
                    "related_knowledge_ids": [relevant_knowledge.index(item)]
                })
                categories.add(item["category"])
        
        return {
            "summary": f"提出された企画案について、{', '.join(categories)}の観点から検討が必要です。",
            "questions": questions,
            "confidence": 0.75,
            "reasoning": "関連知識ベースからの類似度検索結果による推論"
        }
    
    def _structure_result_with_consultants(self, llm_analysis: Dict, relevant_knowledge: List[Dict]) -> Dict[str, Any]:
        """相談先と質問事項を関連付けた結果構造を作成"""
        try:
            # 質問事項から相談先を推定
            consultants_map = {}
            question_consultant_mapping = []
            
            for question_data in llm_analysis.get("questions", []):
                question_text = question_data["question"]
                category = question_data.get("category", "")
                related_ids = question_data.get("related_knowledge_ids", [])
                
                # 関連知識から相談先を特定
                relevant_consultants = []
                for knowledge_id in related_ids:
                    if knowledge_id < len(relevant_knowledge):
                        knowledge = relevant_knowledge[knowledge_id]
                        if "related_consultants" in knowledge:
                            relevant_consultants.extend(knowledge["related_consultants"])
                
                # 重複排除
                unique_consultants = []
                for consultant in relevant_consultants:
                    if consultant not in unique_consultants:
                        unique_consultants.append(consultant)
                        consultants_map[consultant["name"]] = consultant
                
                question_consultant_mapping.append({
                    "question": question_text,
                    "category": category,
                    "priority": question_data.get("priority", "medium"),
                    "consultants": [c["name"] for c in unique_consultants[:2]]  # 最大2名
                })
            
            # 最終的な相談先リスト（重複排除済み）
            final_consultants = list(consultants_map.values())[:3]  # 最大3名
            
            # 結果構造作成
            return {
                "summary": llm_analysis.get("summary", "企画案について法令適合性の確認が必要です。"),
                "questions": [mapping["question"] for mapping in question_consultant_mapping],
                "consultants": final_consultants,
                "question_consultant_mapping": question_consultant_mapping,  # 🆕 追加
                "analysis_metadata": {
                    "confidence": llm_analysis.get("confidence", 0.8),
                    "generated_at": datetime.now().isoformat(),
                    "used_dummy_data": True,  # 現在はダミーデータベース
                    "rag_enabled": True,
                    "llm_reasoning": bool(self.openai_client),
                    "vector_search": bool(self.embedding_model),
                    "knowledge_items_used": len(relevant_knowledge)
                }
            }
            
        except Exception as e:
            logger.error(f"❌ 結果構造化エラー: {e}")
            # 基本的な構造にフォールバック
            return {
                "summary": llm_analysis.get("summary", "企画案について検討が必要です。"),
                "questions": [q.get("question", q) if isinstance(q, dict) else q for q in llm_analysis.get("questions", [])],
                "consultants": final_consultants if 'final_consultants' in locals() else [],
                "question_consultant_mapping": [],
                "analysis_metadata": {
                    "confidence": 0.6,
                    "generated_at": datetime.now().isoformat(),
                    "used_dummy_data": True,
                    "rag_enabled": True,
                    "fallback": True
                }
            }
    
    def get_service_info(self) -> Dict[str, Any]:
        """サービス情報を取得（デバッグ用）"""
        return {
            "service": "RAGService",
            "version": "1.0.0",
            "features": {
                "vector_search": bool(self.embedding_model),
                "llm_reasoning": bool(self.openai_client),
                "knowledge_base_size": len(self.knowledge_items),
                "embedding_model": "all-MiniLM-L6-v2" if self.embedding_model else None
            },
            "status": "production-ready"
        }