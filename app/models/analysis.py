from pydantic import BaseModel
from typing import List, Optional

class AnalysisRequest(BaseModel):
    text: str
    docText: Optional[str] = None  # ファイルから抽出されたテキスト（任意）

class AnalysisResponse(BaseModel):
    # 仕様では 1-5 段階を返却
    completeness: int
    suggestions: List[str]
    confidence: float
    reasoning: Optional[str] = None

class RuleAnalysisResult(BaseModel):
    found_categories: List[str]
    missing_categories: List[str]
    score: int
    missing_elements: List[str]

# 追加：ファイルアップロード用のモデル
class FileUploadResponse(BaseModel):
    success: bool
    extracted_text: str
    filename: str
    file_size: int
    message: Optional[str] = None

class FileAnalysisRequest(BaseModel):
    text: Optional[str] = ""  # 手動入力テキスト（任意）
    files_content: List[str]  # 複数ファイルの抽出テキスト
    
    
class ExtractedFileInfo(BaseModel):
    name: str
    bytes: int


class ExtractTextResponse(BaseModel):
    extractedText: str
    files: List[ExtractedFileInfo]

# 新規追加：Analytics API用モデル
class AnalyticsRequest(BaseModel):
    text: str
    files_content: Optional[List[str]] = []  # ファイルから抽出されたテキスト

class ConsultantInfo(BaseModel):
    name: str
    department: str
    expertise: str

class AnalysisMetadata(BaseModel):
    confidence: float
    generated_at: str
    used_dummy_data: bool
    matched_regulations: Optional[List[str]] = []
    fallback: Optional[bool] = False

class AnalyticsResponse(BaseModel):
    summary: str
    questions: List[str]
    consultants: List[ConsultantInfo]
    analysis_metadata: AnalysisMetadata