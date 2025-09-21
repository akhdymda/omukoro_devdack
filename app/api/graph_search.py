from fastapi import APIRouter, HTTPException, Depends
from typing import Dict, Any
import logging
from app.models.graph_search import GraphSearchRequest, GraphSearchResponse, GraphSearchHealthResponse
from app.services.graph_search_service import GraphSearchService

logger = logging.getLogger(__name__)
router = APIRouter()

# グローバルサービスインスタンス
graph_search_service = GraphSearchService()


@router.post("/graph-search", response_model=GraphSearchResponse)
async def search_graph(request: GraphSearchRequest):
    """Graph検索を実行"""
    try:
        logger.info(f"Graph検索リクエスト: {request.query}")
        
        result = await graph_search_service.search(
            query=request.query,
            limit=10
        )
        
        logger.info(f"Graph検索完了: {result.total_count}件の結果")
        return result
        
    except Exception as e:
        logger.error(f"Graph検索エラー: {e}")
        raise HTTPException(status_code=500, detail=f"Graph検索エラー: {str(e)}")


@router.get("/graph-search/health", response_model=GraphSearchHealthResponse)
async def get_graph_search_health():
    """Graph検索サービスのヘルスチェック"""
    try:
        health_status = await graph_search_service.get_health_status()
        
        return GraphSearchHealthResponse(
            status=health_status.get("status", "unknown"),
            gremlin_connected=health_status.get("gremlin_connected", False),
            vertex_count=health_status.get("vertex_count"),
            error=health_status.get("error")
        )
        
    except Exception as e:
        logger.error(f"ヘルスチェックエラー: {e}")
        return GraphSearchHealthResponse(
            status="error",
            gremlin_connected=False,
            error=str(e)
        )


@router.get("/graph-search/debug")
async def debug_graph_search():
    """Graph検索のデバッグ情報を取得"""
    try:
        from app.config import settings
        
        return {
            "gremlin_endpoint": settings.gremlin_endpoint,
            "gremlin_auth_key": "***" if settings.gremlin_auth_key else None,
            "gremlin_database": settings.gremlin_database,
            "gremlin_graph": settings.gremlin_graph,
            "all_configured": all([
                settings.gremlin_endpoint,
                settings.gremlin_auth_key,
                settings.gremlin_database,
                settings.gremlin_graph
            ])
        }
        
    except Exception as e:
        logger.error(f"デバッグ情報取得エラー: {e}")
        return {"error": str(e)}


@router.post("/graph-search/test-connection")
async def test_gremlin_connection():
    """Gremlin接続テスト"""
    try:
        # サービスを初期化
        success = await graph_search_service.initialize()
        
        if success:
            # 簡単なクエリを実行
            result = await graph_search_service.search("test", limit=1)
            
            return {
                "success": True,
                "message": "Gremlin接続テスト成功",
                "vertex_count": result.total_count
            }
        else:
            return {
                "success": False,
                "message": "Gremlin接続テスト失敗"
            }
            
    except Exception as e:
        logger.error(f"接続テストエラー: {e}")
        return {
            "success": False,
            "message": f"接続テストエラー: {str(e)}"
        }




