from fastapi import APIRouter, HTTPException
import logging
from app.models.nodes_info import NodesInfoRequest, NodesInfoResponse
from app.services.nodes_info_service import NodesInfoService

logger = logging.getLogger(__name__)
router = APIRouter()

# グローバルサービスインスタンス
nodes_info_service = NodesInfoService()


@router.post("/nodes-info", response_model=NodesInfoResponse)
async def get_related_nodes_info(request: NodesInfoRequest):
    """指定されたノードの距離1の双方向関連ノード情報を取得"""
    try:
        logger.info(f"ノード情報取得リクエスト: {request.node_id}")
        
        result = await nodes_info_service.get_related_nodes_info(
            request.node_id, 
            request.max_results
        )
        
        logger.info(f"ノード情報取得完了: {result.total_count}件")
        return result
        
    except Exception as e:
        logger.error(f"ノード情報取得エラー: {e}")
        raise HTTPException(status_code=500, detail=f"ノード情報取得エラー: {str(e)}")


@router.get("/nodes-info/{node_id}")
async def get_related_nodes_info_simple(node_id: str, max_results: int = 20):
    """指定されたノードの距離1の双方向関連ノード情報を取得（シンプル版）"""
    try:
        logger.info(f"ノード情報取得リクエスト（シンプル）: {node_id}")
        
        result = await nodes_info_service.get_related_nodes_info(node_id, max_results)
        
        logger.info(f"ノード情報取得完了（シンプル）: {result.total_count}件")
        return result
        
    except Exception as e:
        logger.error(f"ノード情報取得エラー（シンプル）: {e}")
        raise HTTPException(status_code=500, detail=f"ノード情報取得エラー: {str(e)}")


@router.get("/nodes-info/health")
async def get_nodes_info_health():
    """ノード情報取得サービスのヘルスチェック"""
    try:
        health_status = await nodes_info_service.get_health_status()
        
        return {
            "status": health_status.get("status", "unknown"),
            "gremlin_connected": health_status.get("gremlin_connected", False),
            "vertex_count": health_status.get("vertex_count"),
            "error": health_status.get("error")
        }
        
    except Exception as e:
        logger.error(f"ヘルスチェックエラー: {e}")
        return {
            "status": "error",
            "gremlin_connected": False,
            "error": str(e)
        }


@router.get("/nodes-info/test/{node_id}")
async def test_nodes_info(node_id: str, max_results: int = 20):
    """ノード情報取得のテスト"""
    try:
        logger.info(f"ノード情報取得テスト: {node_id}")
        
        result = await nodes_info_service.get_related_nodes_info(node_id, max_results)
        
        return {
            "success": True,
            "message": f"ノード '{node_id}' の関連ノード情報取得テスト完了",
            "result": result
        }
        
    except Exception as e:
        logger.error(f"ノード情報取得テストエラー: {e}")
        return {
            "success": False,
            "message": f"ノード情報取得テストエラー: {str(e)}"
        }



