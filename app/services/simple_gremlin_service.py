import asyncio
import logging
from typing import List, Dict, Any, Optional
from gremlin_python.driver import client, serializer
from gremlin_python.driver.protocol import GremlinServerError
from app.config import settings

logger = logging.getLogger(__name__)


class SimpleGremlinService:
    """シンプルなGremlin接続サービス"""
    
    def __init__(self):
        self.client = None
        self.is_connected = False
        
    async def connect(self) -> bool:
        """Gremlinに接続"""
        try:
            if not all([
                settings.gremlin_endpoint,
                settings.gremlin_auth_key,
                settings.gremlin_database,
                settings.gremlin_graph
            ]):
                logger.error("Gremlin設定が不完全です")
                return False
                
            # エンドポイントURLの構築
            endpoint_url = settings.gremlin_endpoint.replace('wss://', '').replace('https://', '')
            
            # クライアント初期化（改善版）
            self.client = client.Client(
                f"wss://{endpoint_url}/gremlin",
                'g',
                username=f"/dbs/{settings.gremlin_database}/colls/{settings.gremlin_graph}",
                password=settings.gremlin_auth_key,
                message_serializer=serializer.GraphSONSerializersV2d0(),
                # 追加の設定（改善版）
                pool_size=20,
                max_workers=8
            )
            
            # 接続テスト
            test_result = await self._test_connection()
            if test_result:
                self.is_connected = True
                logger.info("Gremlin接続成功")
                return True
            else:
                logger.error("Gremlin接続テスト失敗")
                return False
                
        except Exception as e:
            logger.error(f"Gremlin接続エラー: {e}")
            return False
    
    async def _test_connection(self) -> bool:
        """接続テスト"""
        try:
            if not self.client:
                return False
                
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(None, self.client.submit, "g.V().limit(1)")
            return True
        except Exception as e:
            logger.error(f"接続テスト失敗: {e}")
            return False
    
    async def execute_query(self, query: str) -> List[Dict[str, Any]]:
        """Gremlinクエリを実行（改善版）"""
        if not self.is_connected or not self.client:
            raise Exception("Gremlin接続が確立されていません")
            
        try:
            loop = asyncio.get_event_loop()
            
            # より確実な方法でクエリを実行
            def execute_sync():
                try:
                    result_set = self.client.submit(query)
                    # 結果セットを完全に読み込む（改善版）
                    results = []
                    
                    # 結果セットをリストに変換
                    result_list = list(result_set)
                    logger.info(f"生の結果セット長: {len(result_list)}")
                    
                    # 各結果を処理
                    for i, result in enumerate(result_list):
                        logger.info(f"生結果 {i+1}: {result} (型: {type(result)})")
                        
                        # 結果を辞書に変換
                        if hasattr(result, 'id') and hasattr(result, 'label'):
                            # 頂点の場合
                            result_dict = {
                                'id': str(result.id),
                                'label': str(result.label),
                                'type': 'vertex',
                                'properties': {}
                            }
                            
                            # プロパティを取得
                            if hasattr(result, 'properties'):
                                for key, value in result.properties.items():
                                    if hasattr(value, 'value'):
                                        result_dict['properties'][key] = value.value
                                    else:
                                        result_dict['properties'][key] = value
                            
                            results.append(result_dict)
                            
                        elif hasattr(result, 'id') and hasattr(result, 'label') and hasattr(result, 'inV') and hasattr(result, 'outV'):
                            # エッジの場合
                            result_dict = {
                                'id': str(result.id),
                                'label': str(result.label),
                                'type': 'edge',
                                'properties': {}
                            }
                            
                            # プロパティを取得
                            if hasattr(result, 'properties'):
                                for key, value in result.properties.items():
                                    if hasattr(value, 'value'):
                                        result_dict['properties'][key] = value.value
                                    else:
                                        result_dict['properties'][key] = value
                            
                            results.append(result_dict)
                            
                        elif isinstance(result, list):
                            # リストの場合（複数の結果がまとめられている）
                            for item in result:
                                if isinstance(item, dict):
                                    results.append(item)
                                else:
                                    results.append({'raw': str(item)})
                                    
                        elif isinstance(result, dict):
                            # 既に辞書の場合（valueMapの結果など）
                            results.append(result)
                            
                        else:
                            # その他の場合
                            logger.warning(f"未対応の結果形式: {type(result)} - {result}")
                            results.append({'raw': str(result)})
                    
                    return results
                    
                except Exception as e:
                    logger.error(f"同期実行エラー: {e}")
                    raise
            
            result_list = await loop.run_in_executor(None, execute_sync)
            
            logger.info(f"最終的な結果数: {len(result_list)}")
            return result_list
            
        except GremlinServerError as e:
            logger.error(f"Gremlinサーバーエラー: {e}")
            raise Exception(f"Gremlinクエリ実行エラー: {e}")
        except Exception as e:
            logger.error(f"クエリ実行エラー: {e}")
            raise Exception(f"クエリ実行エラー: {e}")
    
    async def get_vertex_count(self) -> int:
        """頂点数を取得"""
        try:
            results = await self.execute_query("g.V().count()")
            if results and 'raw' in results[0]:
                return int(results[0]['raw'])
            return 0
        except Exception as e:
            logger.error(f"頂点数取得エラー: {e}")
            return 0
    
    async def disconnect(self):
        """接続を切断"""
        if self.client:
            try:
                self.client.close()
                logger.info("Gremlin接続を切断しました")
            except Exception as e:
                logger.error(f"接続切断エラー: {e}")
            finally:
                self.client = None
                self.is_connected = False
    
    async def get_health_status(self) -> Dict[str, Any]:
        """ヘルスステータスを取得"""
        try:
            if not self.is_connected:
                return {
                    "status": "disconnected",
                    "gremlin_connected": False,
                    "error": "接続されていません"
                }
            
            vertex_count = await self.get_vertex_count()
            return {
                "status": "healthy",
                "gremlin_connected": True,
                "vertex_count": vertex_count,
                "endpoint": settings.gremlin_endpoint,
                "database": settings.gremlin_database,
                "graph": settings.gremlin_graph
            }
        except Exception as e:
            return {
                "status": "error",
                "gremlin_connected": False,
                "error": str(e)
            }
