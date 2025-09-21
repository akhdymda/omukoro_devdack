from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional


class NodeInfo(BaseModel):
    """ノード情報"""
    id: str = Field(..., description="ノードID")
    label: str = Field(..., description="ノードラベル")
    properties: Dict[str, Any] = Field(default_factory=dict, description="ノードプロパティ")
    relationship_type: str = Field(..., description="関係の種類")
    distance: int = Field(..., description="距離", ge=1)
    edge_id: Optional[str] = Field(None, description="エッジID")
    edge_label: Optional[str] = Field(None, description="エッジラベル")


class NodesInfoRequest(BaseModel):
    """ノード情報取得リクエスト"""
    node_id: str = Field(..., description="ノードID", min_length=1)
    max_results: int = Field(default=20, description="最大結果数", ge=1, le=100)


class NodesInfoResponse(BaseModel):
    """ノード情報取得レスポンス"""
    node_id: str = Field(..., description="ノードID")
    related_nodes: List[NodeInfo] = Field(..., description="関連ノード一覧")
    total_count: int = Field(..., description="総関連ノード数")
    execution_time_ms: float = Field(..., description="実行時間（ミリ秒）")
    success: bool = Field(..., description="実行成功フラグ")
    error_message: Optional[str] = Field(None, description="エラーメッセージ")



