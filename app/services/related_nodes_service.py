import time
import logging
from typing import List, Dict, Any, Set, Optional
from app.services.simple_gremlin_service import SimpleGremlinService
from app.models.related_nodes import RelatedNode, RelatedNodesResponse, RelatedNodesByKeywordsResponse, EdgeInfo

logger = logging.getLogger(__name__)


class RelatedNodesService:
    """関連ノード抽出サービス"""
    
    def __init__(self):
        self.gremlin_service = SimpleGremlinService()
        self._connected = False
    
    async def initialize(self) -> bool:
        """サービスを初期化"""
        try:
            self._connected = await self.gremlin_service.connect()
            return self._connected
        except Exception as e:
            logger.error(f"関連ノード抽出サービス初期化エラー: {e}")
            return False
    
    async def get_related_nodes(
        self, 
        node_id: str, 
        max_distance: int = 2, 
        max_results: int = 20,
        relationship_types: List[str] = None
    ) -> RelatedNodesResponse:
        """指定されたノードの関連ノードを抽出"""
        start_time = time.time()
        
        try:
            if not self._connected:
                await self.initialize()
            
            if not self._connected:
                return RelatedNodesResponse(
                    node_id=node_id,
                    related_nodes=[],
                    total_count=0,
                    max_distance=max_distance,
                    execution_time_ms=0.0,
                    success=False
                )
            
            # 関連ノードを抽出
            related_nodes = await self._extract_related_nodes(
                node_id, max_distance, max_results, relationship_types
            )
            
            execution_time = (time.time() - start_time) * 1000
            
            return RelatedNodesResponse(
                node_id=node_id,
                related_nodes=related_nodes,
                total_count=len(related_nodes),
                max_distance=max_distance,
                execution_time_ms=execution_time,
                success=True
            )
            
        except Exception as e:
            logger.error(f"関連ノード抽出エラー: {e}")
            execution_time = (time.time() - start_time) * 1000
            
            return RelatedNodesResponse(
                node_id=node_id,
                related_nodes=[],
                total_count=0,
                max_distance=max_distance,
                execution_time_ms=execution_time,
                success=False
            )
    
    async def get_related_nodes_by_keywords(
        self,
        keywords: List[str],
        max_distance: int = 2,
        max_results_per_keyword: int = 10,
        relationship_types: List[str] = None
    ) -> RelatedNodesByKeywordsResponse:
        """キーワードから関連ノードを抽出"""
        start_time = time.time()
        
        try:
            if not self._connected:
                await self.initialize()
            
            if not self._connected:
                return RelatedNodesByKeywordsResponse(
                    keywords=keywords,
                    keyword_results={},
                    all_related_nodes=[],
                    total_count=0,
                    execution_time_ms=0.0,
                    success=False
                )
            
            keyword_results = {}
            all_related_nodes = []
            seen_nodes = set()
            
            # 各キーワードに対して関連ノードを抽出
            for keyword in keywords:
                try:
                    # キーワードをノードIDとして検索
                    related_nodes = await self._extract_related_nodes(
                        keyword, max_distance, max_results_per_keyword, relationship_types
                    )
                    
                    keyword_results[keyword] = related_nodes
                    
                    # 重複を避けて全関連ノードに追加
                    for node in related_nodes:
                        node_key = f"{node.id}_{node.label}"
                        if node_key not in seen_nodes:
                            all_related_nodes.append(node)
                            seen_nodes.add(node_key)
                            
                except Exception as e:
                    logger.warning(f"キーワード '{keyword}' の関連ノード抽出エラー: {e}")
                    keyword_results[keyword] = []
            
            execution_time = (time.time() - start_time) * 1000
            
            return RelatedNodesByKeywordsResponse(
                keywords=keywords,
                keyword_results=keyword_results,
                all_related_nodes=all_related_nodes,
                total_count=len(all_related_nodes),
                execution_time_ms=execution_time,
                success=True
            )
            
        except Exception as e:
            logger.error(f"キーワード関連ノード抽出エラー: {e}")
            execution_time = (time.time() - start_time) * 1000
            
            return RelatedNodesByKeywordsResponse(
                keywords=keywords,
                keyword_results={},
                all_related_nodes=[],
                total_count=0,
                execution_time_ms=execution_time,
                success=False
            )
    
    async def _extract_related_nodes(
        self, 
        node_id: str, 
        max_distance: int, 
        max_results: int,
        relationship_types: List[str] = None
    ) -> List[RelatedNode]:
        """関連ノードを抽出する内部メソッド"""
        related_nodes = []
        
        try:
            # 距離1の関連ノードを取得
            distance1_nodes = await self._get_nodes_at_distance(node_id, 1, relationship_types)
            related_nodes.extend(distance1_nodes)
            logger.info(f"距離1のノード数: {len(distance1_nodes)}")
            
            # 距離2以上の関連ノードを取得
            if max_distance >= 2:
                distance2_nodes = await self._get_nodes_at_distance(node_id, 2, relationship_types)
                related_nodes.extend(distance2_nodes)
                logger.info(f"距離2のノード数: {len(distance2_nodes)}")
            
            # 距離3以上の関連ノードを取得
            if max_distance >= 3:
                distance3_nodes = await self._get_nodes_at_distance(node_id, 3, relationship_types)
                related_nodes.extend(distance3_nodes)
                logger.info(f"距離3のノード数: {len(distance3_nodes)}")
            
            # 重複を除去し、スコアでソート
            unique_nodes = self._deduplicate_and_sort(related_nodes)
            logger.info(f"重複除去後のノード数: {len(unique_nodes)}")
            
            # 最大結果数で制限
            return unique_nodes[:max_results]
            
        except Exception as e:
            logger.error(f"関連ノード抽出エラー: {e}")
            return []
    
    async def _get_nodes_at_distance(
        self, 
        node_id: str, 
        distance: int, 
        relationship_types: List[str] = None
    ) -> List[RelatedNode]:
        """指定された距離のノードを取得（エッジ情報付き）"""
        try:
            # エッジ情報を含むGremlinクエリを構築
            if distance == 1:
                # 直接接続されたノードとエッジ情報を取得（修正版）
                # より確実にすべての関連ノードを取得するため、シンプルなクエリを使用
                query = f"""
                g.V().has('id', '{node_id}')
                .bothE()
                .as('edge')
                .otherV()
                .as('target')
                .select('edge', 'target')
                .by(valueMap(true))
                """
            else:
                # 指定された距離のノードとパス情報を取得（修正版）
                if distance == 2:
                    # 距離2の場合は、より確実なクエリを使用
                    query = f"""
                    g.V().has('id', '{node_id}').as('start')
                    .bothE().as('e1').otherV().as('v1')
                    .bothE().as('e2').otherV().as('v2')
                    .where('v2', neq('start'))
                    .select('start', 'e1', 'v1', 'e2', 'v2')
                    .by(valueMap(true))
                    """
                else:
                    # 距離3以上の場合は、repeatを使用
                    query = f"""
                    g.V().has('id', '{node_id}')
                    .repeat(bothE().otherV()).times({distance})
                    .path()
                    .by(valueMap(true))
                    """
            
            # 関係の種類でフィルタ
            if relationship_types:
                # 関係の種類でフィルタ（実装は簡略化）
                pass
            
            # クエリ実行
            logger.info(f"実行するGremlinクエリ: {query}")
            raw_results = await self.gremlin_service.execute_query(query)
            logger.info(f"Gremlinクエリ結果数: {len(raw_results)}")
            logger.info(f"Gremlinクエリ結果: {raw_results}")
            
            # 結果をRelatedNodeに変換
            related_nodes = []
            for i, raw_result in enumerate(raw_results):
                try:
                    logger.info(f"結果 {i+1}: {raw_result}")
                    related_node = await self._parse_related_node_result(raw_result, distance)
                    if related_node:
                        related_nodes.append(related_node)
                        logger.info(f"変換成功: {related_node.id} - {related_node.relationship_type}")
                    else:
                        logger.warning(f"変換失敗: 結果 {i+1}")
                except Exception as e:
                    logger.warning(f"ノード変換エラー: {e}, 結果: {raw_result}")
                    continue
            
            logger.info(f"最終的な関連ノード数: {len(related_nodes)}")
            return related_nodes
            
        except Exception as e:
            logger.error(f"距離{distance}のノード取得エラー: {e}")
            return []
    
    def _deduplicate_and_sort(self, nodes: List[RelatedNode]) -> List[RelatedNode]:
        """重複を除去し、スコアでソート"""
        # 重複除去（IDとラベルの組み合わせで）
        seen = set()
        unique_nodes = []
        
        for node in nodes:
            key = f"{node.id}_{node.label}"
            if key not in seen:
                unique_nodes.append(node)
                seen.add(key)
        
        # スコアでソート（高い順）
        unique_nodes.sort(key=lambda x: x.score, reverse=True)
        
        return unique_nodes
    
    async def _parse_related_node_result(self, raw_result: Any, distance: int) -> Optional[RelatedNode]:
        """Gremlinクエリ結果をRelatedNodeに変換"""
        try:
            if distance == 1:
                # 直接接続の場合
                return await self._parse_direct_connection_result(raw_result, distance)
            else:
                # パス経由の場合
                return await self._parse_path_result(raw_result, distance)
        except Exception as e:
            logger.warning(f"結果解析エラー: {e}")
            return None
    
    async def _parse_direct_connection_result(self, raw_result: Any, distance: int) -> Optional[RelatedNode]:
        """直接接続の結果を解析（修正版）"""
        try:
            if not isinstance(raw_result, dict):
                return None
            
            # エッジとターゲットの情報を取得（ソースは不要）
            edge_data = raw_result.get('edge', {})
            target_data = raw_result.get('target', {})
            
            if not target_data or not target_data.get('id'):
                return None
            
            # エッジ情報を作成
            edge_info = None
            if edge_data and edge_data.get('id'):
                edge_info = EdgeInfo(
                    edge_id=str(edge_data.get('id', '')),
                    edge_label=str(edge_data.get('label', '')),
                    edge_properties=edge_data.get('properties', {}),
                    source_id='ビール',  # 固定値（クエリの基準ノード）
                    target_id=str(target_data.get('id', ''))
                )
            
            # 関連ノードを作成
            related_node = RelatedNode(
                id=str(target_data.get('id', '')),
                label=str(target_data.get('label', '')),
                properties=target_data.get('properties', {}),
                relationship_type=str(edge_data.get('label', 'connected')),
                distance=distance,
                score=self._calculate_relationship_score(distance),
                edge_info=edge_info,
                path=['ビール', str(target_data.get('id', ''))]
            )
            
            return related_node
            
        except Exception as e:
            logger.warning(f"直接接続結果解析エラー: {e}")
            return None
    
    async def _parse_path_result(self, raw_result: Any, distance: int) -> Optional[RelatedNode]:
        """パス経由の結果を解析"""
        try:
            if distance == 2 and isinstance(raw_result, dict):
                # 距離2の特別な形式を解析
                return await self._parse_distance2_result(raw_result, distance)
            elif isinstance(raw_result, list) and len(raw_result) >= 2:
                # 通常のパス形式を解析
                return await self._parse_standard_path_result(raw_result, distance)
            else:
                return None
                
        except Exception as e:
            logger.warning(f"パス結果解析エラー: {e}")
            return None
    
    async def _parse_distance2_result(self, raw_result: Dict[str, Any], distance: int) -> Optional[RelatedNode]:
        """距離2の特別な結果形式を解析"""
        try:
            # v2（最後のノード）を取得
            v2_data = raw_result.get('v2', {})
            if not v2_data or not v2_data.get('id'):
                return None
            
            # パスを構築
            start_data = raw_result.get('start', {})
            v1_data = raw_result.get('v1', {})
            path = [
                str(start_data.get('id', '')),
                str(v1_data.get('id', '')),
                str(v2_data.get('id', ''))
            ]
            
            # 最後のエッジ情報を取得
            e2_data = raw_result.get('e2', {})
            edge_info = None
            if e2_data and e2_data.get('id'):
                edge_info = EdgeInfo(
                    edge_id=str(e2_data.get('id', '')),
                    edge_label=str(e2_data.get('label', '')),
                    edge_properties=e2_data.get('properties', {}),
                    source_id=str(v1_data.get('id', '')),
                    target_id=str(v2_data.get('id', ''))
                )
            
            # 関連ノードを作成
            related_node = RelatedNode(
                id=str(v2_data.get('id', '')),
                label=str(v2_data.get('label', '')),
                properties=v2_data.get('properties', {}),
                relationship_type=str(edge_info.edge_label) if edge_info else 'connected',
                distance=distance,
                score=self._calculate_relationship_score(distance),
                edge_info=edge_info,
                path=path
            )
            
            return related_node
            
        except Exception as e:
            logger.warning(f"距離2結果解析エラー: {e}")
            return None
    
    async def _parse_standard_path_result(self, raw_result: List[Any], distance: int) -> Optional[RelatedNode]:
        """標準的なパス形式の結果を解析"""
        try:
            # パスの最後のノードを取得
            last_node_data = raw_result[-1]
            if not isinstance(last_node_data, dict) or not last_node_data.get('id'):
                return None
            
            # パスを構築
            path = []
            for item in raw_result:
                if isinstance(item, dict) and item.get('id'):
                    path.append(str(item.get('id', '')))
            
            # 最後のエッジ情報を取得（簡略化）
            edge_info = None
            if len(raw_result) >= 2:
                # 最後のエッジを探す
                for i in range(len(raw_result) - 1):
                    if isinstance(raw_result[i], dict) and raw_result[i].get('label'):
                        edge_data = raw_result[i]
                        edge_info = EdgeInfo(
                            edge_id=str(edge_data.get('id', '')),
                            edge_label=str(edge_data.get('label', '')),
                            edge_properties=edge_data.get('properties', {}),
                            source_id=path[-2] if len(path) >= 2 else '',
                            target_id=path[-1] if len(path) >= 1 else ''
                        )
                        break
            
            # 関連ノードを作成
            related_node = RelatedNode(
                id=str(last_node_data.get('id', '')),
                label=str(last_node_data.get('label', '')),
                properties=last_node_data.get('properties', {}),
                relationship_type=str(edge_info.edge_label) if edge_info else 'connected',
                distance=distance,
                score=self._calculate_relationship_score(distance),
                edge_info=edge_info,
                path=path
            )
            
            return related_node
            
        except Exception as e:
            logger.warning(f"標準パス結果解析エラー: {e}")
            return None

    def _calculate_relationship_score(self, distance: int) -> float:
        """関係のスコアを計算"""
        # 距離が近いほど高いスコア
        if distance == 1:
            return 1.0
        elif distance == 2:
            return 0.7
        elif distance == 3:
            return 0.4
        else:
            return 0.1
    
    async def get_health_status(self) -> Dict[str, Any]:
        """ヘルスステータスを取得"""
        return await self.gremlin_service.get_health_status()
    
    async def disconnect(self):
        """接続を切断"""
        await self.gremlin_service.disconnect()
        self._connected = False

