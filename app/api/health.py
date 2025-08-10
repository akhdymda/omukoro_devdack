from fastapi import APIRouter

router = APIRouter()

@router.get("/health")
async def health_check():
    """
    アプリケーションの健康状態をチェック
    """
    return {
        "status": "healthy",
        "message": "Sherpath API is running properly"
    } 