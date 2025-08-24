from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
import os

from app.config import settings
from app.core.logging import setup_logging, get_logger
from app.core.exceptions import (
    BaseAPIException,
    api_exception_handler,
    http_exception_handler,
    general_exception_handler
)
from fastapi import HTTPException

from app.api.analysis import router as analysis_router
from app.api.consultations import router as consultations_router
from app.api.health import router as health_router
from app.api.similar_cases import router as similar_cases_router

# 環境変数を読み込み
load_dotenv()

# タイムゾーン設定
os.environ['TZ'] = settings.timezone
try:
    import time
    time.tzset()
except AttributeError:
    # Windowsではtzset()が利用できないため、パス
    pass

# ログ設定
setup_logging()
logger = get_logger(__name__)

def create_app() -> FastAPI:
    """FastAPIアプリケーションを作成"""
    app = FastAPI(
        title=settings.app_name,
        description="酒税法リスク分析判定システム API",
        version=settings.app_version,
        debug=settings.debug,
    )

    # CORS設定
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=settings.cors_allow_credentials,
        allow_methods=settings.cors_allow_methods,
        allow_headers=settings.cors_allow_headers,
    )

    # 例外ハンドラーの追加
    app.add_exception_handler(BaseAPIException, api_exception_handler)
    app.add_exception_handler(HTTPException, http_exception_handler)
    app.add_exception_handler(Exception, general_exception_handler)

    return app

app = create_app()

# ルーターを追加
app.include_router(analysis_router, prefix="/api", tags=["analysis"])
app.include_router(consultations_router, prefix="/api", tags=["consultations"])
app.include_router(health_router, prefix="/api", tags=["health"])
app.include_router(similar_cases_router, prefix="/api", tags=["similar_cases"])

@app.get("/")
async def root():
    """ルート情報を取得"""
    from app.core.exceptions import create_success_response
    from app.services.mysql_service import mysql_service
    
    data = {
        "message": f"{settings.app_name} is running",
        "version": settings.app_version,
        "environment": settings.environment,
        "features": [
            "企画案分析",
            "相談提案生成",
            "マスタデータ管理"
        ],
        "services": {
            "mysql": mysql_service.is_available(),
            "redis": settings.is_redis_configured(),
            "openai": settings.is_openai_configured()
        }
    }
    
    return create_success_response(data).model_dump()

@app.get("/info")
async def get_info():
    """アプリケーション詳細情報を取得"""
    from app.core.exceptions import create_success_response
    
    data = {
        "name": settings.app_name,
        "version": settings.app_version,
        "description": "酒税法リスク分析判定システム API",
        "environment": settings.environment,
        "endpoints": {
            "analysis": "/api/analyze",
            "consultations": {
                "list": "/api/consultations",
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
    
    return create_success_response(data).model_dump()

if __name__ == "__main__":
    import uvicorn
    logger.info(f"🚀 {settings.app_name} を起動中...")
    uvicorn.run(
        app, 
        host=settings.host, 
        port=settings.port,
        log_level=settings.log_level.lower()
    )
