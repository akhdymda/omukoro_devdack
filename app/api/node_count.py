from fastapi import APIRouter, HTTPException
import logging
from app.models.node_count import NodeCountRequest, NodeCountResponse
from app.services.node_count_service import NodeCountService

logger = logging.getLogger(__name__)
router = APIRouter()

# グローバルサービスインスタンス
node_count_service = NodeCountService()


@router.post("/node-count", response_model=NodeCountResponse)
async def count_related_nodes(request: NodeCountRequest):
    """指定されたノードの距離1の双方向関連ノード数をカウント"""
    try:
        logger.info(f"ノード数カウントリクエスト: {request.node_id}")
        
        result = await node_count_service.count_related_nodes(request.node_id)
        
        logger.info(f"ノード数カウント完了: {result.related_nodes_count}件")
        return result
        
    except Exception as e:
        logger.error(f"ノード数カウントエラー: {e}")
        raise HTTPException(status_code=500, detail=f"ノード数カウントエラー: {str(e)}")


@router.get("/node-count/{node_id}")
async def count_related_nodes_simple(node_id: str):
    """指定されたノードの距離1の双方向関連ノード数をカウント（シンプル版）"""
    try:
        logger.info(f"ノード数カウントリクエスト（シンプル）: {node_id}")
        
        result = await node_count_service.count_related_nodes(node_id)
        
        logger.info(f"ノード数カウント完了（シンプル）: {result.related_nodes_count}件")
        return result
        
    except Exception as e:
        logger.error(f"ノード数カウントエラー（シンプル）: {e}")
        raise HTTPException(status_code=500, detail=f"ノード数カウントエラー: {str(e)}")


@router.get("/node-count/health")
async def get_node_count_health():
    """ノード数カウントサービスのヘルスチェック"""
    try:
        health_status = await node_count_service.get_health_status()
        
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


@router.get("/node-count/test/{node_id}")
async def test_node_count(node_id: str):
    """ノード数カウントのテスト"""
    try:
        logger.info(f"ノード数カウントテスト: {node_id}")
        
        result = await node_count_service.count_related_nodes(node_id)
        
        return {
            "success": True,
            "message": f"ノード '{node_id}' の関連ノード数カウントテスト完了",
            "result": result
        }
        
    except Exception as e:
        logger.error(f"ノード数カウントテストエラー: {e}")
        return {
            "success": False,
            "message": f"ノード数カウントテストエラー: {str(e)}"
        }



