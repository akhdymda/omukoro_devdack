from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any, Literal
from enum import Enum

class SearchType(str, Enum):
    """検索タイプの列挙型"""
    TRADITIONAL = "traditional"
    HYBRID = "hybrid"

class HybridSearchRequest(BaseModel):
    """ハイブリッド検索リクエストモデル"""
    query: str = Field(..., description="検索クエリ", min_length=1, max_length=1000)
    search_type: SearchType = Field(..., description="検索タイプ（traditional または hybrid）")
    limit: int = Field(default=10, ge=1, le=50, description="取得件数")
    include_graph_relations: bool = Field(default=True, description="GraphRAGの関係性情報を含めるか")
    
    class Config:
        json_schema_extra = {
            "example": {
                "query": "酒税法 販売業者",
                "search_type": "hybrid",
                "limit": 10,
                "include_graph_relations": True
            }
        }

class SearchResultSource(str, Enum):
    """検索結果のソース"""
    TRADITIONAL = "traditional"
    GRAPH = "graph"
    HYBRID = "hybrid"

class GraphRelation(BaseModel):
    """GraphRAGの関係性情報"""
    target_id: str = Field(..., description="関連する頂点のID")
    target_type: str = Field(..., description="関連する頂点のタイプ")
    relation_type: str = Field(..., description="関係のタイプ")
    relation_properties: Dict[str, Any] = Field(default_factory=dict, description="関係のプロパティ")
    distance: int = Field(..., description="関係の距離（ホップ数）")

class SearchResult(BaseModel):
    """検索結果の個別アイテム"""
    id: str = Field(..., description="法令ID")
    text: str = Field(..., description="法令テキスト")
    prefLabel: str = Field(..., description="法令名")
    score: float = Field(..., description="検索スコア", ge=0.0, le=1.0)
    source: SearchResultSource = Field(..., description="検索結果のソース")
    graph_relations: Optional[List[GraphRelation]] = Field(default=None, description="GraphRAGで見つかった関連情報")
    metadata: Optional[Dict[str, Any]] = Field(default=None, description="追加メタデータ")

class HybridSearchResponse(BaseModel):
    """ハイブリッド検索レスポンスモデル"""
    search_type: SearchType = Field(..., description="実行された検索タイプ")
    query: str = Field(..., description="検索クエリ")
    results: List[SearchResult] = Field(..., description="検索結果リスト")
    total_count: int = Field(..., description="総結果数")
    traditional_count: int = Field(default=0, description="通常RAGの結果数")
    graph_count: int = Field(default=0, description="GraphRAGの結果数")
    hybrid_count: int = Field(default=0, description="ハイブリッド結果数")
    execution_time_ms: Optional[float] = Field(default=None, description="実行時間（ミリ秒）")
    
    class Config:
        json_schema_extra = {
            "example": {
                "search_type": "hybrid",
                "query": "酒税法 販売業者",
                "results": [
                    {
                        "id": "law_001",
                        "text": "酒税法の条文...",
                        "prefLabel": "酒税法",
                        "score": 0.85,
                        "source": "hybrid",
                        "graph_relations": [
                            {
                                "target_id": "article_001",
                                "target_type": "条",
                                "relation_type": "包含",
                                "relation_properties": {},
                                "distance": 1
                            }
                        ]
                    }
                ],
                "total_count": 10,
                "traditional_count": 5,
                "graph_count": 3,
                "hybrid_count": 2
            }
        }

class SearchError(BaseModel):
    """検索エラー情報"""
    error_type: str = Field(..., description="エラータイプ")
    message: str = Field(..., description="エラーメッセージ")
    source: str = Field(..., description="エラーが発生したソース")

class HybridSearchErrorResponse(BaseModel):
    """ハイブリッド検索エラーレスポンス"""
    search_type: SearchType = Field(..., description="検索タイプ")
    query: str = Field(..., description="検索クエリ")
    errors: List[SearchError] = Field(..., description="エラーリスト")
    partial_results: Optional[List[SearchResult]] = Field(default=None, description="部分的な結果（エラー時）")
    total_count: int = Field(default=0, description="取得できた結果数")



