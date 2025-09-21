import asyncio
import logging
import time
from typing import List, Dict, Any, Optional, Tuple
from app.services.cosmos_service import CosmosService
from app.services.gremlin_service import GremlinService
from app.models.hybrid_search import (
    HybridSearchRequest, 
    HybridSearchResponse, 
    SearchResult, 
    SearchResultSource,
    GraphRelation,
    SearchError
)

logger = logging.getLogger(__name__)

class HybridSearchService:
    """ハイブリッド検索統合サービス"""
    
    def __init__(self):
        self.cosmos_service = CosmosService()
        self.gremlin_service = GremlinService()
        self._gremlin_connected = False
    
    async def initialize(self) -> bool:
        """サービスを初期化"""
        try:
            # Gremlin接続を試行
            self._gremlin_connected = await self.gremlin_service.connect()
            if not self._gremlin_connected:
                logger.warning("Gremlin接続に失敗しました。通常RAGのみで動作します。")
            
            return True
        except Exception as e:
            logger.error(f"ハイブリッド検索サービス初期化エラー: {e}")
            return False
    
    async def search(self, request: HybridSearchRequest) -> HybridSearchResponse:
        """ハイブリッド検索を実行"""
        start_time = time.time()
        
        try:
            if request.search_type == "traditional":
                return await self._traditional_search(request, start_time)
            else:  # hybrid
                return await self._hybrid_search(request, start_time)
                
        except Exception as e:
            logger.error(f"ハイブリッド検索エラー: {e}")
            return self._create_error_response(request, str(e))
    
    async def _traditional_search(self, request: HybridSearchRequest, start_time: float) -> HybridSearchResponse:
        """通常RAG検索を実行"""
        try:
            # 通常RAG検索
            traditional_results = self.cosmos_service.search_regulations(request.query, request.limit)
            
            # 結果をフォーマット
            search_results = []
            for result in traditional_results:
                search_results.append(SearchResult(
                    id=result.get('id', ''),
                    text=result.get('text', ''),
                    prefLabel=result.get('prefLabel', ''),
                    score=result.get('score', 0.0),
                    source=SearchResultSource.TRADITIONAL,
                    graph_relations=None
                ))
            
            execution_time = (time.time() - start_time) * 1000
            
            return HybridSearchResponse(
                search_type=request.search_type,
                query=request.query,
                results=search_results,
                total_count=len(search_results),
                traditional_count=len(search_results),
                graph_count=0,
                hybrid_count=0,
                execution_time_ms=execution_time
            )
            
        except Exception as e:
            logger.error(f"通常RAG検索エラー: {e}")
            return self._create_error_response(request, f"通常RAG検索エラー: {str(e)}")
    
    async def _hybrid_search(self, request: HybridSearchRequest, start_time: float) -> HybridSearchResponse:
        """ハイブリッド検索を実行"""
        errors = []
        traditional_results = []
        graph_results = []
        
        try:
            # 並列で通常RAGとGraphRAGを実行
            tasks = []
            
            # 通常RAG検索
            tasks.append(self._run_traditional_search(request.query, request.limit))
            
            # GraphRAG検索（接続されている場合のみ）
            if self._gremlin_connected:
                tasks.append(self._run_graph_search(request.query, request.limit))
            else:
                tasks.append(asyncio.create_task(self._dummy_graph_search()))
            
            # 並列実行
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # 結果を処理
            if isinstance(results[0], Exception):
                errors.append(SearchError(
                    error_type="traditional_search_error",
                    message=str(results[0]),
                    source="cosmos_service"
                ))
            else:
                traditional_results = results[0]
            
            if isinstance(results[1], Exception):
                errors.append(SearchError(
                    error_type="graph_search_error",
                    message=str(results[1]),
                    source="gremlin_service"
                ))
            else:
                graph_results = results[1]
            
            # 結果を統合
            integrated_results = await self._integrate_results(
                traditional_results, 
                graph_results, 
                request.include_graph_relations
            )
            
            execution_time = (time.time() - start_time) * 1000
            
            return HybridSearchResponse(
                search_type=request.search_type,
                query=request.query,
                results=integrated_results[:request.limit],
                total_count=len(integrated_results),
                traditional_count=len(traditional_results),
                graph_count=len(graph_results),
                hybrid_count=len(integrated_results) - len(traditional_results) - len(graph_results),
                execution_time_ms=execution_time
            )
            
        except Exception as e:
            logger.error(f"ハイブリッド検索エラー: {e}")
            return self._create_error_response(request, f"ハイブリッド検索エラー: {str(e)}")
    
    async def _run_traditional_search(self, query: str, limit: int) -> List[SearchResult]:
        """通常RAG検索を実行"""
        try:
            results = self.cosmos_service.search_regulations(query, limit)
            
            search_results = []
            for result in results:
                # スコアを正規化（0-1の範囲に）
                raw_score = result.get('score', 0.0)
                normalized_score = min(1.0, max(0.0, raw_score / 100.0)) if raw_score > 1.0 else raw_score
                
                search_results.append(SearchResult(
                    id=result.get('id', ''),
                    text=result.get('text', ''),
                    prefLabel=result.get('prefLabel', ''),
                    score=normalized_score,
                    source=SearchResultSource.TRADITIONAL,
                    graph_relations=None
                ))
            
            return search_results
            
        except Exception as e:
            logger.error(f"通常RAG検索実行エラー: {e}")
            raise
    
    async def _run_graph_search(self, query: str, limit: int) -> List[SearchResult]:
        """GraphRAG検索を実行"""
        try:
            # 法律概念を検索
            graph_vertices = await self.gremlin_service.search_legal_concepts(query, limit)
            
            search_results = []
            for vertex in graph_vertices:
                # 関係性を取得
                relations = []
                if vertex.get('id'):
                    edge_results = await self.gremlin_service.get_vertex_relations(vertex['id'])
                    relations = self._format_graph_relations(edge_results)
                
                search_results.append(SearchResult(
                    id=vertex.get('id', ''),
                    text=vertex.get('properties', {}).get('text', '')[:200] + "..." if len(vertex.get('properties', {}).get('text', '')) > 200 else vertex.get('properties', {}).get('text', ''),
                    prefLabel=vertex.get('id', ''),
                    score=0.8,  # GraphRAGのデフォルトスコア
                    source=SearchResultSource.GRAPH,
                    graph_relations=relations if relations else None
                ))
            
            return search_results
            
        except Exception as e:
            logger.error(f"GraphRAG検索実行エラー: {e}")
            raise
    
    async def _dummy_graph_search(self) -> List[SearchResult]:
        """GraphRAGが利用できない場合のダミー検索"""
        return []
    
    def _format_graph_relations(self, edge_results: List[Dict[str, Any]]) -> List[GraphRelation]:
        """GraphRAGの関係性をフォーマット"""
        relations = []
        
        for edge in edge_results:
            relations.append(GraphRelation(
                target_id=edge.get('inV', ''),
                target_type=edge.get('properties', {}).get('target_type', ''),
                relation_type=edge.get('label', ''),
                relation_properties=edge.get('properties', {}),
                distance=1
            ))
        
        return relations
    
    async def _integrate_results(
        self, 
        traditional_results: List[SearchResult], 
        graph_results: List[SearchResult],
        include_graph_relations: bool
    ) -> List[SearchResult]:
        """検索結果を統合"""
        integrated_results = []
        seen_ids = set()
        
        # 通常RAGの結果を追加
        for result in traditional_results:
            if result.id not in seen_ids:
                integrated_results.append(result)
                seen_ids.add(result.id)
        
        # GraphRAGの結果を追加（重複を避ける）
        for result in graph_results:
            if result.id not in seen_ids:
                # GraphRAGの結果に通常RAGの情報を補完
                if include_graph_relations and result.graph_relations:
                    # 関係性情報を保持
                    pass
                else:
                    result.graph_relations = None
                
                integrated_results.append(result)
                seen_ids.add(result.id)
            else:
                # 既存の結果にGraphRAGの関係性を追加
                for existing_result in integrated_results:
                    if existing_result.id == result.id and include_graph_relations:
                        existing_result.graph_relations = result.graph_relations
                        existing_result.source = SearchResultSource.HYBRID
                        break
        
        # スコアでソート
        integrated_results.sort(key=lambda x: x.score, reverse=True)
        
        return integrated_results
    
    def _create_error_response(self, request: HybridSearchRequest, error_message: str) -> HybridSearchResponse:
        """エラーレスポンスを作成"""
        return HybridSearchResponse(
            search_type=request.search_type,
            query=request.query,
            results=[],
            total_count=0,
            traditional_count=0,
            graph_count=0,
            hybrid_count=0,
            execution_time_ms=0.0
        )
    
    async def get_health_status(self) -> Dict[str, Any]:
        """ヘルスチェック用の状態を取得"""
        cosmos_status = self.cosmos_service.get_health_status()
        gremlin_status = await self.gremlin_service.get_health_status()
        
        return {
            "cosmos_service": cosmos_status,
            "gremlin_service": gremlin_status,
            "hybrid_available": self._gremlin_connected
        }
    
    async def cleanup(self):
        """リソースをクリーンアップ"""
        try:
            await self.gremlin_service.disconnect()
        except Exception as e:
            logger.error(f"クリーンアップエラー: {e}")
