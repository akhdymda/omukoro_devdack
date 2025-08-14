from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
import os
import logging

from app.api.analysis import router as analysis_router
from app.api.consultations import router as consultations_router
from app.api.health import router as health_router

# 環境変数を読み込み
load_dotenv()

# ログ設定
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Sherpath API (統合版)",
    description="企画案の論点整理と相談先提案API + 法令検索機能",
    version="1.0.0",
)

# CORS設定（本番環境では適切なオリジンを指定することを推奨）
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 本番環境では具体的なドメインを指定
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["*"],
)

# ルーターを追加
app.include_router(analysis_router, prefix="/api", tags=["analysis"])
app.include_router(consultations_router, prefix="/api", tags=["consultations"])
app.include_router(health_router, prefix="/api", tags=["health"])

@app.get("/")
async def root():
    return {
        "message": "Sherpath API (統合版) is running",
        "version": "1.0.0",
        "features": [
            "企画案分析",
            "法令検索",
            "相談提案生成"
        ]
    }

@app.get("/info")
async def get_info():
    """アプリケーション情報を取得"""
    return {
        "name": "Sherpath API (統合版)",
        "version": "1.0.0",
        "description": "omukoro_devdack_clone + sherpath_backend の統合版",
        "endpoints": {
            "analysis": "/api/analyze",
            "consultations": {
                "list": "/api/consultations",
                "detail": "/api/consultations/{id}",
                "search": "/api/consultations/search",
                "generate": "/api/consultations/generate-suggestions"
            },
            "master_data": {
                "industries": "/api/master/industries",
                "alcohol_types": "/api/master/alcohol-types"
            },
            "health": "/api/health"
        }
    }

if __name__ == "__main__":
    import uvicorn
    logger.info("🚀 Sherpath API (統合版) を起動中...")
    uvicorn.run(app, host="0.0.0.0", port=8000)
