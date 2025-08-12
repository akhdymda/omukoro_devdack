from fastapi import APIRouter, HTTPException, UploadFile, File, Form
from typing import List
from app.models.analysis import (
    AnalysisRequest,
    AnalysisResponse,
    FileUploadResponse,
    FileAnalysisRequest,
    AnalyticsRequest,
    AnalyticsResponse,
    ExtractTextResponse,
    ExtractedFileInfo,
)
from app.services.analysis_service import AnalysisService
from app.services.analytics_service import AnalyticsService
from app.services.ocr_service import DocumentService
from typing import List, Optional
import logging

logger = logging.getLogger(__name__)

router = APIRouter()

# 分析サービスのインスタンス
analysis_service = AnalysisService()
document_service = DocumentService()
analytics_service = AnalyticsService()

@router.post("/analyze", response_model=AnalysisResponse)
async def analyze_input(request: AnalysisRequest):
    """
    入力されたテキストの充実度を分析する
    
    Args:
        request: 分析リクエスト（テキスト）
        
    Returns:
        AnalysisResponse: 分析結果
        
    Raises:
        HTTPException: 分析エラーの場合
    """
    try:
        # text も docText も空なら早期リターン
        if (not request.text or len(request.text.strip()) == 0) and (
            not getattr(request, "docText", None) or len(request.docText.strip()) == 0
        ):
            return AnalysisResponse(
                completeness=1,
                suggestions=["相談内容を入力してください"],
                confidence=1.0
            )
        
        # 分析実行
        result = await analysis_service.analyze_input_completeness(request)
        return result
        
    except HTTPException:
        # HTTPExceptionはそのまま再送出
        raise
    except Exception as e:
        logger.error(f"Analysis error: {e}")
        raise HTTPException(
            status_code=500,
            detail="分析処理中にエラーが発生しました"
        )

@router.get("/analyze/test")
async def test_analysis():
    """
    分析機能のテスト用エンドポイント
    """
    test_request = AnalysisRequest(
        text="新しいモバイルアプリを開発したいと考えています。ターゲットは20代の学生です。"
    )
    
    try:
        result = await analysis_service.analyze_input_completeness(test_request)
        return {
            "message": "テスト実行成功",
            "result": result
        }
    except Exception as e:
        return {
            "message": "テスト実行失敗",
            "error": str(e)
        }
