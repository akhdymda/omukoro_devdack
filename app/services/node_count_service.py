import time
import logging
from typing import Optional
from app.services.simple_gremlin_service import SimpleGremlinService
from app.models.node_count import NodeCountResponse

logger = logging.getLogger(__name__)


class NodeCountService:
    """ノード数カウントサービス"""
    
    def __init__(self):
        self.gremlin_service = SimpleGremlinService()
        self._connected = False
    
    async def initialize(self) -> bool:
        """サービスを初期化"""
        try:
            self._connected = await self.gremlin_service.connect()
            return self._connected
        except Exception as e:
            logger.error(f"ノード数カウントサービス初期化エラー: {e}")
            return False
    
    async def count_related_nodes(self, node_id: str) -> NodeCountResponse:
        """指定されたノードの距離1の双方向関連ノード数をカウント"""
        start_time = time.time()
        
        try:
            if not self._connected:
                await self.initialize()
            
            if not self._connected:
                execution_time = (time.time() - start_time) * 1000
                return NodeCountResponse(
                    node_id=node_id,
                    related_nodes_count=0,
                    execution_time_ms=execution_time,
                    success=False,
                    error_message="Gremlin接続が確立されていません"
                )
            
            # 距離1の双方向関連ノード数をカウント
            count = await self._count_related_nodes_at_distance_1(node_id)
            
            execution_time = (time.time() - start_time) * 1000
            
            return NodeCountResponse(
                node_id=node_id,
                related_nodes_count=count,
                execution_time_ms=execution_time,
                success=True,
                error_message=None
            )
            
        except Exception as e:
            logger.error(f"ノード数カウントエラー: {e}")
            execution_time = (time.time() - start_time) * 1000
            
            return NodeCountResponse(
                node_id=node_id,
                related_nodes_count=0,
                execution_time_ms=execution_time,
                success=False,
                error_message=str(e)
            )
    
    async def _count_related_nodes_at_distance_1(self, node_id: str) -> int:
        """距離1の双方向関連ノード数をカウント"""
        try:
            # 複数のクエリを試行して最も確実な結果を取得
            queries = [
                # クエリ1: 基本的なカウント
                f"g.V().has('id', '{node_id}').both().count()",
                
                # クエリ2: エッジ経由でカウント
                f"g.V().has('id', '{node_id}').bothE().otherV().count()",
                
                # クエリ3: 重複を除去してカウント
                f"g.V().has('id', '{node_id}').both().dedup().count()",
                
                # クエリ4: エッジ経由で重複を除去してカウント
                f"g.V().has('id', '{node_id}').bothE().otherV().dedup().count()"
            ]
            
            max_count = 0
            
            for i, query in enumerate(queries):
                try:
                    logger.info(f"クエリ {i+1} を実行: {query}")
                    results = await self.gremlin_service.execute_query(query)
                    
                    if results and len(results) > 0:
                        # 結果から数値を抽出
                        count = self._extract_count_from_result(results[0])
                        logger.info(f"クエリ {i+1} の結果: {count}")
                        max_count = max(max_count, count)
                    else:
                        logger.warning(f"クエリ {i+1} で結果が取得できませんでした")
                        
                except Exception as e:
                    logger.warning(f"クエリ {i+1} でエラー: {e}")
                    continue
            
            logger.info(f"最終的なカウント結果: {max_count}")
            return max_count
            
        except Exception as e:
            logger.error(f"距離1のノード数カウントエラー: {e}")
            return 0
    
    def _extract_count_from_result(self, result) -> int:
        """結果から数値を抽出（改善版）"""
        try:
            if isinstance(result, (int, float)):
                return int(result)
            elif isinstance(result, dict):
                # 辞書の場合は、値の型を確認
                for value in result.values():
                    if isinstance(value, (int, float)):
                        return int(value)
                    elif isinstance(value, list) and len(value) > 0:
                        if isinstance(value[0], (int, float)):
                            return int(value[0])
                # 'raw'キーがある場合の処理
                if 'raw' in result:
                    raw_value = result['raw']
                    if isinstance(raw_value, str):
                        # 文字列から数値を抽出
                        import re
                        numbers = re.findall(r'\d+', raw_value)
                        if numbers:
                            return int(numbers[0])
            elif isinstance(result, list) and len(result) > 0:
                if isinstance(result[0], (int, float)):
                    return int(result[0])
            
            # 文字列の場合は数値として解析を試行
            result_str = str(result)
            import re
            numbers = re.findall(r'\d+', result_str)
            if numbers:
                return int(numbers[0])
            
            logger.warning(f"数値を抽出できませんでした: {result}")
            return 0
            
        except Exception as e:
            logger.warning(f"数値抽出エラー: {e}, 結果: {result}")
            return 0
    
    async def get_health_status(self) -> dict:
        """ヘルスステータスを取得"""
        return await self.gremlin_service.get_health_status()
    
    async def disconnect(self):
        """接続を切断"""
        await self.gremlin_service.disconnect()
        self._connected = False
