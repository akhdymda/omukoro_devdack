from fastapi import APIRouter, HTTPException, Query
from typing import List, Optional
import logging
from app.services.similar_cases_service import similar_cases_service
from app.models.similar_cases import SimilarCaseResponse, SimilarCasesResponse

logger = logging.getLogger(__name__)

router = APIRouter()

@router.get("/similar-cases", response_model=SimilarCasesResponse)
async def get_similar_cases(
    industry_category_id: Optional[str] = Query(None, description="業種カテゴリID"),
    summary_title: Optional[str] = Query(None, description="新規生成された要約タイトル"),
    limit: int = Query(2, ge=1, le=10, description="取得件数（デフォルト: 2）")
):
    """
    類似相談案件を取得する
    
    Args:
        industry_category_id: 業種カテゴリID（指定時はその業種の相談のみ、未指定時は全件）
        summary_title: 新規生成された要約タイトル（類似度計算に使用）
        limit: 取得件数（デフォルト: 2、最大: 10）
        
    Returns:
        SimilarCasesResponse: 類似度の高い相談案件のリスト
    """
    try:
        # 新規サービスを使用して類似相談案件を取得
        result = await similar_cases_service.get_similar_cases(
            industry_category_id=industry_category_id,
            summary_title=summary_title,
            limit=limit
        )
        
        logger.info(f"類似相談案件取得完了: {len(result.similar_cases)} 件")
        return result
        
    except Exception as e:
        logger.error(f"類似相談案件取得エラー: {e}")
        raise HTTPException(
            status_code=500,
            detail="類似相談案件の取得中にエラーが発生しました"
        )
