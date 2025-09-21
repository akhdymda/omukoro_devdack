import time
import logging
from typing import List, Dict, Any
from app.services.simple_gremlin_service import SimpleGremlinService
from app.models.graph_search import GraphSearchResult, GraphSearchResponse

logger = logging.getLogger(__name__)


class GraphSearchService:
    """Graph検索サービス"""
    
    def __init__(self):
        self.gremlin_service = SimpleGremlinService()
        self._connected = False
    
    async def initialize(self) -> bool:
        """サービスを初期化"""
        try:
            self._connected = await self.gremlin_service.connect()
            return self._connected
        except Exception as e:
            logger.error(f"Graph検索サービス初期化エラー: {e}")
            return False
    
    async def search(self, query: str, limit: int = 10) -> GraphSearchResponse:
        """Graph検索を実行"""
        start_time = time.time()
        
        try:
            if not self._connected:
                await self.initialize()
            
            if not self._connected:
                return GraphSearchResponse(
                    query=query,
                    results=[],
                    total_count=0,
                    execution_time_ms=0.0,
                    success=False
                )
            
            # Gremlinクエリを構築
            gremlin_query = self._build_search_query(query, limit)
            logger.info(f"実行クエリ: {gremlin_query}")
            
            # クエリ実行
            raw_results = await self.gremlin_service.execute_query(gremlin_query)
            
            # 結果を整形
            results = self._format_results(raw_results, query)
            
            execution_time = (time.time() - start_time) * 1000
            
            return GraphSearchResponse(
                query=query,
                results=results,
                total_count=len(results),
                execution_time_ms=execution_time,
                success=True
            )
            
        except Exception as e:
            logger.error(f"Graph検索エラー: {e}")
            execution_time = (time.time() - start_time) * 1000
            
            return GraphSearchResponse(
                query=query,
                results=[],
                total_count=0,
                execution_time_ms=execution_time,
                success=False
            )
    
    def _build_search_query(self, query: str, limit: int) -> str:
        """検索クエリを構築"""
        # クエリをエスケープ
        escaped_query = query.replace("'", "\\'")
        
        # IDで完全一致（最も確実な検索）
        return f"g.V().has('id', '{escaped_query}').limit({limit})"
    
    def _format_results(self, raw_results: List[Dict[str, Any]], query: str) -> List[GraphSearchResult]:
        """結果を整形"""
        results = []
        
        logger.info(f"生の結果: {raw_results}")
        
        for raw_result in raw_results:
            try:
                logger.info(f"処理中の結果: {raw_result}")
                
                # 基本情報を取得
                node_id = raw_result.get('id', '')
                label = raw_result.get('label', '')
                properties = raw_result.get('properties', {})
                
                logger.info(f"抽出された情報 - ID: '{node_id}', Label: '{label}', Properties: {properties}")
                
                # スコアを計算（シンプルな実装）
                score = self._calculate_score(node_id, label, properties, query)
                
                result = GraphSearchResult(
                    id=node_id,
                    label=label,
                    properties=properties,
                    score=score
                )
                
                logger.info(f"作成された結果: {result}")
                results.append(result)
                
            except Exception as e:
                logger.error(f"結果整形エラー: {e}, 結果: {raw_result}")
                continue
        
        # スコアでソート
        results.sort(key=lambda x: x.score, reverse=True)
        
        logger.info(f"最終結果: {results}")
        return results
    
    def _calculate_score(self, node_id: str, label: str, properties: Dict[str, Any], query: str) -> float:
        """スコアを計算"""
        query_lower = query.lower()
        score = 0.0
        
        # ID完全一致
        if node_id.lower() == query_lower:
            score += 1.0
        # ID部分一致
        elif query_lower in node_id.lower():
            score += 0.8
        
        # ラベル完全一致
        if label.lower() == query_lower:
            score += 0.9
        # ラベル部分一致
        elif query_lower in label.lower():
            score += 0.7
        
        # プロパティで部分一致
        for key, value in properties.items():
            if isinstance(value, str) and query_lower in value.lower():
                score += 0.5
        
        # スコアを0-1の範囲に正規化
        return min(1.0, score)
    
    async def get_health_status(self) -> Dict[str, Any]:
        """ヘルスステータスを取得"""
        return await self.gremlin_service.get_health_status()
    
    async def disconnect(self):
        """接続を切断"""
        await self.gremlin_service.disconnect()
        self._connected = False
