from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional
from enum import Enum


class SearchType(str, Enum):
    """検索タイプ"""
    VECTOR = "vector"
    GRAPH = "graph"
    KEYWORD = "keyword"


class DocumentChunk(BaseModel):
    """文書チャンク"""
    id: str = Field(..., description="チャンクID")
    content: str = Field(..., description="チャンク内容")
    source: str = Field(..., description="ソース文書")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="メタデータ")
    score: float = Field(..., description="関連性スコア", ge=0.0, le=1.0)
    search_type: SearchType = Field(..., description="検索タイプ")
    node_id: Optional[str] = Field(None, description="関連ノードID")
    edge_info: Optional[Dict[str, Any]] = Field(None, description="エッジ情報")


class SearchResult(BaseModel):
    """検索結果"""
    search_type: SearchType = Field(..., description="検索タイプ")
    documents: List[DocumentChunk] = Field(..., description="検索された文書")
    total_count: int = Field(..., description="総件数")
    execution_time_ms: float = Field(..., description="実行時間（ミリ秒）")


class HybridSearchRequest(BaseModel):
    """ハイブリッド検索リクエスト"""
    query: str = Field(..., description="検索クエリ", min_length=1)
    max_chunks: int = Field(default=5, description="最大チャンク数", ge=1, le=20)
    vector_weight: float = Field(default=0.4, description="ベクトル検索の重み", ge=0.0, le=1.0)
    graph_weight: float = Field(default=0.4, description="グラフ検索の重み", ge=0.0, le=1.0)
    keyword_weight: float = Field(default=0.2, description="キーワード検索の重み", ge=0.0, le=1.0)
    enable_query_expansion: bool = Field(default=True, description="クエリ拡張を有効にするか")
    max_related_nodes: int = Field(default=10, description="最大関連ノード数", ge=1, le=50)


class HybridSearchResponse(BaseModel):
    """ハイブリッド検索レスポンス"""
    query: str = Field(..., description="検索クエリ")
    expanded_query: Optional[str] = Field(None, description="拡張されたクエリ")
    final_chunks: List[DocumentChunk] = Field(..., description="最終選択されたチャンク")
    search_results: Dict[SearchType, SearchResult] = Field(..., description="各検索の結果")
    total_execution_time_ms: float = Field(..., description="総実行時間（ミリ秒）")
    success: bool = Field(..., description="成功フラグ")
    error_message: Optional[str] = Field(None, description="エラーメッセージ")


class QueryExpansionRequest(BaseModel):
    """クエリ拡張リクエスト"""
    query: str = Field(..., description="元のクエリ", min_length=1)
    max_related_nodes: int = Field(default=10, description="最大関連ノード数", ge=1, le=50)


class QueryExpansionResponse(BaseModel):
    """クエリ拡張レスポンス"""
    original_query: str = Field(..., description="元のクエリ")
    expanded_query: str = Field(..., description="拡張されたクエリ")
    related_nodes: List[Dict[str, Any]] = Field(..., description="関連ノード情報")
    keywords: List[str] = Field(..., description="抽出されたキーワード")
    execution_time_ms: float = Field(..., description="実行時間（ミリ秒）")
    success: bool = Field(..., description="成功フラグ")
    error_message: Optional[str] = Field(None, description="エラーメッセージ")

