from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional


class EdgeInfo(BaseModel):
    """エッジ（関係）情報"""
    edge_id: str = Field(..., description="エッジID")
    edge_label: str = Field(..., description="エッジラベル")
    edge_properties: Dict[str, Any] = Field(default_factory=dict, description="エッジプロパティ")
    source_id: str = Field(..., description="ソースノードID")
    target_id: str = Field(..., description="ターゲットノードID")


class RelatedNode(BaseModel):
    """関連ノード情報"""
    id: str = Field(..., description="ノードID")
    label: str = Field(..., description="ノードラベル")
    properties: Dict[str, Any] = Field(default_factory=dict, description="ノードプロパティ")
    relationship_type: str = Field(..., description="関係の種類")
    distance: int = Field(..., description="距離（ホップ数）", ge=1)
    score: float = Field(..., description="関連度スコア", ge=0.0, le=1.0)
    edge_info: Optional[EdgeInfo] = Field(None, description="エッジ情報")
    path: Optional[List[str]] = Field(None, description="パス（ノードIDのリスト）")


class RelatedNodesRequest(BaseModel):
    """関連ノード抽出リクエスト"""
    node_id: str = Field(..., description="基準ノードID", min_length=1)
    max_distance: int = Field(default=2, description="最大距離", ge=1, le=5)
    max_results: int = Field(default=20, description="最大結果数", ge=1, le=100)
    relationship_types: Optional[List[str]] = Field(default=None, description="抽出する関係の種類")


class RelatedNodesResponse(BaseModel):
    """関連ノード抽出レスポンス"""
    node_id: str = Field(..., description="基準ノードID")
    related_nodes: List[RelatedNode] = Field(..., description="関連ノード一覧")
    total_count: int = Field(..., description="総関連ノード数")
    max_distance: int = Field(..., description="最大距離")
    execution_time_ms: float = Field(..., description="実行時間（ミリ秒）")
    success: bool = Field(..., description="抽出成功フラグ")


class RelatedNodesByKeywordsRequest(BaseModel):
    """キーワードから関連ノード抽出リクエスト"""
    keywords: List[str] = Field(..., description="キーワード一覧", min_items=1, max_items=10)
    max_distance: int = Field(default=2, description="最大距離", ge=1, le=5)
    max_results_per_keyword: int = Field(default=10, description="キーワードあたりの最大結果数", ge=1, le=50)
    relationship_types: Optional[List[str]] = Field(default=None, description="抽出する関係の種類")


class RelatedNodesByKeywordsResponse(BaseModel):
    """キーワードから関連ノード抽出レスポンス"""
    keywords: List[str] = Field(..., description="キーワード一覧")
    keyword_results: Dict[str, List[RelatedNode]] = Field(..., description="キーワード別関連ノード")
    all_related_nodes: List[RelatedNode] = Field(..., description="全関連ノード（重複除去）")
    total_count: int = Field(..., description="総関連ノード数")
    execution_time_ms: float = Field(..., description="実行時間（ミリ秒）")
    success: bool = Field(..., description="抽出成功フラグ")

