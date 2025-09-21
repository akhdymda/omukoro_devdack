import asyncio
import logging
from typing import List, Dict, Any, Optional, Tuple
from gremlin_python.driver import client, protocol, serializer
from gremlin_python.driver.protocol import GremlinServerError
from app.config import settings
import time

logger = logging.getLogger(__name__)

class GremlinService:
    """Azure Cosmos DB Gremlin API接続・検索サービス"""
    
    def __init__(self):
        self.client = None
        self.is_connected = False
        self._connection_params = None
        
    async def connect(self) -> bool:
        """Gremlin接続を確立"""
        try:
            if not self._validate_config():
                logger.error("Gremlin設定が不完全です")
                return False
            
            # 接続を確立
            endpoint_url = settings.gremlin_endpoint.replace('wss://', '').replace('https://', '')
            self.client = client.Client(
                f"wss://{endpoint_url}/gremlin",
                'g',
                username=f"/dbs/{settings.gremlin_database}/colls/{settings.gremlin_graph}",
                password=settings.gremlin_auth_key,
                message_serializer=serializer.GraphSONSerializersV2d0()
            )
            
            # 接続テスト
            await self._test_connection()
            self.is_connected = True
            logger.info("Gremlin接続が確立されました")
            return True
            
        except Exception as e:
            logger.error(f"Gremlin接続エラー: {e}")
            self.is_connected = False
            return False
    
    async def disconnect(self):
        """Gremlin接続を閉じる"""
        if self.client:
            try:
                self.client.close()
                self.is_connected = False
                logger.info("Gremlin接続を閉じました")
            except Exception as e:
                logger.error(f"Gremlin切断エラー: {e}")
    
    def _validate_config(self) -> bool:
        """設定の妥当性を検証"""
        required_settings = [
            settings.gremlin_endpoint,
            settings.gremlin_auth_key,
            settings.gremlin_database,
            settings.gremlin_graph
        ]
        return all(setting is not None and setting.strip() != "" for setting in required_settings)
    
    async def _test_connection(self) -> bool:
        """接続テストを実行"""
        try:
            # 非同期で接続テストを実行
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(None, self.client.submit, "g.V().limit(1)")
            return True
        except Exception as e:
            logger.error(f"接続テスト失敗: {e}")
            return False
    
    async def _run_query(self, query: str, retries: int = 3) -> List[Dict[str, Any]]:
        """Gremlinクエリを実行"""
        if not self.is_connected:
            raise Exception("Gremlin接続が確立されていません")
        
        for attempt in range(retries):
            try:
                # 非同期でクエリを実行
                loop = asyncio.get_event_loop()
                result_set = await loop.run_in_executor(None, self.client.submit, query)
                results = []
                
                for result in result_set:
                    if result:
                        results.append(result)
                
                return results
                
            except GremlinServerError as e:
                if e.status_code == 429:  # Rate limit
                    wait_time = (2 ** attempt) * 0.5  # 指数バックオフ
                    logger.warning(f"Rate limit hit, waiting {wait_time}s (attempt {attempt + 1})")
                    await asyncio.sleep(wait_time)
                    continue
                else:
                    logger.error(f"Gremlinサーバーエラー: {e}")
                    raise
            except Exception as e:
                logger.error(f"Gremlinクエリエラー: {e}")
                if attempt == retries - 1:
                    raise
                await asyncio.sleep(0.5)
        
        return []
    
    async def search_vertices_by_text(self, query: str, limit: int = 10) -> List[Dict[str, Any]]:
        """テキスト検索で頂点を検索"""
        try:
            # 基本的なテキスト検索クエリ
            search_query = f"""
            g.V()
            .hasLabel('法律', '条', '章', '節')
            .or(
                has('id', containing('{query}')),
                has('properties', containing('{query}'))
            )
            .limit({limit})
            .valueMap(true)
            """
            
            results = await self._run_query(search_query)
            return self._format_vertex_results(results)
            
        except Exception as e:
            logger.error(f"頂点検索エラー: {e}")
            return []
    
    async def search_related_vertices(self, vertex_id: str, max_distance: int = 2, limit: int = 10) -> List[Dict[str, Any]]:
        """指定された頂点に関連する頂点を検索"""
        try:
            # 関係性検索クエリ
            search_query = f"""
            g.V('{vertex_id}')
            .repeat(bothE().otherV())
            .times({max_distance})
            .limit({limit})
            .valueMap(true)
            """
            
            results = await self._run_query(search_query)
            return self._format_vertex_results(results)
            
        except Exception as e:
            logger.error(f"関連頂点検索エラー: {e}")
            return []
    
    async def search_edges_by_type(self, edge_type: str, limit: int = 10) -> List[Dict[str, Any]]:
        """エッジタイプでエッジを検索"""
        try:
            search_query = f"""
            g.E()
            .hasLabel('{edge_type}')
            .limit({limit})
            .valueMap(true)
            """
            
            results = await self._run_query(search_query)
            return self._format_edge_results(results)
            
        except Exception as e:
            logger.error(f"エッジ検索エラー: {e}")
            return []
    
    async def get_vertex_by_id(self, vertex_id: str) -> Optional[Dict[str, Any]]:
        """IDで頂点を取得"""
        try:
            search_query = f"g.V('{vertex_id}').valueMap(true)"
            results = await self._run_query(search_query)
            
            if results:
                return self._format_vertex_results(results)[0]
            return None
            
        except Exception as e:
            logger.error(f"頂点取得エラー: {e}")
            return None
    
    async def get_vertex_relations(self, vertex_id: str, direction: str = "both") -> List[Dict[str, Any]]:
        """頂点の関係性を取得"""
        try:
            if direction == "out":
                search_query = f"g.V('{vertex_id}').outE().valueMap(true)"
            elif direction == "in":
                search_query = f"g.V('{vertex_id}').inE().valueMap(true)"
            else:  # both
                search_query = f"g.V('{vertex_id}').bothE().valueMap(true)"
            
            results = await self._run_query(search_query)
            return self._format_edge_results(results)
            
        except Exception as e:
            logger.error(f"関係性取得エラー: {e}")
            return []
    
    async def search_legal_concepts(self, query: str, limit: int = 10) -> List[Dict[str, Any]]:
        """法律概念を検索（複数ホップ）"""
        try:
            # 法律概念の多段階検索
            search_query = f"""
            g.V()
            .hasLabel('法律')
            .or(
                has('id', containing('{query}')),
                has('properties', containing('{query}'))
            )
            .union(
                identity(),
                out().hasLabel('条', '章', '節'),
                out().out().hasLabel('条', '章', '節')
            )
            .dedup()
            .limit({limit})
            .valueMap(true)
            """
            
            results = await self._run_query(search_query)
            return self._format_vertex_results(results)
            
        except Exception as e:
            logger.error(f"法律概念検索エラー: {e}")
            return []
    
    def _format_vertex_results(self, results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """頂点結果をフォーマット"""
        formatted_results = []
        
        for result in results:
            if isinstance(result, dict):
                vertex_data = {
                    'id': result.get('id', [''])[0] if isinstance(result.get('id'), list) else result.get('id', ''),
                    'label': result.get('label', [''])[0] if isinstance(result.get('label'), list) else result.get('label', ''),
                    'properties': {}
                }
                
                # プロパティを抽出
                for key, value in result.items():
                    if key not in ['id', 'label']:
                        if isinstance(value, list) and len(value) == 1:
                            vertex_data['properties'][key] = value[0]
                        else:
                            vertex_data['properties'][key] = value
                
                formatted_results.append(vertex_data)
        
        return formatted_results
    
    def _format_edge_results(self, results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """エッジ結果をフォーマット"""
        formatted_results = []
        
        for result in results:
            if isinstance(result, dict):
                edge_data = {
                    'id': result.get('id', [''])[0] if isinstance(result.get('id'), list) else result.get('id', ''),
                    'label': result.get('label', [''])[0] if isinstance(result.get('label'), list) else result.get('label', ''),
                    'outV': result.get('outV', [''])[0] if isinstance(result.get('outV'), list) else result.get('outV', ''),
                    'inV': result.get('inV', [''])[0] if isinstance(result.get('inV'), list) else result.get('inV', ''),
                    'properties': {}
                }
                
                # プロパティを抽出
                for key, value in result.items():
                    if key not in ['id', 'label', 'outV', 'inV']:
                        if isinstance(value, list) and len(value) == 1:
                            edge_data['properties'][key] = value[0]
                        else:
                            edge_data['properties'][key] = value
                
                formatted_results.append(edge_data)
        
        return formatted_results
    
    async def get_health_status(self) -> Dict[str, Any]:
        """ヘルスチェック用の状態を取得"""
        try:
            if not self.is_connected:
                return {
                    "connected": False,
                    "error": "接続されていません"
                }
            
            # 簡単なクエリで接続をテスト
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(None, self.client.submit, "g.V().count()")
            vertex_count = result[0] if result else 0
            
            return {
                "connected": True,
                "vertex_count": vertex_count,
                "endpoint": settings.gremlin_endpoint,
                "database": settings.gremlin_database,
                "graph": settings.gremlin_graph
            }
            
        except Exception as e:
            return {
                "connected": False,
                "error": str(e)
            }
