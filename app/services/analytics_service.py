from typing import Dict, Any
import logging

logger = logging.getLogger(__name__)

class AnalyticsService:
    """分析サービス（ダミー実装）"""
    
    async def analyze_consultation(self, request) -> Dict[str, Any]:
        """相談内容を分析"""
        return {
            "questions": ["分析完了"],
            "consultants": ["システム"],
            "key_points": ["テスト用"]
        }
    
    async def get_dummy_data_info(self) -> Dict[str, Any]:
        """ダミーデータ情報を取得"""
        return {
            "message": "ダミーデータサービス",
            "status": "active"
        }
