from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime

class SimilarCaseResponse(BaseModel):
    """類似相談案件の完全なレスポンスモデル（MySQLサービスとの互換性を保つ）"""
    
    consultation_id: str = Field(..., description="相談案件ID")
    title: str = Field(..., description="相談タイトル")
    summary_title: Optional[str] = Field(None, description="要約タイトル")
    initial_content: Optional[str] = Field(None, description="初期内容")
    created_at: Optional[str] = Field(None, description="作成日時")
    industry_category_id: Optional[str] = Field(None, description="業種カテゴリID")
    alcohol_type_id: Optional[str] = Field(None, description="酒類タイプID")
    key_issues: Optional[List[str]] = Field(None, description="主要課題（リスト型）")
    suggested_questions: Optional[List[str]] = Field(None, description="提案される質問（リスト型）")
    action_items: Optional[List[str]] = Field(None, description="アクション項目（リスト型）")
    relevant_regulations: Optional[List[Dict[str, Any]]] = Field(None, description="関連法令（リスト型）")
    detected_terms: Optional[List[Dict[str, Any]]] = Field(None, description="検出された用語（リスト型）")
    similarity_score: Optional[int] = Field(None, ge=0, le=100, description="類似度スコア（0-100）")
    reason: Optional[str] = Field(None, description="類似性の理由")

class SimilarCasesResponse(BaseModel):
    """類似相談案件取得APIのレスポンスモデル"""
    
    similar_cases: List[SimilarCaseResponse] = Field(..., description="類似相談案件のリスト")
    total_candidates: int = Field(..., ge=0, description="類似度計算対象の総件数")
    message: str = Field(..., description="処理結果のメッセージ")

class SimilarCasesRequest(BaseModel):
    """類似相談案件取得APIのリクエストモデル（オプション）"""
    
    industry_category_id: Optional[str] = Field(None, description="業種カテゴリID")
    summary_title: Optional[str] = Field(None, description="新規生成された要約タイトル")
    limit: int = Field(2, ge=1, le=10, description="取得件数（デフォルト: 2、最大: 10）")
