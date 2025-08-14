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

@router.post("/extract_text", response_model=ExtractTextResponse)
async def extract_text(files: List[UploadFile] = File(..., alias="files[]")):
    """
    Word(.docx)/Excel(.xlsx) の複数ファイルからテキスト抽出

    制限:
      - 1ファイル最大10MB
      - 同時最大3ファイル
      - 対応拡張子: .docx/.xlsx のみ
    """
    try:
        # ファイル数バリデーション
        document_service.validate_file_count(0, new_files_count=len(files))

        extracted_parts: List[str] = []
        file_infos: List[ExtractedFileInfo] = []

        for f in files:
            content = await f.read()
            # バリデーション
            document_service.validate_file(f.filename or "", len(content))
            # 抽出
            text = await document_service.extract_text_from_file(content, f.filename or "")
            extracted_parts.append(text)
            file_infos.append(ExtractedFileInfo(name=f.filename or "", bytes=len(content)))

        combined_text = "\n\n".join([t for t in extracted_parts if t and t.strip()])
        return ExtractTextResponse(extractedText=combined_text, files=file_infos)
    except Exception as e:
        logger.error(f"extract_text error: {e}")
        raise HTTPException(status_code=500, detail=f"ファイル抽出中にエラーが発生しました: {str(e)}")
    
# ファイル内容を含む分析エンドポイント
@router.post("/analyze-with-files", response_model=AnalysisResponse)
async def analyze_with_files(request: FileAnalysisRequest):
    """
    手動入力テキストとファイル抽出テキストを組み合わせて分析する
    
    Args:
        request: 分析リクエスト

    Returns:
        AnalysisResponse: 分析結果
    """
    try:
        # 手動入力テキストとファイル抽出テキストを組み合わせて分析
        combined_text = ""

        if request.text and request.text.strip():
            combined_text += request.text.strip() + "\n\n"

        if request.files_content:
            for i, file_content in enumerate(request.files_content):
                if file_content.strip():
                    combined_text += f"[資料 {i+1}]\n" + file_content.strip() + "\n\n"
        
        if not combined_text.strip():
            return AnalysisResponse(
                completeness=0,
                suggestions=["相談内容または資料を入力してください"],
                confidence=1.0
            )
        
        # 通常の分析処理を実行
        analysis_request = AnalysisRequest(text=combined_text.strip())
        result = await analysis_service.analyze_input_completeness(analysis_request)
        
        return result
        
    except Exception as e:
        logger.error(f"File analysis error: {e}")
        raise HTTPException(
            status_code=500,
            detail="ファイル内容の分析中にエラーが発生しました"
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
