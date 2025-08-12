from fastapi import APIRouter
from app.services.cosmos_service import CosmosService
from app.services.consultation_service import ConsultationService
from app.services.cache_service import CacheService
import logging

logger = logging.getLogger(__name__)

router = APIRouter()

@router.get("/health")
async def health_check():
    """
    ヘルスチェックエンドポイント
    """
    try:
        # 各サービスの状態を確認
        cosmos_service = CosmosService()
        consultation_service = ConsultationService()
        cache_service = CacheService()
        
        cosmos_status = cosmos_service.get_health_status()
        consultation_status = consultation_service.get_health_status()
        cache_status = cache_service.get_health_status()
        
        # 全体的な健康状態を判定
        overall_healthy = (
            cosmos_status.get("mongodb_connected", False) and
            cosmos_status.get("bm25_initialized", False) and
            consultation_status.get("openai_configured", False)
        )
        
        return {
            "status": "healthy" if overall_healthy else "degraded",
            "timestamp": "2025-08-12T22:00:00Z",
            "services": {
                "cosmos": cosmos_status,
                "consultation": consultation_status,
                "cache": cache_status
            },
            "overall_status": {
                "mongodb": cosmos_status.get("mongodb_connected", False),
                "bm25": cosmos_status.get("bm25_initialized", False),
                "openai": consultation_status.get("openai_configured", False)
            }
        }
        
    except Exception as e:
        logger.error(f"ヘルスチェックエラー: {e}")
        return {
            "status": "unhealthy",
            "error": str(e),
            "timestamp": "2025-08-12T22:00:00Z"
        }
