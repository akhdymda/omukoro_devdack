from pydantic import BaseModel
from typing import List, Optional

class ConsultationDetailResponse(BaseModel):
    """相談詳細レスポンス"""
    consultation_id: str
    title: str
    content: str
    created_at: str
    status: str

class RegulationChunkResponse(BaseModel):
    """法令チャンクレスポンス"""
    id: str
    text: str
    prefLabel: str
    relevance_score: float
