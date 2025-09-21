import time
import logging
from typing import List, Dict, Any, Optional
from app.services.simple_gremlin_service import SimpleGremlinService
from app.models.nodes_info import NodeInfo, NodesInfoResponse

logger = logging.getLogger(__name__)


class NodesInfoService:
    """ノード情報取得サービス"""
    
    def __init__(self):
        self.gremlin_service = SimpleGremlinService()
        self._connected = False
    
    async def initialize(self) -> bool:
        """サービスを初期化"""
        try:
            self._connected = await self.gremlin_service.connect()
            return self._connected
        except Exception as e:
            logger.error(f"ノード情報取得サービス初期化エラー: {e}")
            return False
    
    async def get_related_nodes_info(self, node_id: str, max_results: int = 20) -> NodesInfoResponse:
        """指定されたノードの距離1の双方向関連ノード情報を取得"""
        start_time = time.time()
        
        try:
            if not self._connected:
                await self.initialize()
            
            if not self._connected:
                execution_time = (time.time() - start_time) * 1000
                return NodesInfoResponse(
                    node_id=node_id,
                    related_nodes=[],
                    total_count=0,
                    execution_time_ms=execution_time,
                    success=False,
                    error_message="Gremlin接続が確立されていません"
                )
            
            # 距離1の双方向関連ノード情報を取得
            related_nodes = await self._get_related_nodes_at_distance_1(node_id, max_results)
            
            execution_time = (time.time() - start_time) * 1000
            
            return NodesInfoResponse(
                node_id=node_id,
                related_nodes=related_nodes,
                total_count=len(related_nodes),
                execution_time_ms=execution_time,
                success=True,
                error_message=None
            )
            
        except Exception as e:
            logger.error(f"ノード情報取得エラー: {e}")
            execution_time = (time.time() - start_time) * 1000
            
            return NodesInfoResponse(
                node_id=node_id,
                related_nodes=[],
                total_count=0,
                execution_time_ms=execution_time,
                success=False,
                error_message=str(e)
            )
    
    async def _get_related_nodes_at_distance_1(self, node_id: str, max_results: int) -> List[NodeInfo]:
        """距離1の双方向関連ノード情報を取得"""
        try:
            # 複数のクエリを試行して最も確実な結果を取得
            queries = [
                # クエリ1: エッジ情報を含む関連ノード取得（最優先）
                f"""
                g.V().has('id', '{node_id}').as('source')
                .bothE().as('edge')
                .otherV().as('target')
                .select('source', 'edge', 'target')
                .by(valueMap(true))
                """,
                
                # クエリ2: 基本的な関連ノード取得
                f"g.V().has('id', '{node_id}').both()",
                
                # クエリ3: エッジ経由で関連ノード取得
                f"g.V().has('id', '{node_id}').bothE().otherV()",
                
                # クエリ4: より詳細なエッジ情報取得
                f"""
                g.V().has('id', '{node_id}')
                .bothE()
                .as('edge')
                .otherV()
                .as('target')
                .select('edge', 'target')
                .by(valueMap(true))
                """
            ]
            
            best_result = []
            
            for i, query in enumerate(queries):
                try:
                    logger.info(f"クエリ {i+1} を実行: {query}")
                    results = await self.gremlin_service.execute_query(query)
                    
                    if results and len(results) > 0:
                        # 結果をNodeInfoに変換
                        nodes = self._convert_to_node_info(results, node_id)
                        logger.info(f"クエリ {i+1} の結果: {len(nodes)}件")
                        logger.info(f"クエリ {i+1} の生結果: {results}")
                        
                        if len(nodes) > len(best_result):
                            best_result = nodes
                            logger.info(f"新しい最良結果: {len(best_result)}件")
                            
                    else:
                        logger.warning(f"クエリ {i+1} で結果が取得できませんでした")
                        
                except Exception as e:
                    logger.warning(f"クエリ {i+1} でエラー: {e}")
                    continue
            
            # 最大結果数で制限
            return best_result[:max_results]
            
        except Exception as e:
            logger.error(f"距離1のノード情報取得エラー: {e}")
            return []
    
    def _convert_to_node_info(self, results: List[Any], source_node_id: str) -> List[NodeInfo]:
        """Gremlinクエリ結果をNodeInfoに変換"""
        nodes = []
        
        for result in results:
            try:
                if isinstance(result, dict):
                    # エッジ情報を含む結果の場合
                    if 'source' in result and 'edge' in result and 'target' in result:
                        node_info = self._convert_edge_result(result, source_node_id)
                        if node_info:
                            nodes.append(node_info)
                    # 単純なノード結果の場合
                    elif 'id' in result and 'label' in result:
                        node_info = self._convert_simple_node_result(result, source_node_id)
                        if node_info:
                            nodes.append(node_info)
                    # その他の辞書形式
                    else:
                        node_info = self._convert_other_dict_result(result, source_node_id)
                        if node_info:
                            nodes.append(node_info)
                else:
                    # その他の形式
                    node_info = self._convert_other_result(result, source_node_id)
                    if node_info:
                        nodes.append(node_info)
                        
            except Exception as e:
                logger.warning(f"結果変換エラー: {e}, 結果: {result}")
                continue
        
        return nodes
    
    def _convert_edge_result(self, result: Dict[str, Any], source_node_id: str) -> Optional[NodeInfo]:
        """エッジ情報を含む結果を変換"""
        try:
            target_data = result.get('target', {})
            edge_data = result.get('edge', {})
            
            if not target_data or not target_data.get('id'):
                return None
            
            return NodeInfo(
                id=str(target_data.get('id', '')),
                label=str(target_data.get('label', '')),
                properties=target_data.get('properties', {}),
                relationship_type=str(edge_data.get('label', 'connected')),
                distance=1,
                edge_id=str(edge_data.get('id', '')) if edge_data.get('id') else None,
                edge_label=str(edge_data.get('label', '')) if edge_data.get('label') else None
            )
            
        except Exception as e:
            logger.warning(f"エッジ結果変換エラー: {e}")
            return None
    
    def _convert_simple_node_result(self, result: Dict[str, Any], source_node_id: str) -> Optional[NodeInfo]:
        """単純なノード結果を変換"""
        try:
            return NodeInfo(
                id=str(result.get('id', '')),
                label=str(result.get('label', '')),
                properties=result.get('properties', {}),
                relationship_type='connected',
                distance=1,
                edge_id=None,
                edge_label=None
            )
            
        except Exception as e:
            logger.warning(f"単純ノード結果変換エラー: {e}")
            return None
    
    def _convert_other_dict_result(self, result: Dict[str, Any], source_node_id: str) -> Optional[NodeInfo]:
        """その他の辞書形式の結果を変換"""
        try:
            # 可能なキーを探す
            node_id = None
            node_label = None
            
            for key, value in result.items():
                if key in ['id', 'node_id'] and value:
                    node_id = str(value)
                elif key in ['label', 'node_label'] and value:
                    node_label = str(value)
            
            if node_id and node_label:
                return NodeInfo(
                    id=node_id,
                    label=node_label,
                    properties=result.get('properties', {}),
                    relationship_type='connected',
                    distance=1,
                    edge_id=None,
                    edge_label=None
                )
            
            return None
            
        except Exception as e:
            logger.warning(f"その他辞書結果変換エラー: {e}")
            return None
    
    def _convert_other_result(self, result: Any, source_node_id: str) -> Optional[NodeInfo]:
        """その他の形式の結果を変換"""
        try:
            # 文字列の場合
            if isinstance(result, str):
                return NodeInfo(
                    id=result,
                    label='unknown',
                    properties={},
                    relationship_type='connected',
                    distance=1,
                    edge_id=None,
                    edge_label=None
                )
            
            return None
            
        except Exception as e:
            logger.warning(f"その他結果変換エラー: {e}")
            return None
    
    async def get_health_status(self) -> dict:
        """ヘルスステータスを取得"""
        return await self.gremlin_service.get_health_status()
    
    async def disconnect(self):
        """接続を切断"""
        await self.gremlin_service.disconnect()
        self._connected = False
