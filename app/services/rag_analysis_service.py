import os
import json
import logging
from typing import Dict, Any, Optional
import openai
from dotenv import load_dotenv
from app.models.rag_comparison import RAGAnalysis

# .envファイルを読み込み
load_dotenv()

logger = logging.getLogger(__name__)


class RAGAnalysisService:
    """RAG比較分析サービス"""
    
    def __init__(self):
        self.openai_client = None
        self._initialize_openai()
    
    def _initialize_openai(self):
        """OpenAIクライアントを初期化"""
        try:
            api_key = os.getenv("OPENAI_API_KEY")
            if not api_key:
                logger.warning("OPENAI_API_KEY環境変数が設定されていません")
                return
            
            self.openai_client = openai.OpenAI(api_key=api_key)
            logger.info("OpenAIクライアント初期化完了")
            
        except Exception as e:
            logger.error(f"OpenAIクライアント初期化エラー: {e}")
    
    async def generate_analysis(
        self, 
        query: str, 
        traditional_rag: Dict[str, Any], 
        hybrid_rag: Dict[str, Any]
    ) -> Optional[RAGAnalysis]:
        """RAG比較結果を分析して解説を生成"""
        
        if not self.openai_client:
            logger.warning("OpenAIクライアントが初期化されていません")
            return self._create_fallback_analysis()
        
        try:
            # プロンプトを作成
            prompt = self._create_analysis_prompt(query, traditional_rag, hybrid_rag)
            
            # OpenAI APIを呼び出し
            response = self.openai_client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {
                        "role": "system",
                        "content": "あなたはRAG（Retrieval-Augmented Generation）システムの専門家です。従来RAGとハイブリッドRAGの比較分析を行い、それぞれの特徴と優位性を客観的に評価してください。"
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                temperature=0.7,
                max_tokens=2000,
                response_format={"type": "json_object"}
            )
            
            content = response.choices[0].message.content
            if not content:
                logger.error("OpenAI APIから空のレスポンスを受信")
                return self._create_fallback_analysis()
            
            # JSONレスポンスをパース
            try:
                analysis_data = json.loads(content)
                return RAGAnalysis(
                    analysis=analysis_data.get("analysis", "分析を実行しました。"),
                    traditional_advantages=analysis_data.get("traditional_advantages", ["シンプルな検索手法", "実行速度が速い", "安定した結果取得"]),
                    hybrid_advantages=analysis_data.get("hybrid_advantages", ["複数の検索手法を組み合わせ", "より網羅的な検索", "関連情報の発見"]),
                    recommendation=analysis_data.get("recommendation", "クエリの内容に応じて適切なRAG手法を選択することを推奨します。")
                )
            except json.JSONDecodeError as e:
                logger.error(f"JSON解析エラー: {e}")
                return self._create_fallback_analysis()
                
        except Exception as e:
            logger.error(f"RAG分析生成エラー: {e}")
            return self._create_fallback_analysis()
    
    def _create_analysis_prompt(self, query: str, traditional_rag: Dict[str, Any], hybrid_rag: Dict[str, Any]) -> str:
        """分析用プロンプトを作成"""
        
        # 従来RAGの結果を整理
        traditional_chunks = traditional_rag.get("chunks", [])
        traditional_count = len(traditional_chunks)
        
        # ハイブリッドRAGの結果を整理
        hybrid_chunks = hybrid_rag.get("final_chunks", [])
        hybrid_count = len(hybrid_chunks)
        hybrid_search_methods = hybrid_rag.get("search_methods", [])
        
        # 従来RAGの詳細情報を作成（prefLabelとtextのみ）
        traditional_details = []
        for i, chunk in enumerate(traditional_chunks[:5], 1):
            pref_label = chunk.get("prefLabel", "N/A")
            text = chunk.get("text", "")[:300] + "..." if len(chunk.get("text", "")) > 300 else chunk.get("text", "")
            traditional_details.append(f"{i}. {pref_label}\n   内容: {text}")
        
        # ハイブリッドRAGの詳細情報を作成（prefLabelとtextのみ）
        hybrid_details = []
        for i, chunk in enumerate(hybrid_chunks[:5], 1):
            metadata = chunk.get("metadata", {})
            pref_label = metadata.get("prefLabel", "N/A")
            search_type = chunk.get("search_type", "N/A")
            content = chunk.get("content", "")[:300] + "..." if len(chunk.get("content", "")) > 300 else chunk.get("content", "")
            hybrid_details.append(f"{i}. {pref_label} ({search_type})\n   内容: {content}")
        
        # 検索手法の分布を計算
        search_type_counts = {}
        for chunk in hybrid_chunks:
            search_type = chunk.get("search_type", "unknown")
            search_type_counts[search_type] = search_type_counts.get(search_type, 0) + 1
        
        prompt = f"""
以下のRAG比較結果について、クエリと検索された法令条文の内容を照らし合わせて分析してください。

【クエリ】
{query}

【従来RAG結果】
- 取得件数: {traditional_count}件
- 検索手法: {traditional_rag.get("search_method", "Vector Search")}

法令条文の詳細:
{chr(10).join(traditional_details) if traditional_details else "  - 結果なし"}

【ハイブリッドRAG結果】
- 取得件数: {hybrid_count}件
- 検索手法: {', '.join(hybrid_search_methods)}
- 検索手法分布: {search_type_counts}

法令条文の詳細:
{chr(10).join(hybrid_details) if hybrid_details else "  - 結果なし"}

【分析要求】
以下の観点から具体的に分析してください：

1. **発見された条文の価値分析**
   - 従来RAGが発見した条文の具体的な価値（クエリへの回答として）
   - ハイブリッドRAGが発見した条文の具体的な価値
   - クエリに対する回答の完全性の比較

2. **条文内容の比較**
   - 従来RAGとハイブリッドRAGで発見された条文の重複と違い
   - 各RAGが発見した条文の特徴と関連性
   - クエリに対する回答の網羅性

3. **網羅性の観点（重要）**
   - リスク評価の観点：取得された法令情報で、クエリに関連する法的リスクを十分に把握できているか
   - アクション計画の観点：今後の対応策を検討する上で必要な法令情報が網羅されているか
   - 幅の観点：関連する複数の法令・条文が取得されているか（単一の条文に偏っていないか）
   - インパクトの観点：重要な法令（基本法、施行令、通達等）が適切に含まれているか
   - 不足している可能性のある法令領域や条文の特定

4. **各RAGの特徴と優位性**
   - 従来RAGの成功した点と課題
   - ハイブリッドRAGの成功した点と課題
   - 具体的な改善提案

5. **推奨事項**
   - このクエリに対してどちらのRAGが適しているか
   - その理由と根拠
   - 網羅性の観点からの推奨

回答は以下のJSON形式で返してください：
{{
  "analysis": "クエリと検索された条文内容を照らし合わせた詳細分析（網羅性の観点を含む）",
  "traditional_advantages": ["具体的な優位性1", "具体的な優位性2", "具体的な優位性3"],
  "hybrid_advantages": ["具体的な優位性1", "具体的な優位性2", "具体的な優位性3"],
  "recommendation": "具体的な推奨とその理由（網羅性の観点を含む）"
}}
"""
        return prompt
    
    def _create_fallback_analysis(self) -> RAGAnalysis:
        """フォールバック分析結果を作成"""
        return RAGAnalysis(
            analysis="RAG比較結果の分析を実行しましたが、詳細な解析に失敗しました。基本的な比較情報を表示します。",
            traditional_advantages=[
                "シンプルで安定した検索手法",
                "実行速度が速い",
                "リソース使用量が少ない"
            ],
            hybrid_advantages=[
                "複数の検索手法を組み合わせ",
                "より網羅的な検索が可能",
                "関連情報の発見に優れている"
            ],
            recommendation="クエリの内容に応じて適切なRAG手法を選択することを推奨します。シンプルな検索には従来RAG、複雑な検索にはハイブリッドRAGが適しています。"
        )
