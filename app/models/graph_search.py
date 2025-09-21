from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional


class GraphSearchRequest(BaseModel):
    """Graph検索リクエストモデル"""
    query: str = Field(..., description="検索クエリ", min_length=1, max_length=200)


class GraphSearchResult(BaseModel):
    """Graph検索結果アイテム"""
    id: str = Field(..., description="ノードID")
    label: str = Field(..., description="ノードラベル")
    properties: Dict[str, Any] = Field(default_factory=dict, description="ノードプロパティ")
    score: float = Field(..., description="スコア", ge=0.0, le=1.0)


class GraphSearchResponse(BaseModel):
    """Graph検索レスポンスモデル"""
    query: str = Field(..., description="検索クエリ")
    results: List[GraphSearchResult] = Field(..., description="検索結果")
    total_count: int = Field(..., description="総結果数")
    execution_time_ms: float = Field(..., description="実行時間（ミリ秒）")
    success: bool = Field(..., description="検索成功フラグ")


class GraphSearchHealthResponse(BaseModel):
    """Graph検索ヘルスチェックレスポンス"""
    status: str = Field(..., description="ステータス")
    gremlin_connected: bool = Field(..., description="Gremlin接続状態")
    vertex_count: Optional[int] = Field(None, description="頂点数")
    error: Optional[str] = Field(None, description="エラーメッセージ")




