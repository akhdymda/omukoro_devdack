from pydantic import BaseModel
from typing import List, Optional, Dict, Any

class ConsultationDetailResponse(BaseModel):
    """相談詳細レスポンス"""
    consultation_id: str
    title: str
    summary_title: Optional[str] = None
    initial_content: Optional[str] = None
    content: Optional[str] = None
    created_at: Optional[str] = None
    status: Optional[str] = None
    industry_category_id: Optional[str] = None
    alcohol_type_id: Optional[str] = None
    key_issues: Optional[str] = None
    suggested_questions: Optional[List[str]] = None
    action_items: Optional[str] = None
    relevant_regulations: Optional[List[Dict[str, Any]]] = None

class RegulationChunkResponse(BaseModel):
    """法令チャンクレスポンス"""
    id: str
    text: str
    prefLabel: str
    relevance_score: float

class RecommendedAdvisor(BaseModel):
    """推奨相談先のアドバイザー情報スキーマ"""
    user_id: str
    name: str
    department: Optional[str] = None
    email: str
