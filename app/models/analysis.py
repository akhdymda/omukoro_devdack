from pydantic import BaseModel
from typing import List, Optional

class AnalysisRequest(BaseModel):
    """分析リクエスト"""
    text: Optional[str] = None
    docText: Optional[str] = None

class AnalysisResponse(BaseModel):
    """分析レスポンス"""
    completeness: int  # 1-5のスコア
    suggestions: List[str]
    confidence: float  # 0.0-1.0

class FileUploadResponse(BaseModel):
    """ファイルアップロードレスポンス"""
    extractedText: str
    files: List[dict]

class FileAnalysisRequest(BaseModel):
    """ファイル分析リクエスト"""
    text: Optional[str] = None
    files_content: List[str] = []

class AnalyticsRequest(BaseModel):
    """分析リクエスト"""
    text: str
    files_content: Optional[List[str]] = None

class AnalyticsResponse(BaseModel):
    """分析レスポンス"""
    questions: List[str]
    consultants: List[str]
    key_points: List[str]

class ExtractTextResponse(BaseModel):
    """テキスト抽出レスポンス"""
    extractedText: str
    files: List[dict]

class ExtractedFileInfo(BaseModel):
    """抽出されたファイル情報"""
    name: str
    bytes: int
