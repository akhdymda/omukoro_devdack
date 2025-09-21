import time
import logging
import asyncio
from typing import List, Dict, Any, Optional
import requests

from app.models.rag_comparison import (
    RAGComparisonRequest, RAGComparisonResponse, 
    DocumentChunk, HybridDocumentChunk, RAGType, RAGAnalysis
)
from app.services.cosmos_service import CosmosService
from app.services.hybrid_rag_service import HybridRAGService
from app.services.rag_analysis_service import RAGAnalysisService

logger = logging.getLogger(__name__)


class RAGComparisonService:
    """RAG比較サービス"""
    
    def __init__(self):
        self.cosmos_service = CosmosService()
        self.hybrid_rag_service = HybridRAGService()
        self.analysis_service = RAGAnalysisService()
        self._initialized = False
    
    async def initialize(self) -> bool:
        """サービスを初期化"""
        try:
            # ハイブリッドRAGサービスの初期化
            hybrid_initialized = await self.hybrid_rag_service.initialize()
            
            self._initialized = hybrid_initialized
            
            if self._initialized:
                logger.info("RAG比較サービス初期化完了")
            else:
                logger.error("RAG比較サービス初期化失敗")
            
            return self._initialized
            
        except Exception as e:
            logger.error(f"RAG比較サービス初期化エラー: {e}")
            return False
    
    async def compare_rag(self, request: RAGComparisonRequest) -> RAGComparisonResponse:
        """RAG比較を実行"""
        start_time = time.time()
        
        try:
            if not self._initialized:
                await self.initialize()
            
            if not self._initialized:
                execution_time = (time.time() - start_time) * 1000
                return RAGComparisonResponse(
                    query=request.query,
                    traditional_rag_labels=[],
                    hybrid_rag_labels=[],
                    traditional_rag={},
                    hybrid_rag={},
                    comparison_metrics={},
                    total_execution_time_ms=execution_time,
                    success=False,
                    error_message="サービス初期化に失敗しました"
                )
            
            # 1. 従来RAGの実行
            traditional_start = time.time()
            traditional_result = await self._execute_traditional_rag(request)
            traditional_time = (time.time() - traditional_start) * 1000
            
            # 2. ハイブリッドRAGの実行
            hybrid_start = time.time()
            hybrid_result = await self._execute_hybrid_rag(request)
            hybrid_time = (time.time() - hybrid_start) * 1000
            
            # 3. 比較メトリクスの計算
            comparison_metrics = self._calculate_comparison_metrics(
                traditional_result, hybrid_result, traditional_time, hybrid_time
            )
            
            execution_time = (time.time() - start_time) * 1000
            
            # prefLabelの比較用データを準備
            traditional_labels = []
            hybrid_labels = []
            
            # 従来RAGのprefLabelを抽出
            for chunk in traditional_result.get("chunks", []):
                pref_label = chunk.get("prefLabel", "")
                if pref_label and pref_label not in traditional_labels:
                    traditional_labels.append(pref_label)
            
            # ハイブリッドRAGのprefLabelを抽出（メタデータから）
            for chunk in hybrid_result.get("final_chunks", []):
                metadata = chunk.get("metadata", {})
                node_label = metadata.get("node_label", "")
                if node_label and node_label not in hybrid_labels:
                    hybrid_labels.append(node_label)
            
            # 4. RAG分析を生成
            analysis = await self.analysis_service.generate_analysis(
                request.query, traditional_result, hybrid_result
            )
            
            # レスポンスにprefLabel比較と分析を追加
            response_data = {
                "query": request.query,
                "traditional_rag_labels": traditional_labels,
                "hybrid_rag_labels": hybrid_labels,
                "traditional_rag": traditional_result,
                "hybrid_rag": hybrid_result,
                "comparison_metrics": comparison_metrics,
                "analysis": analysis,
                "total_execution_time_ms": execution_time,
                "success": True,
                "error_message": None
            }
            
            return RAGComparisonResponse(**response_data)
            
        except Exception as e:
            logger.error(f"RAG比較エラー: {e}")
            execution_time = (time.time() - start_time) * 1000
            
            return RAGComparisonResponse(
                query=request.query,
                traditional_rag_labels=[],
                hybrid_rag_labels=[],
                traditional_rag={},
                hybrid_rag={},
                comparison_metrics={},
                total_execution_time_ms=execution_time,
                success=False,
                error_message=str(e)
            )
    
    async def _execute_traditional_rag(self, request: RAGComparisonRequest) -> Dict[str, Any]:
        """従来RAGを実行（ベクトル検索）"""
        try:
            # ハイブリッドRAGサービスのベクトル検索のみを使用
            from app.models.hybrid_rag import HybridSearchRequest
            
            # ベクトル検索のみを実行するためのリクエスト
            vector_request = HybridSearchRequest(
                query=request.query,
                max_chunks=request.traditional_limit,
                vector_weight=1.0,  # ベクトル検索のみ
                graph_weight=0.0,   # グラフ検索無効
                keyword_weight=0.0, # キーワード検索無効
                enable_query_expansion=False,
                max_related_nodes=1  # 最小値に設定（使用されないが）
            )
            
            # ハイブリッドRAGサービスのベクトル検索のみを実行
            vector_result = await self.hybrid_rag_service._vector_search(request.query)
            
            # DocumentChunkに変換
            chunks = []
            for doc in vector_result.documents:
                chunk = DocumentChunk(
                    chunk_id=doc.id,
                    prefLabel=doc.source,
                    section_label=doc.source,
                    text=doc.content,
                    score=doc.score,
                    search_type="vector"  # ベクトル検索として明示
                )
                chunks.append(chunk)
            
            return {
                "rag_type": RAGType.TRADITIONAL,
                "chunks": [chunk.dict() for chunk in chunks],
                "total_count": len(chunks),
                "execution_time_ms": vector_result.execution_time_ms,
                "search_method": "Vector Search",
                "data_source": "Vector DB"
            }
            
        except Exception as e:
            logger.error(f"従来RAG実行エラー: {e}")
            return {
                "rag_type": RAGType.TRADITIONAL,
                "chunks": [],
                "total_count": 0,
                "execution_time_ms": 0.0,
                "search_method": "Vector Search",
                "data_source": "Vector DB",
                "error": str(e)
            }
    
    async def _execute_hybrid_rag(self, request: RAGComparisonRequest) -> Dict[str, Any]:
        """ハイブリッドRAGを実行"""
        try:
            # ハイブリッドRAGサービスを呼び出し
            from app.models.hybrid_rag import HybridSearchRequest
            
            hybrid_request = HybridSearchRequest(
                query=request.query,
                max_chunks=request.hybrid_max_chunks,
                vector_weight=request.hybrid_vector_weight,
                graph_weight=request.hybrid_graph_weight,
                keyword_weight=request.hybrid_keyword_weight,
                enable_query_expansion=request.enable_query_expansion,
                max_related_nodes=request.hybrid_max_related_nodes
            )
            
            hybrid_result = await self.hybrid_rag_service.hybrid_search(hybrid_request)
            
            return {
                "rag_type": RAGType.HYBRID,
                "query": hybrid_result.query,
                "expanded_query": hybrid_result.expanded_query,
                "final_chunks": [chunk.dict() for chunk in hybrid_result.final_chunks],
                "search_results": {
                    search_type: {
                        "search_type": search_result.search_type,
                        "total_count": search_result.total_count,
                        "execution_time_ms": search_result.execution_time_ms
                    }
                    for search_type, search_result in hybrid_result.search_results.items()
                },
                "total_count": len(hybrid_result.final_chunks),
                "execution_time_ms": hybrid_result.total_execution_time_ms,
                "search_methods": ["vector", "graph", "keyword"],
                "data_sources": ["Vector DB", "Graph DB", "Keyword Search"]
            }
            
        except Exception as e:
            logger.error(f"ハイブリッドRAG実行エラー: {e}")
            return {
                "rag_type": RAGType.HYBRID,
                "query": request.query,
                "expanded_query": None,
                "final_chunks": [],
                "search_results": {},
                "total_count": 0,
                "execution_time_ms": 0.0,
                "search_methods": ["vector", "graph", "keyword"],
                "data_sources": ["Vector DB", "Graph DB", "Keyword Search"],
                "error": str(e)
            }
    
    def _calculate_comparison_metrics(
        self, 
        traditional_result: Dict[str, Any], 
        hybrid_result: Dict[str, Any],
        traditional_time: float,
        hybrid_time: float
    ) -> Dict[str, Any]:
        """比較メトリクスを計算"""
        try:
            traditional_count = traditional_result.get("total_count", 0)
            hybrid_count = hybrid_result.get("total_count", 0)
            
            # 実行時間比較
            time_comparison = {
                "traditional_time_ms": traditional_time,
                "hybrid_time_ms": hybrid_time,
                "time_difference_ms": abs(hybrid_time - traditional_time),
                "faster_method": "traditional" if traditional_time < hybrid_time else "hybrid"
            }
            
            # 結果数比較
            count_comparison = {
                "traditional_count": traditional_count,
                "hybrid_count": hybrid_count,
                "count_difference": abs(hybrid_count - traditional_count),
                "more_results_method": "traditional" if traditional_count > hybrid_count else "hybrid"
            }
            
            # スコア比較（利用可能な場合）
            score_comparison = self._compare_scores(traditional_result, hybrid_result)
            
            # 多様性比較
            diversity_comparison = self._compare_diversity(traditional_result, hybrid_result)
            
            return {
                "time_comparison": time_comparison,
                "count_comparison": count_comparison,
                "score_comparison": score_comparison,
                "diversity_comparison": diversity_comparison,
                "summary": {
                    "traditional_advantages": self._get_traditional_advantages(time_comparison, count_comparison),
                    "hybrid_advantages": self._get_hybrid_advantages(time_comparison, count_comparison, diversity_comparison)
                }
            }
            
        except Exception as e:
            logger.error(f"比較メトリクス計算エラー: {e}")
            return {"error": str(e)}
    
    def _compare_scores(self, traditional_result: Dict[str, Any], hybrid_result: Dict[str, Any]) -> Dict[str, Any]:
        """スコアを比較"""
        try:
            traditional_chunks = traditional_result.get("chunks", [])
            hybrid_chunks = hybrid_result.get("final_chunks", [])
            
            if not traditional_chunks or not hybrid_chunks:
                return {"error": "スコア比較に必要なデータが不足しています"}
            
            # 従来RAGのスコア統計
            traditional_scores = [chunk.get("score", 0) for chunk in traditional_chunks]
            traditional_avg = sum(traditional_scores) / len(traditional_scores) if traditional_scores else 0
            traditional_max = max(traditional_scores) if traditional_scores else 0
            traditional_min = min(traditional_scores) if traditional_scores else 0
            
            # ハイブリッドRAGのスコア統計
            hybrid_scores = [chunk.get("score", 0) for chunk in hybrid_chunks]
            hybrid_avg = sum(hybrid_scores) / len(hybrid_scores) if hybrid_scores else 0
            hybrid_max = max(hybrid_scores) if hybrid_scores else 0
            hybrid_min = min(hybrid_scores) if hybrid_scores else 0
            
            return {
                "traditional": {
                    "average_score": round(traditional_avg, 3),
                    "max_score": round(traditional_max, 3),
                    "min_score": round(traditional_min, 3)
                },
                "hybrid": {
                    "average_score": round(hybrid_avg, 3),
                    "max_score": round(hybrid_max, 3),
                    "min_score": round(hybrid_min, 3)
                },
                "comparison": {
                    "higher_average": "traditional" if traditional_avg > hybrid_avg else "hybrid",
                    "score_difference": round(abs(traditional_avg - hybrid_avg), 3)
                }
            }
            
        except Exception as e:
            logger.error(f"スコア比較エラー: {e}")
            return {"error": str(e)}
    
    def _compare_diversity(self, traditional_result: Dict[str, Any], hybrid_result: Dict[str, Any]) -> Dict[str, Any]:
        """多様性を比較"""
        try:
            traditional_chunks = traditional_result.get("chunks", [])
            hybrid_chunks = hybrid_result.get("final_chunks", [])
            
            # 従来RAGの多様性（法令名の種類）
            traditional_sources = set()
            for chunk in traditional_chunks:
                source = chunk.get("prefLabel", "")
                if source:
                    traditional_sources.add(source)
            
            # ハイブリッドRAGの多様性（検索タイプの種類）
            hybrid_search_types = set()
            for chunk in hybrid_chunks:
                search_type = chunk.get("search_type", "")
                if search_type:
                    hybrid_search_types.add(search_type)
            
            return {
                "traditional_unique_sources": len(traditional_sources),
                "hybrid_unique_search_types": len(hybrid_search_types),
                "traditional_sources": list(traditional_sources),
                "hybrid_search_types": list(hybrid_search_types),
                "diversity_winner": "traditional" if len(traditional_sources) > len(hybrid_search_types) else "hybrid"
            }
            
        except Exception as e:
            logger.error(f"多様性比較エラー: {e}")
            return {"error": str(e)}
    
    def _get_traditional_advantages(self, time_comparison: Dict, count_comparison: Dict) -> List[str]:
        """従来RAGの利点を取得"""
        advantages = []
        
        if time_comparison.get("faster_method") == "traditional":
            advantages.append("実行速度が速い")
        
        if count_comparison.get("more_results_method") == "traditional":
            advantages.append("より多くの結果を取得")
        
        advantages.extend([
            "シンプルなベクトル検索",
            "文脈理解に優れる",
            "実装が単純で安定"
        ])
        
        return advantages
    
    def _get_hybrid_advantages(self, time_comparison: Dict, count_comparison: Dict, diversity_comparison: Dict) -> List[str]:
        """ハイブリッドRAGの利点を取得"""
        advantages = []
        
        if time_comparison.get("faster_method") == "hybrid":
            advantages.append("実行速度が速い")
        
        if count_comparison.get("more_results_method") == "hybrid":
            advantages.append("より多くの結果を取得")
        
        advantages.extend([
            "ベクトル+グラフ+キーワードの複合検索",
            "関連概念の拡張による網羅性",
            "多様な検索手法の相乗効果",
            "複雑なクエリへの対応力"
        ])
        
        return advantages
    
    async def get_health_status(self) -> Dict[str, Any]:
        """ヘルスステータスを取得"""
        try:
            status = {
                "rag_comparison_initialized": self._initialized,
                "cosmos_service_available": self.cosmos_service is not None,
                "hybrid_rag_available": False
            }
            
            if self._initialized:
                hybrid_health = await self.hybrid_rag_service.get_health_status()
                status["hybrid_rag_available"] = hybrid_health.get("hybrid_rag_initialized", False)
                status["hybrid_rag_details"] = hybrid_health
            
            return status
            
        except Exception as e:
            return {
                "rag_comparison_initialized": False,
                "error": str(e)
            }
