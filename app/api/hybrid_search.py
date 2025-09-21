from fastapi import APIRouter, HTTPException, Query
from typing import Optional
import logging
from app.models.hybrid_search import (
    HybridSearchRequest, 
    HybridSearchResponse, 
    SearchType
)
from app.services.hybrid_search_service import HybridSearchService

logger = logging.getLogger(__name__)

router = APIRouter()

# ハイブリッド検索サービスのインスタンス
hybrid_search_service = HybridSearchService()

@router.post("/hybrid-search", response_model=HybridSearchResponse)
async def hybrid_search(request: HybridSearchRequest):
    """
    ハイブリッド検索を実行する
    
    Args:
        request: ハイブリッド検索リクエスト
        
    Returns:
        HybridSearchResponse: 検索結果
        
    Raises:
        HTTPException: 検索エラーの場合
    """
    try:
        # サービスを初期化（初回のみ）
        if not hasattr(hybrid_search_service, '_initialized'):
            await hybrid_search_service.initialize()
            hybrid_search_service._initialized = True
        
        # ハイブリッド検索を実行
        result = await hybrid_search_service.search(request)
        
        logger.info(f"ハイブリッド検索完了: {result.search_type}, 結果数: {result.total_count}")
        return result
        
    except Exception as e:
        logger.error(f"ハイブリッド検索APIエラー: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"ハイブリッド検索中にエラーが発生しました: {str(e)}"
        )

@router.get("/hybrid-search/health")
async def get_hybrid_search_health():
    """
    ハイブリッド検索サービスのヘルスチェック
    
    Returns:
        dict: サービス状態情報
    """
    try:
        if not hasattr(hybrid_search_service, '_initialized'):
            await hybrid_search_service.initialize()
            hybrid_search_service._initialized = True
        
        health_status = await hybrid_search_service.get_health_status()
        
        return {
            "status": "healthy" if health_status.get("hybrid_available", False) else "degraded",
            "services": health_status
        }
        
    except Exception as e:
        logger.error(f"ヘルスチェックエラー: {e}")
        return {
            "status": "unhealthy",
            "error": str(e)
        }

@router.get("/hybrid-search/test")
async def test_hybrid_search(
    query: str = Query("酒税法 販売業者", description="テスト用検索クエリ"),
    search_type: SearchType = Query(SearchType.HYBRID, description="検索タイプ")
):
    """
    ハイブリッド検索のテスト用エンドポイント
    
    Args:
        query: 検索クエリ
        search_type: 検索タイプ
        
    Returns:
        HybridSearchResponse: テスト検索結果
    """
    try:
        # テスト用リクエストを作成
        test_request = HybridSearchRequest(
            query=query,
            search_type=search_type,
            limit=5,
            include_graph_relations=True
        )
        
        # サービスを初期化（初回のみ）
        if not hasattr(hybrid_search_service, '_initialized'):
            await hybrid_search_service.initialize()
            hybrid_search_service._initialized = True
        
        # テスト検索を実行
        result = await hybrid_search_service.search(test_request)
        
        logger.info(f"テスト検索完了: {result.search_type}, 結果数: {result.total_count}")
        return result
        
    except Exception as e:
        logger.error(f"テスト検索エラー: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"テスト検索中にエラーが発生しました: {str(e)}"
        )

@router.get("/hybrid-search/available-types")
async def get_available_search_types():
    """
    利用可能な検索タイプを取得
    
    Returns:
        dict: 利用可能な検索タイプの情報
    """
    try:
        # サービスを初期化（初回のみ）
        if not hasattr(hybrid_search_service, '_initialized'):
            await hybrid_search_service.initialize()
            hybrid_search_service._initialized = True
        
        health_status = await hybrid_search_service.get_health_status()
        
        available_types = {
            "traditional": True,  # 通常RAGは常に利用可能
            "hybrid": health_status.get("hybrid_available", False)
        }
        
        return {
            "available_types": available_types,
            "recommended_type": "hybrid" if available_types["hybrid"] else "traditional",
            "services_status": health_status
        }
        
    except Exception as e:
        logger.error(f"検索タイプ取得エラー: {e}")
        return {
            "available_types": {
                "traditional": True,
                "hybrid": False
            },
            "recommended_type": "traditional",
            "error": str(e)
        }



