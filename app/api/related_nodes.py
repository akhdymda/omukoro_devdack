from fastapi import APIRouter, HTTPException
from typing import List, Optional
import logging
from app.models.related_nodes import (
    RelatedNodesRequest, RelatedNodesResponse,
    RelatedNodesByKeywordsRequest, RelatedNodesByKeywordsResponse
)
from app.services.related_nodes_service import RelatedNodesService

logger = logging.getLogger(__name__)
router = APIRouter()

# グローバルサービスインスタンス
related_nodes_service = RelatedNodesService()


@router.post("/related-nodes", response_model=RelatedNodesResponse)
async def get_related_nodes(request: RelatedNodesRequest):
    """指定されたノードの関連ノードを抽出"""
    try:
        logger.info(f"関連ノード抽出リクエスト: {request.node_id}, 距離: {request.max_distance}")
        
        result = await related_nodes_service.get_related_nodes(
            node_id=request.node_id,
            max_distance=request.max_distance,
            max_results=request.max_results,
            relationship_types=request.relationship_types
        )
        
        logger.info(f"関連ノード抽出完了: {result.total_count}件の結果")
        return result
        
    except Exception as e:
        logger.error(f"関連ノード抽出エラー: {e}")
        raise HTTPException(status_code=500, detail=f"関連ノード抽出エラー: {str(e)}")


@router.post("/related-nodes/by-keywords", response_model=RelatedNodesByKeywordsResponse)
async def get_related_nodes_by_keywords(request: RelatedNodesByKeywordsRequest):
    """キーワードから関連ノードを抽出"""
    try:
        logger.info(f"キーワード関連ノード抽出リクエスト: {request.keywords}")
        
        result = await related_nodes_service.get_related_nodes_by_keywords(
            keywords=request.keywords,
            max_distance=request.max_distance,
            max_results_per_keyword=request.max_results_per_keyword,
            relationship_types=request.relationship_types
        )
        
        logger.info(f"キーワード関連ノード抽出完了: {result.total_count}件の結果")
        return result
        
    except Exception as e:
        logger.error(f"キーワード関連ノード抽出エラー: {e}")
        raise HTTPException(status_code=500, detail=f"キーワード関連ノード抽出エラー: {str(e)}")


@router.get("/related-nodes/health")
async def get_related_nodes_health():
    """関連ノード抽出サービスのヘルスチェック"""
    try:
        health_status = await related_nodes_service.get_health_status()
        
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


@router.post("/related-nodes/test/{node_id}")
async def test_related_nodes_extraction(node_id: str, max_distance: int = 2):
    """関連ノード抽出のテスト"""
    try:
        logger.info(f"関連ノード抽出テスト: {node_id}")
        
        result = await related_nodes_service.get_related_nodes(
            node_id=node_id,
            max_distance=max_distance,
            max_results=10
        )
        
        return {
            "success": True,
            "message": f"ノード '{node_id}' の関連ノード抽出テスト完了",
            "result": result
        }
        
    except Exception as e:
        logger.error(f"関連ノード抽出テストエラー: {e}")
        return {
            "success": False,
            "message": f"関連ノード抽出テストエラー: {str(e)}"
        }


@router.post("/related-nodes/test-keywords")
async def test_keywords_related_nodes_extraction(keywords: List[str]):
    """キーワード関連ノード抽出のテスト"""
    try:
        logger.info(f"キーワード関連ノード抽出テスト: {keywords}")
        
        result = await related_nodes_service.get_related_nodes_by_keywords(
            keywords=keywords,
            max_distance=2,
            max_results_per_keyword=5
        )
        
        return {
            "success": True,
            "message": f"キーワード {keywords} の関連ノード抽出テスト完了",
            "result": result
        }
        
    except Exception as e:
        logger.error(f"キーワード関連ノード抽出テストエラー: {e}")
        return {
            "success": False,
            "message": f"キーワード関連ノード抽出テストエラー: {str(e)}"
        }




