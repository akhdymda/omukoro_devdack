from fastapi import APIRouter
from datetime import datetime

router = APIRouter()

@router.get("/health")
async def health_check():
    """
    シンプルなヘルスチェックエンドポイント
    APIサーバーが正常に動作していることを確認
    """
    return {
        "status": "ok",
        "timestamp": datetime.now().isoformat(),
        "service": "Sherpath API"
    }
