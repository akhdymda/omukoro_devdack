from fastapi import APIRouter, HTTPException, status
import logging
from typing import Dict, Any

from app.models.hybrid_rag import (
    HybridSearchRequest, HybridSearchResponse, 
    QueryExpansionRequest, QueryExpansionResponse
)
from app.services.hybrid_rag_service import HybridRAGService
from app.core.exceptions import create_success_response, create_error_response

logger = logging.getLogger(__name__)
router = APIRouter()

# グローバルサービスインスタンス
hybrid_rag_service = HybridRAGService()


@router.post("/hybrid-rag-search", response_model=HybridSearchResponse, summary="ハイブリッドRAG検索を実行")
async def hybrid_search(request: HybridSearchRequest):
    """
    ベクトル検索、グラフ検索、キーワード検索を組み合わせたハイブリッド検索を実行します。
    
    - **query**: 検索クエリ
    - **max_chunks**: 最大チャンク数（デフォルト: 5）
    - **vector_weight**: ベクトル検索の重み（デフォルト: 0.4）
    - **graph_weight**: グラフ検索の重み（デフォルト: 0.4）
    - **keyword_weight**: キーワード検索の重み（デフォルト: 0.2）
    - **enable_query_expansion**: クエリ拡張を有効にするか（デフォルト: True）
    - **max_related_nodes**: 最大関連ノード数（デフォルト: 10）
    """
    try:
        logger.info(f"ハイブリッド検索リクエスト: {request.query}")
        
        result = await hybrid_rag_service.hybrid_search(request)
        
        logger.info(f"ハイブリッド検索完了: {len(result.final_chunks)}件のチャンク")
        return result
        
    except Exception as e:
        logger.error(f"ハイブリッド検索エラー: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=create_error_response(f"ハイブリッド検索エラー: {str(e)}")
        )


@router.post("/hybrid-rag-query-expansion", response_model=QueryExpansionResponse, summary="ハイブリッドRAGクエリ拡張を実行")
async def expand_query(request: QueryExpansionRequest):
    """
    クエリを拡張して関連キーワードを追加します。
    
    - **query**: 元のクエリ
    - **max_related_nodes**: 最大関連ノード数（デフォルト: 10）
    """
    try:
        logger.info(f"クエリ拡張リクエスト: {request.query}")
        
        result = await hybrid_rag_service.expand_query(request)
        
        logger.info(f"クエリ拡張完了: {len(result.keywords)}個のキーワード")
        return result
        
    except Exception as e:
        logger.error(f"クエリ拡張エラー: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=create_error_response(f"クエリ拡張エラー: {str(e)}")
        )


@router.get("/hybrid-rag-search/{query}")
async def hybrid_search_simple(
    query: str,
    max_chunks: int = 5,
    vector_weight: float = 0.4,
    graph_weight: float = 0.4,
    keyword_weight: float = 0.2,
    enable_query_expansion: bool = True,
    max_related_nodes: int = 10
):
    """ハイブリッド検索を実行（シンプル版）"""
    try:
        request = HybridSearchRequest(
            query=query,
            max_chunks=max_chunks,
            vector_weight=vector_weight,
            graph_weight=graph_weight,
            keyword_weight=keyword_weight,
            enable_query_expansion=enable_query_expansion,
            max_related_nodes=max_related_nodes
        )
        
        result = await hybrid_rag_service.hybrid_search(request)
        return result
        
    except Exception as e:
        logger.error(f"ハイブリッド検索エラー（シンプル）: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=create_error_response(f"ハイブリッド検索エラー: {str(e)}")
        )


@router.get("/hybrid-rag-query-expansion/{query}")
async def expand_query_simple(
    query: str,
    max_related_nodes: int = 10
):
    """クエリ拡張を実行（シンプル版）"""
    try:
        request = QueryExpansionRequest(
            query=query,
            max_related_nodes=max_related_nodes
        )
        
        result = await hybrid_rag_service.expand_query(request)
        return result
        
    except Exception as e:
        logger.error(f"クエリ拡張エラー（シンプル）: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=create_error_response(f"クエリ拡張エラー: {str(e)}")
        )


@router.get("/hybrid-rag-search/test/{query}")
async def test_hybrid_search(
    query: str,
    max_chunks: int = 5
):
    """ハイブリッド検索のテスト"""
    try:
        request = HybridSearchRequest(
            query=query,
            max_chunks=max_chunks,
            enable_query_expansion=True
        )
        
        result = await hybrid_rag_service.hybrid_search(request)
        
        return create_success_response({
            "query": result.query,
            "expanded_query": result.expanded_query,
            "final_chunks_count": len(result.final_chunks),
            "search_results_summary": {
                search_type: {
                    "count": search_result.total_count,
                    "execution_time_ms": search_result.execution_time_ms
                }
                for search_type, search_result in result.search_results.items()
            },
            "total_execution_time_ms": result.total_execution_time_ms,
            "success": result.success
        })
        
    except Exception as e:
        logger.error(f"ハイブリッド検索テストエラー: {e}")
        return create_error_response(f"ハイブリッド検索テストエラー: {str(e)}")


@router.get("/hybrid-rag-search/health")
async def get_hybrid_rag_health():
    """ハイブリッドRAGサービスのヘルスチェック"""
    try:
        health_status = await hybrid_rag_service.get_health_status()
        return create_success_response(health_status)
        
    except Exception as e:
        logger.error(f"ヘルスチェックエラー: {e}")
        return create_error_response(f"ヘルスチェックエラー: {str(e)}")


@router.get("/hybrid-rag-search/demo/{query}")
async def demo_hybrid_search(query: str):
    """ハイブリッド検索のデモ"""
    try:
        # デモ用の設定
        request = HybridSearchRequest(
            query=query,
            max_chunks=3,  # デモ用に少なく
            vector_weight=0.3,
            graph_weight=0.5,  # グラフ検索を重視
            keyword_weight=0.2,
            enable_query_expansion=True,
            max_related_nodes=5
        )
        
        result = await hybrid_rag_service.hybrid_search(request)
        
        # デモ用のレスポンス
        demo_response = {
            "query": result.query,
            "expanded_query": result.expanded_query,
            "final_chunks": [
                {
                    "id": chunk.id,
                    "content": chunk.content[:200] + "..." if len(chunk.content) > 200 else chunk.content,
                    "source": chunk.source,
                    "score": round(chunk.score, 3),
                    "search_type": chunk.search_type,
                    "node_id": chunk.node_id
                }
                for chunk in result.final_chunks
            ],
            "search_summary": {
                "total_chunks": len(result.final_chunks),
                "vector_results": result.search_results.get("vector", {}).get("total_count", 0),
                "graph_results": result.search_results.get("graph", {}).get("total_count", 0),
                "keyword_results": result.search_results.get("keyword", {}).get("total_count", 0),
                "execution_time_ms": round(result.total_execution_time_ms, 2)
            },
            "success": result.success
        }
        
        return create_success_response(demo_response)
        
    except Exception as e:
        logger.error(f"ハイブリッド検索デモエラー: {e}")
        return create_error_response(f"ハイブリッド検索デモエラー: {str(e)}")
