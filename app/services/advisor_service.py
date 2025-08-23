from typing import Optional, List, Dict, Any
import random
import pymysql
from app.services.mysql_service import MySQLService
from app.models.consultations import RecommendedAdvisor


class AdvisorService:
    """アドバイザー検索・選択サービス"""
    
    def __init__(self, mysql_service: MySQLService):
        self.mysql_service = mysql_service
    
    async def get_recommended_advisor(
        self, 
        industry_category: str, 
        alcohol_type: str
    ) -> Optional[RecommendedAdvisor]:
        """
        推奨相談先のアドバイザーを選択する
        
        Args:
            industry_category: 事業カテゴリID
            alcohol_type: 酒類タイプID
            
        Returns:
            RecommendedAdvisor: 推奨相談先のアドバイザー情報
            None: 適切なアドバイザーが見つからない場合
            
        Raises:
            Exception: データベースエラーが発生した場合
        """
        try:
            # アドバイザー候補を取得
            advisors = await self._get_advisor_candidates(industry_category, alcohol_type)
            
            if not advisors:
                return None
            
            # 最適なアドバイザーを選択
            selected_advisor = self._select_best_advisor(advisors, industry_category, alcohol_type)
            
            if not selected_advisor:
                return None
            
            # RecommendedAdvisorスキーマに変換
            return RecommendedAdvisor(
                user_id=selected_advisor['user_id'],
                name=selected_advisor['name'],
                department=selected_advisor['department'],
                email=selected_advisor['email']
            )
            
        except Exception as e:
            # ログ出力（本格運用時は適切なログライブラリを使用）
            print(f"アドバイザー選択中にエラーが発生: {str(e)}")
            raise
    
    async def _get_advisor_candidates(
        self, 
        industry_category: str, 
        alcohol_type: str
    ) -> List[Dict[str, Any]]:
        """
        アドバイザー候補を取得する
        
        Args:
            industry_category: 事業カテゴリID
            alcohol_type: 酒類タイプID
            
        Returns:
            List[Dict]: アドバイザー候補のリスト
        """
        query = """
            SELECT 
                user_id, name, department, email,
                industry_category_id, alcohol_type_id
            FROM omukoro.user 
            WHERE role = 'advisor' 
            AND is_active = 1
            AND (
                industry_category_id = %s 
                OR alcohol_type_id = %s
            )
        """
        
        params = [industry_category, alcohol_type]
        
        try:
            async with self.mysql_service.get_connection() as conn:
                with conn.cursor(pymysql.cursors.DictCursor) as cursor:
                    cursor.execute(query, params)
                    result = cursor.fetchall()
                    return result
        except Exception as e:
            print(f"アドバイザー候補取得エラー: {str(e)}")
            raise
    
    def _select_best_advisor(
        self, 
        advisors: List[Dict[str, Any]], 
        industry_category: str, 
        alcohol_type: str
    ) -> Optional[Dict[str, Any]]:
        """
        最適なアドバイザーを選択する
        
        Args:
            advisors: アドバイザー候補のリスト
            industry_category: 事業カテゴリID
            alcohol_type: 酒類タイプID
            
        Returns:
            Dict: 選択されたアドバイザー情報
        """
        # マッチングレベル別にグループ化
        perfect_matches = []  # 両方一致
        industry_matches = []  # 事業カテゴリ一致
        alcohol_matches = []   # 酒類タイプ一致
        
        for advisor in advisors:
            advisor_industry = advisor.get('industry_category_id')
            advisor_alcohol = advisor.get('alcohol_type_id')
            
            # 両方一致
            if (advisor_industry == industry_category and 
                advisor_alcohol == alcohol_type):
                perfect_matches.append(advisor)
            # 事業カテゴリ一致
            elif advisor_industry == industry_category:
                industry_matches.append(advisor)
            # 酒類タイプ一致
            elif advisor_alcohol == alcohol_type:
                alcohol_matches.append(advisor)
        
        # 優先順位に従って選択
        if perfect_matches:
            return random.choice(perfect_matches)
        elif industry_matches:
            return random.choice(industry_matches)
        elif alcohol_matches:
            return random.choice(alcohol_matches)
        else:
            return None
