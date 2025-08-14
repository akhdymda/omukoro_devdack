from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime

class ConsultationSearchResult(BaseModel):
    """相談検索結果モデル"""
    consultation_id: str
    title: str
    summary_title: Optional[str] = None
    initial_content: str
    information_sufficiency_level: int = 0
    key_issues: Optional[List[str]] = []
    suggested_questions: Optional[List[str]] = []
    relevant_regulations: Optional[List[Dict[str, Any]]] = []
    action_items: Optional[List[str]] = []
    detected_terms: Optional[List[Dict[str, Any]]] = []
    created_at: datetime
    updated_at: datetime
    user_name: Optional[str] = None
    user_email: Optional[str] = None
    industry_category_name: Optional[str] = None
    alcohol_type_name: Optional[str] = None

class IndustryCategoryResponse(BaseModel):
    """業界カテゴリレスポンスモデル"""
    category_id: str
    category_code: str
    category_name: str
    description: Optional[str] = None
    is_default: bool = False
    sort_order: int = 0

class AlcoholTypeResponse(BaseModel):
    """アルコール種別レスポンスモデル"""
    type_id: str
    type_code: str
    type_name: str
    description: Optional[str] = None
    is_default: bool = False
    sort_order: int = 0

class SearchResponse(BaseModel):
    """検索レスポンスモデル"""
    total_count: int
    results: List[ConsultationSearchResult]
    industry_categories: List[IndustryCategoryResponse]
    alcohol_types: List[AlcoholTypeResponse]

class SearchFiltersResponse(BaseModel):
    """検索フィルタオプションレスポンスモデル"""
    industry_categories: List[IndustryCategoryResponse]
    alcohol_types: List[AlcoholTypeResponse]