"""
カスタム例外クラスとエラーハンドリング
"""
from fastapi import HTTPException, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import Optional, Any
import logging

logger = logging.getLogger(__name__)

class ErrorDetail(BaseModel):
    """エラー詳細情報"""
    error_code: str
    message: str
    details: Optional[Any] = None

class APIResponse(BaseModel):
    """標準APIレスポンス形式"""
    success: bool
    data: Optional[Any] = None
    error: Optional[ErrorDetail] = None

# カスタム例外クラス
class BaseAPIException(Exception):
    """APIベース例外クラス"""
    def __init__(
        self, 
        error_code: str, 
        message: str, 
        status_code: int = 500,
        details: Optional[Any] = None
    ):
        self.error_code = error_code
        self.message = message
        self.status_code = status_code
        self.details = details
        super().__init__(message)

class DatabaseConnectionError(BaseAPIException):
    """データベース接続エラー"""
    def __init__(self, message: str = "データベース接続に失敗しました", details: Optional[Any] = None):
        super().__init__(
            error_code="DATABASE_CONNECTION_ERROR",
            message=message,
            status_code=500,
            details=details
        )

class ValidationError(BaseAPIException):
    """バリデーションエラー"""
    def __init__(self, message: str = "入力データが無効です", details: Optional[Any] = None):
        super().__init__(
            error_code="VALIDATION_ERROR",
            message=message,
            status_code=400,
            details=details
        )

class NotFoundError(BaseAPIException):
    """リソースが見つからないエラー"""
    def __init__(self, message: str = "指定されたリソースが見つかりません", details: Optional[Any] = None):
        super().__init__(
            error_code="NOT_FOUND",
            message=message,
            status_code=404,
            details=details
        )

class ExternalServiceError(BaseAPIException):
    """外部サービスエラー"""
    def __init__(self, service_name: str, message: str = "外部サービスでエラーが発生しました", details: Optional[Any] = None):
        super().__init__(
            error_code=f"{service_name.upper()}_SERVICE_ERROR",
            message=f"{service_name}: {message}",
            status_code=502,
            details=details
        )

# エラーハンドラー
async def api_exception_handler(request: Request, exc: BaseAPIException) -> JSONResponse:
    """カスタム例外ハンドラー"""
    logger.error(f"API Exception: {exc.error_code} - {exc.message}", extra={"details": exc.details})
    
    response = APIResponse(
        success=False,
        error=ErrorDetail(
            error_code=exc.error_code,
            message=exc.message,
            details=exc.details
        )
    )
    
    return JSONResponse(
        status_code=exc.status_code,
        content=response.model_dump()
    )

async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    """HTTPException ハンドラー"""
    logger.error(f"HTTP Exception: {exc.status_code} - {exc.detail}")
    
    response = APIResponse(
        success=False,
        error=ErrorDetail(
            error_code="HTTP_ERROR",
            message=str(exc.detail),
            details={"status_code": exc.status_code}
        )
    )
    
    return JSONResponse(
        status_code=exc.status_code,
        content=response.model_dump()
    )

async def general_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """一般的な例外ハンドラー"""
    logger.error(f"Unexpected error: {type(exc).__name__} - {str(exc)}", exc_info=True)
    
    response = APIResponse(
        success=False,
        error=ErrorDetail(
            error_code="INTERNAL_SERVER_ERROR",
            message="内部サーバーエラーが発生しました",
            details={"exception_type": type(exc).__name__}
        )
    )
    
    return JSONResponse(
        status_code=500,
        content=response.model_dump()
    )

def create_success_response(data: Any = None) -> APIResponse:
    """成功レスポンスを作成"""
    return APIResponse(success=True, data=data)

def create_error_response(error_code: str, message: str, details: Optional[Any] = None) -> APIResponse:
    """エラーレスポンスを作成"""
    return APIResponse(
        success=False,
        error=ErrorDetail(
            error_code=error_code,
            message=message,
            details=details
        )
    )