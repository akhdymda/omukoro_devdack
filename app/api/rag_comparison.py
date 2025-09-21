from fastapi import APIRouter, HTTPException, status
import logging
from typing import Dict, Any

from app.models.rag_comparison import RAGComparisonRequest, RAGComparisonResponse
from app.services.rag_comparison_service import RAGComparisonService
from app.core.exceptions import create_success_response, create_error_response

logger = logging.getLogger(__name__)
router = APIRouter()

# グローバルサービスインスタンス
rag_comparison_service = RAGComparisonService()


@router.post("/compare-rag", response_model=RAGComparisonResponse, summary="RAG比較を実行")
async def compare_rag(request: RAGComparisonRequest):
    """
    従来RAGとハイブリッドRAGを比較します。
    
    - **query**: 検索クエリ
    - **traditional_limit**: 従来RAGの取得件数（デフォルト: 5）
    - **hybrid_max_chunks**: ハイブリッドRAGの最大チャンク数（デフォルト: 5）
    - **hybrid_vector_weight**: ハイブリッドRAGのベクトル検索重み（デフォルト: 0.4）
    - **hybrid_graph_weight**: ハイブリッドRAGのグラフ検索重み（デフォルト: 0.4）
    - **hybrid_keyword_weight**: ハイブリッドRAGのキーワード検索重み（デフォルト: 0.2）
    - **enable_query_expansion**: クエリ拡張を有効にするか（デフォルト: True）
    - **hybrid_max_related_nodes**: ハイブリッドRAGの最大関連ノード数（デフォルト: 10）
    """
    try:
        logger.info(f"RAG比較リクエスト: {request.query}")
        
        result = await rag_comparison_service.compare_rag(request)
        
        logger.info(f"RAG比較完了: 従来RAG {result.traditional_rag.get('total_count', 0)}件, ハイブリッドRAG {result.hybrid_rag.get('total_count', 0)}件")
        return result
        
    except Exception as e:
        logger.error(f"RAG比較エラー: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=create_error_response(f"RAG比較エラー: {str(e)}")
        )


@router.get("/compare-rag/{query}")
async def compare_rag_simple(
    query: str,
    traditional_limit: int = 5,
    hybrid_max_chunks: int = 5,
    hybrid_vector_weight: float = 0.4,
    hybrid_graph_weight: float = 0.4,
    hybrid_keyword_weight: float = 0.2,
    enable_query_expansion: bool = True,
    hybrid_max_related_nodes: int = 10
):
    """RAG比較を実行（シンプル版）"""
    try:
        request = RAGComparisonRequest(
            query=query,
            traditional_limit=traditional_limit,
            hybrid_max_chunks=hybrid_max_chunks,
            hybrid_vector_weight=hybrid_vector_weight,
            hybrid_graph_weight=hybrid_graph_weight,
            hybrid_keyword_weight=hybrid_keyword_weight,
            enable_query_expansion=enable_query_expansion,
            hybrid_max_related_nodes=hybrid_max_related_nodes
        )
        
        result = await rag_comparison_service.compare_rag(request)
        return result
        
    except Exception as e:
        logger.error(f"RAG比較エラー（シンプル）: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=create_error_response(f"RAG比較エラー: {str(e)}")
        )


@router.get("/compare-rag/test/{query}")
async def test_rag_comparison(
    query: str,
    traditional_limit: int = 3,
    hybrid_max_chunks: int = 3
):
    """RAG比較のテスト"""
    try:
        request = RAGComparisonRequest(
            query=query,
            traditional_limit=traditional_limit,
            hybrid_max_chunks=hybrid_max_chunks,
            enable_query_expansion=True
        )
        
        result = await rag_comparison_service.compare_rag(request)
        
        return create_success_response({
            "query": result.query,
            "traditional_count": result.traditional_rag.get("total_count", 0),
            "hybrid_count": result.hybrid_rag.get("total_count", 0),
            "execution_time_ms": result.total_execution_time_ms,
            "comparison_summary": result.comparison_metrics.get("summary", {}),
            "success": result.success
        })
        
    except Exception as e:
        logger.error(f"RAG比較テストエラー: {e}")
        return create_error_response(f"RAG比較テストエラー: {str(e)}")


@router.get("/compare-rag/demo/{query}")
async def demo_rag_comparison(query: str):
    """RAG比較のデモ"""
    try:
        # デモ用の設定
        request = RAGComparisonRequest(
            query=query,
            traditional_limit=3,  # デモ用に少なく
            hybrid_max_chunks=3,  # デモ用に少なく
            hybrid_vector_weight=0.3,
            hybrid_graph_weight=0.5,  # グラフ検索を重視
            hybrid_keyword_weight=0.2,
            enable_query_expansion=True,
            hybrid_max_related_nodes=5
        )
        
        result = await rag_comparison_service.compare_rag(request)
        
        # デモ用のレスポンス
        demo_response = {
            "query": result.query,
            "traditional_rag": {
                "count": result.traditional_rag.get("total_count", 0),
                "execution_time_ms": result.traditional_rag.get("execution_time_ms", 0),
                "chunks_preview": [
                    {
                        "chunk_id": chunk.get("chunk_id", ""),
                        "prefLabel": chunk.get("prefLabel", ""),
                        "text": chunk.get("text", "")[:100] + "..." if len(chunk.get("text", "")) > 100 else chunk.get("text", ""),
                        "score": round(chunk.get("score", 0), 3)
                    }
                    for chunk in result.traditional_rag.get("chunks", [])[:2]  # 最初の2件のみ
                ]
            },
            "hybrid_rag": {
                "count": result.hybrid_rag.get("total_count", 0),
                "execution_time_ms": result.hybrid_rag.get("execution_time_ms", 0),
                "expanded_query": result.hybrid_rag.get("expanded_query", ""),
                "chunks_preview": [
                    {
                        "id": chunk.get("id", ""),
                        "content": chunk.get("content", "")[:100] + "..." if len(chunk.get("content", "")) > 100 else chunk.get("content", ""),
                        "search_type": chunk.get("search_type", ""),
                        "score": round(chunk.get("score", 0), 3)
                    }
                    for chunk in result.hybrid_rag.get("final_chunks", [])[:2]  # 最初の2件のみ
                ]
            },
            "comparison_summary": result.comparison_metrics.get("summary", {}),
            "total_execution_time_ms": round(result.total_execution_time_ms, 2),
            "success": result.success
        }
        
        return create_success_response(demo_response)
        
    except Exception as e:
        logger.error(f"RAG比較デモエラー: {e}")
        return create_error_response(f"RAG比較デモエラー: {str(e)}")


@router.get("/compare-rag/health")
async def get_rag_comparison_health():
    """RAG比較サービスのヘルスチェック"""
    try:
        health_status = await rag_comparison_service.get_health_status()
        return create_success_response(health_status)
        
    except Exception as e:
        logger.error(f"ヘルスチェックエラー: {e}")
        return create_error_response(f"ヘルスチェックエラー: {str(e)}")

