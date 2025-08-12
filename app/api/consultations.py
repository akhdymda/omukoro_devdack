from fastapi import APIRouter, HTTPException, Form
from app.models.consultations import ConsultationDetailResponse, RegulationChunkResponse
from app.services.consultation_service import ConsultationService
import logging
from typing import List

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
