from fastapi import APIRouter, HTTPException, Form, Query
from app.models.consultations import ConsultationDetailResponse, RegulationChunkResponse
from app.models.search_models import SearchResponse, SearchFiltersResponse
from app.services.consultation_service import ConsultationService
from app.services.mysql_service import mysql_service
import logging
from typing import List, Optional

logger = logging.getLogger(__name__)

router = APIRouter()
consultation_service = ConsultationService()

@router.post("/consultations/generate-suggestions")
async def generate_suggestions(text: str = Form(...)):
    """
    相談内容から提案を生成する
    
    Args:
        text: 相談内容のテキスト
        
    Returns:
        dict: 相談IDと分析結果
    """
    try:
        if not text or len(text.strip()) == 0:
            raise HTTPException(status_code=400, detail="相談内容が入力されていません")
        
        result = await consultation_service.generate_suggestions(text)
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"提案生成エラー: {e}")
        raise HTTPException(
            status_code=500,
            detail="提案生成中にエラーが発生しました"
        )

@router.get("/consultations/{consultation_id}", response_model=ConsultationDetailResponse)
async def get_consultation_detail(consultation_id: str):
    """
    相談詳細を取得する
    
    Args:
        consultation_id: 相談ID
        
    Returns:
        ConsultationDetailResponse: 相談詳細
    """
    try:
        result = await consultation_service.get_consultation_detail(consultation_id)
        return result
        
    except Exception as e:
        logger.error(f"相談詳細取得エラー: {e}")
        raise HTTPException(
            status_code=500,
            detail="相談詳細の取得中にエラーが発生しました"
        )

@router.get("/consultations/{consultation_id}/regulations",
            response_model=List[RegulationChunkResponse])
async def get_consultation_regulations(consultation_id: str):
    """
    相談に関連する法令を取得する
    
    Args:
        consultation_id: 相談ID
        
    Returns:
        List[RegulationChunkResponse]: 関連法令のリスト
    """
    try:
        result = await consultation_service.get_consultation_regulations(consultation_id)
        return result
        
    except Exception as e:
        logger.error(f"相談法令取得エラー: {e}")
        raise HTTPException(
            status_code=500,
            detail="関連法令の取得中にエラーが発生しました"
        )

@router.get("/consultations/search", response_model=SearchResponse)
async def search_consultations(
    query: Optional[str] = Query(None, description="検索クエリ"),
    tenant_id: Optional[str] = Query(None, description="テナントID"),
    user_id: Optional[str] = Query(None, description="ユーザーID"),
    industry_categories: Optional[str] = Query(None, description="業界カテゴリ（カンマ区切り）"),
    alcohol_types: Optional[str] = Query(None, description="アルコール種別（カンマ区切り）"),
    limit: int = Query(50, ge=1, le=100, description="取得件数"),
    offset: int = Query(0, ge=0, description="オフセット")
):
    """
    相談を検索する
    
    Args:
        query: 検索キーワード
        tenant_id: テナントID
        user_id: ユーザーID
        industry_categories: 業界カテゴリコード（例: "FOOD,BEVERAGE"）
        alcohol_types: アルコール種別コード（例: "BEER,SAKE"）
        limit: 取得件数
        offset: オフセット
        
    Returns:
        SearchResponse: 検索結果とフィルタオプション
    """
    try:
        # カンマ区切り文字列をリストに変換
        industry_category_list = industry_categories.split(',') if industry_categories else None
        alcohol_type_list = alcohol_types.split(',') if alcohol_types else None
        
        # 検索実行
        search_results = await mysql_service.search_consultations(
            query=query,
            tenant_id=tenant_id,
            user_id=user_id,
            industry_categories=industry_category_list,
            alcohol_types=alcohol_type_list,
            limit=limit,
            offset=offset
        )
        
        # フィルタオプション取得
        industry_categories_data = await mysql_service.get_industry_categories()
        alcohol_types_data = await mysql_service.get_alcohol_types()
        
        return SearchResponse(
            total_count=len(search_results),  # TODO: 実際のカウントクエリを実装
            results=search_results,
            industry_categories=industry_categories_data,
            alcohol_types=alcohol_types_data
        )
        
    except Exception as e:
        logger.error(f"相談検索エラー: {e}")
        raise HTTPException(
            status_code=500,
            detail="検索中にエラーが発生しました"
        )

@router.get("/consultations/search/filters", response_model=SearchFiltersResponse)
async def get_search_filters():
    """
    検索フィルタのオプションを取得する
    
    Returns:
        SearchFiltersResponse: フィルタオプション
    """
    try:
        industry_categories = await mysql_service.get_industry_categories()
        alcohol_types = await mysql_service.get_alcohol_types()
        
        return SearchFiltersResponse(
            industry_categories=industry_categories,
            alcohol_types=alcohol_types
        )
        
    except Exception as e:
        logger.error(f"フィルタ取得エラー: {e}")
        raise HTTPException(
            status_code=500,
            detail="フィルタオプションの取得中にエラーが発生しました"
        )
