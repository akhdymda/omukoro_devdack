from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional
from enum import Enum


class RAGType(str, Enum):
    """RAGタイプ"""
    TRADITIONAL = "traditional"
    HYBRID = "hybrid"


class DocumentChunk(BaseModel):
    """文書チャンク（従来RAG用）"""
    chunk_id: str = Field(..., description="チャンクID")
    prefLabel: str = Field(..., description="法令名")
    section_label: str = Field(..., description="セクションラベル")
    text: str = Field(..., description="チャンクテキスト")
    score: float = Field(..., description="関連性スコア", ge=0.0, le=1.0)
    search_type: str = Field(..., description="検索タイプ")


class HybridDocumentChunk(BaseModel):
    """ハイブリッドRAG用文書チャンク"""
    id: str = Field(..., description="チャンクID")
    content: str = Field(..., description="チャンク内容")
    source: str = Field(..., description="ソース文書")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="メタデータ")
    score: float = Field(..., description="関連性スコア", ge=0.0, le=1.0)
    search_type: str = Field(..., description="検索タイプ")
    node_id: Optional[str] = Field(None, description="関連ノードID")
    edge_info: Optional[Dict[str, Any]] = Field(None, description="エッジ情報")


class RAGComparisonRequest(BaseModel):
    """RAG比較リクエスト"""
    query: str = Field(..., description="検索クエリ", min_length=1)
    traditional_limit: int = Field(default=10, description="従来RAGの取得件数", ge=1, le=20)
    hybrid_max_chunks: int = Field(default=10, description="ハイブリッドRAGの最大チャンク数", ge=1, le=20)
    hybrid_vector_weight: float = Field(default=0.4, description="ハイブリッドRAGのベクトル検索重み", ge=0.0, le=1.0)
    hybrid_graph_weight: float = Field(default=0.4, description="ハイブリッドRAGのグラフ検索重み", ge=0.0, le=1.0)
    hybrid_keyword_weight: float = Field(default=0.2, description="ハイブリッドRAGのキーワード検索重み", ge=0.0, le=1.0)
    enable_query_expansion: bool = Field(default=True, description="クエリ拡張を有効にするか")
    hybrid_max_related_nodes: int = Field(default=10, description="ハイブリッドRAGの最大関連ノード数", ge=1, le=50)


class RAGAnalysis(BaseModel):
    """RAG比較分析結果"""
    analysis: str = Field(..., description="分析概要")
    traditional_advantages: List[str] = Field(..., description="従来RAGの優位性")
    hybrid_advantages: List[str] = Field(..., description="ハイブリッドRAGの優位性")
    recommendation: str = Field(..., description="推奨事項")


class RAGComparisonResponse(BaseModel):
    """RAG比較レスポンス"""
    query: str = Field(..., description="検索クエリ")
    traditional_rag_labels: List[str] = Field(..., description="従来RAGで抽出されたprefLabelのリスト")
    hybrid_rag_labels: List[str] = Field(..., description="ハイブリッドRAGで抽出されたprefLabelのリスト")
    traditional_rag: Dict[str, Any] = Field(..., description="従来RAGの結果")
    hybrid_rag: Dict[str, Any] = Field(..., description="ハイブリッドRAGの結果")
    comparison_metrics: Dict[str, Any] = Field(..., description="比較メトリクス")
    analysis: Optional[RAGAnalysis] = Field(None, description="RAG比較分析結果")
    total_execution_time_ms: float = Field(..., description="総実行時間（ミリ秒）")
    success: bool = Field(..., description="成功フラグ")
    error_message: Optional[str] = Field(None, description="エラーメッセージ")
