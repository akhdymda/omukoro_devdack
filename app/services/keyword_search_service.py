import logging
from typing import List, Dict, Any

logger = logging.getLogger(__name__)


class KeywordSearchService:
    """キーワード検索サービス（モック実装）"""
    
    def __init__(self):
        self.initialized = False
    
    async def initialize(self) -> bool:
        """サービスを初期化"""
        try:
            # モック実装：常に成功
            self.initialized = True
            logger.info("キーワード検索サービス初期化完了（モック）")
            return True
        except Exception as e:
            logger.error(f"キーワード検索サービス初期化エラー: {e}")
            return False
    
    async def search(self, query: str, top_k: int = 15) -> List[Dict[str, Any]]:
        """キーワード検索を実行（モック実装）"""
        try:
            # モックデータを返す
            mock_results = [
                {
                    "content": f"キーワード検索結果1: {query}のキーワードマッチした文書です。",
                    "source": "manual1.pdf",
                    "metadata": {"chapter": 1, "keyword_count": 5},
                    "score": 0.90,
                    "node_id": "keyword_node1",
                    "edge_info": None
                },
                {
                    "content": f"キーワード検索結果2: {query}を含む詳細な説明文書です。",
                    "source": "manual2.pdf",
                    "metadata": {"chapter": 3, "keyword_count": 3},
                    "score": 0.85,
                    "node_id": "keyword_node2",
                    "edge_info": None
                },
                {
                    "content": f"キーワード検索結果3: {query}の関連キーワードを含む文書です。",
                    "source": "manual3.pdf",
                    "metadata": {"chapter": 2, "keyword_count": 2},
                    "score": 0.78,
                    "node_id": "keyword_node3",
                    "edge_info": None
                },
                {
                    "content": f"キーワード検索結果4: {query}の補足情報が含まれています。",
                    "source": "manual4.pdf",
                    "metadata": {"chapter": 4, "keyword_count": 1},
                    "score": 0.72,
                    "node_id": "keyword_node4",
                    "edge_info": None
                },
                {
                    "content": f"キーワード検索結果5: {query}の参考資料です。",
                    "source": "manual5.pdf",
                    "metadata": {"chapter": 5, "keyword_count": 1},
                    "score": 0.68,
                    "node_id": "keyword_node5",
                    "edge_info": None
                }
            ]
            
            return mock_results[:top_k]
            
        except Exception as e:
            logger.error(f"キーワード検索エラー: {e}")
            return []
    
    async def get_health_status(self) -> Dict[str, Any]:
        """ヘルスステータスを取得"""
        return {
            "initialized": self.initialized,
            "service_type": "keyword_search",
            "status": "healthy" if self.initialized else "unhealthy"
        }

