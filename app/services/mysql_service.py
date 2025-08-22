import pymysql
from typing import List, Dict, Optional, Any, AsyncContextManager
from contextlib import asynccontextmanager
from app.config import settings
from app.core.exceptions import DatabaseConnectionError, NotFoundError, ValidationError
from app.core.logging import get_logger
import json

logger = get_logger(__name__)

class MySQLService:
    """MySQL データベース接続とクエリサービス"""
    
    def __init__(self):
        self._connection_config = None
        self._initialize_config()
    
    def _initialize_config(self):
        """接続設定を初期化"""
        if not settings.is_mysql_configured():
            logger.warning("MySQL設定が不完全です。一部の機能が利用できません。")
            return
        
        self._connection_config = settings.get_mysql_config()
        logger.info("MySQL接続設定を初期化しました")
    
    def is_available(self) -> bool:
        """MySQLサービスが利用可能かチェック"""
        return self._connection_config is not None
    
    @asynccontextmanager
    async def get_connection(self) -> AsyncContextManager[pymysql.Connection]:
        """MySQL接続を取得（コンテキストマネージャー）"""
        if not self.is_available():
            raise DatabaseConnectionError("MySQL設定が不完全です")
        
        connection = None
        try:
            connection = pymysql.connect(**self._connection_config)
            
            # タイムゾーンを日本時間に設定
            with connection.cursor() as cursor:
                cursor.execute("SET time_zone = '+09:00'")
                cursor.execute("SET @@session.time_zone = '+09:00'")
            
            logger.debug("MySQL接続を確立しました（タイムゾーン: +09:00）")
            yield connection
        except pymysql.Error as e:
            logger.error(f"MySQL接続エラー: {e}")
            raise DatabaseConnectionError(f"データベース接続に失敗しました: {str(e)}")
        except Exception as e:
            logger.error(f"予期しないデータベースエラー: {e}")
            raise DatabaseConnectionError(f"データベースエラー: {str(e)}")
        finally:
            if connection:
                connection.close()
                logger.debug("MySQL接続を閉じました")
    
    async def search_consultations(
        self,
        query: Optional[str] = None,
        tenant_id: Optional[str] = None,
        user_id: Optional[str] = None,
        industry_categories: Optional[List[str]] = None,
        alcohol_types: Optional[List[str]] = None,
        limit: int = 50,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """相談検索"""
        
        sql = """
        SELECT 
            c.consultation_id,
            c.tenant_id,
            c.user_id,
            c.title,
            c.summary_title,
            c.initial_content,
            c.information_sufficiency_level,
            c.key_issues,
            c.suggested_questions,
            c.relevant_regulations,
            c.action_items,
            c.detected_terms,
            c.created_at,
            c.updated_at,
            u.name as user_name,
            u.email as user_email,
            ic.category_name as industry_category_name,
            at.type_name as alcohol_type_name
        FROM consultation c
        LEFT JOIN user u ON c.user_id = u.user_id
        LEFT JOIN industry_category ic ON c.industry_category_id = ic.category_id
        LEFT JOIN alcohol_type at ON c.alcohol_type_id = at.type_id
        WHERE 1=1
        """
        
        params = []
        
        # テナント条件
        if tenant_id:
            sql += " AND c.tenant_id = %s"
            params.append(tenant_id)
        
        # ユーザー条件
        if user_id:
            sql += " AND c.user_id = %s"
            params.append(user_id)
        
        # 業界カテゴリフィルタ
        if industry_categories:
            placeholders = ','.join(['%s'] * len(industry_categories))
            sql += f" AND c.industry_category_id IN ({placeholders})"
            params.extend(industry_categories)
        
        # アルコール種別フィルタ
        if alcohol_types:
            placeholders = ','.join(['%s'] * len(alcohol_types))
            sql += f" AND c.alcohol_type_id IN ({placeholders})"
            params.extend(alcohol_types)
        
        # テキスト検索（LIKE検索に変更）
        if query:
            sql += " AND (c.title LIKE %s OR c.initial_content LIKE %s)"
            search_pattern = f"%{query}%"
            params.extend([search_pattern, search_pattern])
        
        # 並び順
        sql += " ORDER BY c.updated_at DESC"
        
        # ページング
        sql += " LIMIT %s OFFSET %s"
        params.extend([limit, offset])
        
        try:
            async with self.get_connection() as conn:
                with conn.cursor(pymysql.cursors.DictCursor) as cursor:
                    cursor.execute(sql, params)
                    results = cursor.fetchall()
                    
                    # JSON フィールドをパース
                    for result in results:
                        for json_field in ['key_issues', 'suggested_questions', 'relevant_regulations', 'action_items', 'detected_terms']:
                            if result[json_field]:
                                result[json_field] = result[json_field] if isinstance(result[json_field], (list, dict)) else []
                    
                    logger.debug(f"相談検索結果: {len(results)}件")
                    return results
                    
        except DatabaseConnectionError:
            raise
        except Exception as e:
            logger.error(f"相談検索エラー: {e}")
            raise DatabaseConnectionError(f"相談検索中にエラーが発生しました: {str(e)}")
    
    async def create_consultation(self, consultation_data: Dict[str, Any]) -> str:
        """相談データを作成・保存"""
        sql = """
        INSERT INTO consultation (
            consultation_id, tenant_id, user_id, title, summary_title, initial_content,
            industry_category_id, alcohol_type_id, key_issues,
            suggested_questions, action_items, relevant_regulations
        ) VALUES (
            %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
        )
        """
        
        params = [
            consultation_data.get('consultation_id'),
            '1',  # tenant_id を1に固定
            consultation_data.get('user_id', '1'),  # user_id を動的に設定（デフォルトは'1'）
            consultation_data.get('title'),
            consultation_data.get('summary_title'),
            consultation_data.get('initial_content'),
            consultation_data.get('industry_category_id'),
            consultation_data.get('alcohol_type_id'),
            json.dumps(consultation_data.get('key_issues')) if consultation_data.get('key_issues') else None,
            json.dumps(consultation_data.get('suggested_questions')) if consultation_data.get('suggested_questions') else None,
            json.dumps(consultation_data.get('action_items')) if consultation_data.get('action_items') else None,
            json.dumps(consultation_data.get('relevant_regulations')) if consultation_data.get('relevant_regulations') else None
        ]
        
        try:
            async with self.get_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute(sql, params)
                    conn.commit()
                    consultation_id = consultation_data.get('consultation_id')
                    logger.info(f"相談データを保存しました: {consultation_id}")
                    return consultation_id
        except Exception as e:
            logger.error(f"相談データ保存エラー: {e}")
            raise DatabaseConnectionError(f"相談データの保存に失敗しました: {str(e)}")
    
    async def get_consultation_by_id(self, consultation_id: str) -> Optional[Dict[str, Any]]:
        """相談IDで相談データを取得"""
        sql = """
        SELECT 
            consultation_id, tenant_id, user_id, title, summary_title, initial_content,
            industry_category_id, alcohol_type_id, key_issues,
            suggested_questions, action_items, relevant_regulations,
            updated_at
        FROM consultation 
        WHERE consultation_id = %s
        """
        
        try:
            async with self.get_connection() as conn:
                with conn.cursor(pymysql.cursors.DictCursor) as cursor:
                    cursor.execute(sql, [consultation_id])
                    result = cursor.fetchone()
                    
                    if result:
                        # JSONフィールドをパース
                        for json_field in ['key_issues', 'suggested_questions', 'action_items', 'relevant_regulations']:
                            if result[json_field]:
                                try:
                                    result[json_field] = json.loads(result[json_field])
                                except json.JSONDecodeError:
                                    result[json_field] = None
                    
                    return result
        except Exception as e:
            logger.error(f"相談データ取得エラー: {e}")
            raise DatabaseConnectionError(f"相談データの取得に失敗しました: {str(e)}")
    
    async def update_consultation(self, consultation_id: str, update_data: Dict[str, Any]) -> bool:
        """相談データを更新"""
        # 更新可能なフィールドを定義（存在するカラムのみ）
        updateable_fields = [
            'title', 'summary_title', 'key_issues', 'suggested_questions',
            'action_items', 'relevant_regulations'
        ]
        
        set_clauses = []
        params = []
        
        for field in updateable_fields:
            if field in update_data and update_data[field] is not None:
                if field in ['key_issues', 'suggested_questions', 'action_items', 'relevant_regulations']:
                    set_clauses.append(f"{field} = %s")
                    params.append(json.dumps(update_data[field]))
                else:
                    set_clauses.append(f"{field} = %s")
                    params.append(update_data[field])
        
        if not set_clauses:
            return False
        
        set_clauses.append("updated_at = NOW()")
        params.append(consultation_id)
        
        sql = f"""
        UPDATE consultation 
        SET {', '.join(set_clauses)}
        WHERE consultation_id = %s
        """
        
        try:
            async with self.get_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute(sql, params)
                    conn.commit()
                    logger.info(f"相談データを更新しました: {consultation_id}")
                    return True
        except Exception as e:
            logger.error(f"相談データ更新エラー: {e}")
            raise DatabaseConnectionError(f"相談データの更新に失敗しました: {str(e)}")
    
    async def get_industry_categories(self, active_only: bool = True) -> List[Dict[str, Any]]:
        """業界カテゴリ一覧取得"""
        sql = """
        SELECT category_id, category_code, category_name, description, is_default, sort_order
        FROM industry_category
        WHERE 1=1
        """
        params = []
        
        if active_only:
            sql += " AND is_active = %s"
            params.append(True)
        
        sql += " ORDER BY sort_order, category_name"
        
        try:
            async with self.get_connection() as conn:
                with conn.cursor(pymysql.cursors.DictCursor) as cursor:
                    cursor.execute(sql, params)
                    results = cursor.fetchall()
                    logger.debug(f"業界カテゴリ取得: {len(results)}件")
                    return results
        except DatabaseConnectionError:
            raise
        except Exception as e:
            logger.error(f"業界カテゴリ取得エラー: {e}")
            raise DatabaseConnectionError(f"業界カテゴリの取得中にエラーが発生しました: {str(e)}")
    
    async def get_alcohol_types(self, active_only: bool = True) -> List[Dict[str, Any]]:
        """アルコール種別一覧取得"""
        sql = """
        SELECT type_id, type_code, type_name, description, is_default, sort_order
        FROM alcohol_type
        WHERE 1=1
        """
        params = []
        
        if active_only:
            sql += " AND is_active = %s"
            params.append(True)
        
        sql += " ORDER BY sort_order, type_name"
        
        try:
            async with self.get_connection() as conn:
                with conn.cursor(pymysql.cursors.DictCursor) as cursor:
                    cursor.execute(sql, params)
                    results = cursor.fetchall()
                    logger.debug(f"アルコール種別取得: {len(results)}件")
                    return results
        except DatabaseConnectionError:
            raise
        except Exception as e:
            logger.error(f"アルコール種別取得エラー: {e}")
            raise DatabaseConnectionError(f"アルコール種別の取得中にエラーが発生しました: {str(e)}")

mysql_service = MySQLService()