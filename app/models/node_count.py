from pydantic import BaseModel, Field
from typing import Optional


class NodeCountRequest(BaseModel):
    """ノード数カウントリクエスト"""
    node_id: str = Field(..., description="ノードID", min_length=1)


class NodeCountResponse(BaseModel):
    """ノード数カウントレスポンス"""
    node_id: str = Field(..., description="ノードID")
    related_nodes_count: int = Field(..., description="距離1の双方向関連ノード数")
    execution_time_ms: float = Field(..., description="実行時間（ミリ秒）")
    success: bool = Field(..., description="実行成功フラグ")
    error_message: Optional[str] = Field(None, description="エラーメッセージ")



