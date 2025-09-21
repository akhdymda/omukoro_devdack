import time
import logging
import asyncio
from typing import List, Dict, Any, Optional, Tuple
from collections import defaultdict
import re

from app.models.hybrid_rag import (
    HybridSearchRequest, HybridSearchResponse, QueryExpansionRequest, QueryExpansionResponse,
    DocumentChunk, SearchResult, SearchType
)
from app.services.simple_gremlin_service import SimpleGremlinService
from app.services.nodes_info_service import NodesInfoService
from app.services.vector_search_service import VectorSearchService
from app.services.keyword_search_service import KeywordSearchService
from app.services.cosmos_service import CosmosService

logger = logging.getLogger(__name__)


class HybridRAGService:
    """ハイブリッドRAGサービス"""
    
    def __init__(self):
        self.gremlin_service = SimpleGremlinService()
        self.nodes_info_service = NodesInfoService()
        self.vector_search_service = VectorSearchService()
        self.keyword_search_service = KeywordSearchService()
        self.cosmos_service = CosmosService()
        self._initialized = False
    
    async def initialize(self) -> bool:
        """サービスを初期化"""
        try:
            # 各サービスの初期化
            gremlin_connected = await self.gremlin_service.connect()
            nodes_initialized = await self.nodes_info_service.initialize()
            vector_initialized = await self.vector_search_service.initialize()
            keyword_initialized = await self.keyword_search_service.initialize()
            
            self._initialized = all([
                gremlin_connected, 
                nodes_initialized, 
                vector_initialized, 
                keyword_initialized
            ])
            
            if self._initialized:
                logger.info("ハイブリッドRAGサービス初期化完了")
            else:
                logger.error("ハイブリッドRAGサービス初期化失敗")
            
            return self._initialized
            
        except Exception as e:
            logger.error(f"ハイブリッドRAGサービス初期化エラー: {e}")
            return False
    
    async def hybrid_search(self, request: HybridSearchRequest) -> HybridSearchResponse:
        """ハイブリッド検索を実行"""
        start_time = time.time()
        
        try:
            if not self._initialized:
                await self.initialize()
            
            if not self._initialized:
                execution_time = (time.time() - start_time) * 1000
                return HybridSearchResponse(
                    query=request.query,
                    final_chunks=[],
                    search_results={},
                    total_execution_time_ms=execution_time,
                    success=False,
                    error_message="サービス初期化に失敗しました"
                )
            
            # 1. クエリ拡張（オプション）
            expanded_query = request.query
            if request.enable_query_expansion:
                expansion_result = await self._expand_query(request.query, request.max_related_nodes)
                if expansion_result.success:
                    expanded_query = expansion_result.expanded_query
                    logger.info(f"クエリ拡張完了: {request.query} -> {expanded_query}")
            
            # 2. 並列検索実行
            search_tasks = [
                self._vector_search(request.query),
                self._graph_search(request.query, request.max_related_nodes),
                self._keyword_search(expanded_query)
            ]
            
            vector_result, graph_result, keyword_result = await asyncio.gather(
                *search_tasks, return_exceptions=True
            )
            
            # 3. 検索結果を統合
            search_results = {
                SearchType.VECTOR: vector_result if not isinstance(vector_result, Exception) else SearchResult(
                    search_type=SearchType.VECTOR,
                    documents=[],
                    total_count=0,
                    execution_time_ms=0.0
                ),
                SearchType.GRAPH: graph_result if not isinstance(graph_result, Exception) else SearchResult(
                    search_type=SearchType.GRAPH,
                    documents=[],
                    total_count=0,
                    execution_time_ms=0.0
                ),
                SearchType.KEYWORD: keyword_result if not isinstance(keyword_result, Exception) else SearchResult(
                    search_type=SearchType.KEYWORD,
                    documents=[],
                    total_count=0,
                    execution_time_ms=0.0
                )
            }
            
            # 4. 結果統合・重み付け
            all_documents = []
            for search_result in search_results.values():
                all_documents.extend(search_result.documents)
            
            # 重複除去とスコア計算
            deduplicated_documents = self._deduplicate_and_score(
                all_documents, 
                request.vector_weight, 
                request.graph_weight, 
                request.keyword_weight
            )
            
            # 5. 10つの関連条文を効果的に選抜
            try:
                final_documents = await self._select_effective_documents(
                    deduplicated_documents,
                    request.query,
                    max_documents=request.max_chunks
                )
            except Exception as e:
                logger.error(f"効果的選抜エラー: {e}")
                # エラーが発生した場合は従来の方法で選択
                final_documents = self._select_final_chunks(deduplicated_documents, request.max_chunks)
            
            execution_time = (time.time() - start_time) * 1000
            
            return HybridSearchResponse(
                query=request.query,
                expanded_query=expanded_query if request.enable_query_expansion else None,
                final_chunks=final_documents,
                search_results=search_results,
                total_execution_time_ms=execution_time,
                success=True,
                error_message=None
            )
            
        except Exception as e:
            logger.error(f"ハイブリッド検索エラー: {e}")
            execution_time = (time.time() - start_time) * 1000
            
            return HybridSearchResponse(
                query=request.query,
                final_chunks=[],
                search_results={},
                total_execution_time_ms=execution_time,
                success=False,
                error_message=str(e)
            )
    
    async def expand_query(self, request: QueryExpansionRequest) -> QueryExpansionResponse:
        """クエリ拡張を実行"""
        start_time = time.time()
        
        try:
            if not self._initialized:
                await self.initialize()
            
            if not self._initialized:
                execution_time = (time.time() - start_time) * 1000
                return QueryExpansionResponse(
                    original_query=request.query,
                    expanded_query=request.query,
                    related_nodes=[],
                    keywords=[],
                    execution_time_ms=execution_time,
                    success=False,
                    error_message="サービス初期化に失敗しました"
                )
            
            result = await self._expand_query(request.query, request.max_related_nodes)
            result.execution_time_ms = (time.time() - start_time) * 1000
            
            return result
            
        except Exception as e:
            logger.error(f"クエリ拡張エラー: {e}")
            execution_time = (time.time() - start_time) * 1000
            
            return QueryExpansionResponse(
                original_query=request.query,
                expanded_query=request.query,
                related_nodes=[],
                keywords=[],
                execution_time_ms=execution_time,
                success=False,
                error_message=str(e)
            )
    
    async def _expand_query(self, query: str, max_related_nodes: int) -> QueryExpansionResponse:
        """クエリ拡張の内部実装"""
        try:
            # 1. クエリからノードを抽出
            extracted_nodes = self._extract_nodes_from_query(query)
            logger.info(f"抽出されたノード: {extracted_nodes}")
            
            # 2. 各ノードの関連ノードを取得
            all_related_nodes = []
            for node in extracted_nodes:
                try:
                    nodes_info = await self.nodes_info_service.get_related_nodes_info(
                        node, max_related_nodes
                    )
                    if nodes_info.success:
                        for related_node in nodes_info.related_nodes:
                            all_related_nodes.append({
                                "id": related_node.id,
                                "label": related_node.label,
                                "relationship_type": related_node.relationship_type,
                                "distance": related_node.distance
                            })
                except Exception as e:
                    logger.warning(f"ノード '{node}' の関連ノード取得エラー: {e}")
                    continue
            
            # 3. キーワードを抽出
            keywords = self._extract_keywords(all_related_nodes)
            
            # 4. 拡張クエリを生成
            expanded_query = self._generate_expanded_query(query, keywords)
            
            return QueryExpansionResponse(
                original_query=query,
                expanded_query=expanded_query,
                related_nodes=all_related_nodes,
                keywords=keywords,
                execution_time_ms=0.0,
                success=True,
                error_message=None
            )
            
        except Exception as e:
            logger.error(f"クエリ拡張内部エラー: {e}")
            return QueryExpansionResponse(
                original_query=query,
                expanded_query=query,
                related_nodes=[],
                keywords=[],
                execution_time_ms=0.0,
                success=False,
                error_message=str(e)
            )
    
    def _extract_nodes_from_query(self, query: str) -> List[str]:
        """クエリからノードを抽出（改善版）"""
        # 日本語の単語を抽出
        keywords = re.findall(r'[\u3040-\u309F\u30A0-\u30FF\u4E00-\u9FAF]+', query)
        
        # 一般的なストップワードを除外
        stop_words = {
            'の', 'は', 'が', 'を', 'に', 'で', 'と', 'から', 'まで', 'です', 'である', 'だ', 'である',
            '何', 'か', 'について', 'について', '教えて', 'ください', 'です', 'ます', 'である',
            '必要', 'な', 'に', 'ついて', 'について', '教えて', 'ください'
        }
        
        # より厳密なフィルタリング
        filtered_keywords = []
        for kw in keywords:
            if (kw not in stop_words and 
                len(kw) > 1 and 
                not kw.isdigit() and  # 数字を除外
                kw not in ['必要', 'な', 'に', 'ついて', 'について', '教えて', 'ください']):
                filtered_keywords.append(kw)
        
        # 既知の重要なノードを優先
        priority_nodes = ['ビール', '酒税', '新酒税法', '製造免許', '販売業免許', '酒類製造免許']
        extracted_nodes = []
        
        # 優先ノードを最初に追加
        for priority_node in priority_nodes:
            if priority_node in query and priority_node not in extracted_nodes:
                extracted_nodes.append(priority_node)
        
        # その他のキーワードを追加
        for kw in filtered_keywords:
            if kw not in extracted_nodes:
                extracted_nodes.append(kw)
        
        return extracted_nodes[:5]  # 最大5つのノード
    
    def _extract_keywords(self, related_nodes: List[Dict[str, Any]]) -> List[str]:
        """関連ノードからキーワードを抽出"""
        keywords = set()
        
        for node in related_nodes:
            # ノードIDとラベルをキーワードとして追加
            keywords.add(node['id'])
            keywords.add(node['label'])
            
            # 関係の種類もキーワードとして追加
            if node['relationship_type'] and node['relationship_type'] != 'connected':
                keywords.add(node['relationship_type'])
        
        return list(keywords)[:20]  # 最大20個のキーワード
    
    def _generate_expanded_query(self, original_query: str, keywords: List[str]) -> str:
        """拡張クエリを生成"""
        if not keywords:
            return original_query
        
        # キーワードを追加して拡張クエリを生成
        expanded_keywords = ' '.join(keywords[:10])  # 最大10個のキーワード
        return f"{original_query} {expanded_keywords}"
    
    async def _vector_search(self, query: str) -> SearchResult:
        """ベクトル検索を実行（MongoDB検索）"""
        start_time = time.time()
        
        try:
            # CosmosServiceを使用して法令検索（ベクトル検索として）
            regulations = self.cosmos_service.search_regulations(query, limit=10)
            
            # DocumentChunkに変換
            documents = []
            for reg in regulations:
                # スコアを0-1の範囲に正規化
                normalized_score = min(reg["score"], 1.0) if reg["score"] > 1.0 else reg["score"]
                
                document = DocumentChunk(
                    id=f"vector_{reg['id']}",
                    content=reg["text"],
                    source=reg["prefLabel"],
                    metadata={
                        "prefLabel": reg["prefLabel"],
                        "section_label": reg["prefLabel"],
                        "chunk_id": reg["id"]
                    },
                    score=normalized_score,
                    search_type=SearchType.VECTOR,
                    node_id=None,
                    edge_info=None
                )
                documents.append(document)
            
            execution_time = (time.time() - start_time) * 1000
            
            return SearchResult(
                search_type=SearchType.VECTOR,
                documents=documents,
                total_count=len(documents),
                execution_time_ms=execution_time
            )
            
        except Exception as e:
            logger.error(f"ベクトル検索エラー: {e}")
            execution_time = (time.time() - start_time) * 1000
            
            return SearchResult(
                search_type=SearchType.VECTOR,
                documents=[],
                total_count=0,
                execution_time_ms=execution_time
            )
    
    async def _graph_search(self, query: str, max_related_nodes: int) -> SearchResult:
        """グラフ検索を実行（関連ノードをキーワードとしてMongoDB検索）"""
        start_time = time.time()
        
        try:
            # クエリからノードを抽出
            extracted_nodes = self._extract_nodes_from_query(query)
            logger.info(f"グラフ検索で抽出されたノード: {extracted_nodes}")
            
            # 関連ノードを取得
            all_related_keywords = []
            successful_nodes = 0
            
            for node in extracted_nodes:
                try:
                    logger.info(f"ノード '{node}' の関連ノードを取得中...")
                    
                    # 関連ノード情報を取得
                    nodes_info = await self.nodes_info_service.get_related_nodes_info(
                        node, max_related_nodes
                    )
                    
                    if nodes_info.success and nodes_info.related_nodes:
                        logger.info(f"ノード '{node}' から {len(nodes_info.related_nodes)} 件の関連ノードを取得")
                        successful_nodes += 1
                        
                        for related_node in nodes_info.related_nodes:
                            all_related_keywords.append(related_node.id)
                            
                except Exception as e:
                    logger.warning(f"ノード '{node}' のグラフ検索エラー: {e}")
                    continue
            
            # 関連ノードをキーワードとしてMongoDB検索
            documents = []
            if all_related_keywords:
                # 関連キーワードで法令検索
                graph_query = ' '.join(all_related_keywords[:10])  # 最大10個のキーワード
                logger.info(f"グラフ拡張クエリ: {graph_query}")
                regulations = self.cosmos_service.search_regulations(graph_query, limit=10)
                
                for reg in regulations:
                    # スコアを0-1の範囲に正規化
                    normalized_score = min(reg["score"], 1.0) if reg["score"] > 1.0 else reg["score"]
                    
                    document = DocumentChunk(
                        id=f"graph_{reg['id']}",
                        content=reg["text"],
                        source=reg["prefLabel"],
                        metadata={
                            "prefLabel": reg["prefLabel"],
                            "section_label": reg["prefLabel"],
                            "chunk_id": reg["id"],
                            "graph_keywords": all_related_keywords
                        },
                        score=normalized_score,
                        search_type=SearchType.GRAPH,
                        node_id=None,
                        edge_info=None
                    )
                    documents.append(document)
            
            logger.info(f"グラフ検索完了: {successful_nodes}/{len(extracted_nodes)} ノードから {len(documents)} 件の法令を取得")
            
            execution_time = (time.time() - start_time) * 1000
            
            return SearchResult(
                search_type=SearchType.GRAPH,
                documents=documents,
                total_count=len(documents),
                execution_time_ms=execution_time
            )
            
        except Exception as e:
            logger.error(f"グラフ検索エラー: {e}")
            execution_time = (time.time() - start_time) * 1000
            
            return SearchResult(
                search_type=SearchType.GRAPH,
                documents=[],
                total_count=0,
                execution_time_ms=execution_time
            )
    
    async def _keyword_search(self, query: str) -> SearchResult:
        """キーワード検索を実行（MongoDB検索）"""
        start_time = time.time()
        
        try:
            # CosmosServiceを使用して法令検索（キーワード検索として）
            regulations = self.cosmos_service.search_regulations(query, limit=10)
            
            # DocumentChunkに変換
            documents = []
            for reg in regulations:
                # スコアを0-1の範囲に正規化
                normalized_score = min(reg["score"], 1.0) if reg["score"] > 1.0 else reg["score"]
                
                document = DocumentChunk(
                    id=f"keyword_{reg['id']}",
                    content=reg["text"],
                    source=reg["prefLabel"],
                    metadata={
                        "prefLabel": reg["prefLabel"],
                        "section_label": reg["prefLabel"],
                        "chunk_id": reg["id"]
                    },
                    score=normalized_score,
                    search_type=SearchType.KEYWORD,
                    node_id=None,
                    edge_info=None
                )
                documents.append(document)
            
            execution_time = (time.time() - start_time) * 1000
            
            return SearchResult(
                search_type=SearchType.KEYWORD,
                documents=documents,
                total_count=len(documents),
                execution_time_ms=execution_time
            )
            
        except Exception as e:
            logger.error(f"キーワード検索エラー: {e}")
            execution_time = (time.time() - start_time) * 1000
            
            return SearchResult(
                search_type=SearchType.KEYWORD,
                documents=[],
                total_count=0,
                execution_time_ms=execution_time
            )
    
    def _generate_content_from_node(self, node) -> str:
        """ノードからコンテンツを生成"""
        content_parts = []
        
        # ノードの基本情報
        content_parts.append(f"ノード: {node.id}")
        content_parts.append(f"ラベル: {node.label}")
        
        # 関係の種類
        if node.relationship_type and node.relationship_type != 'connected':
            content_parts.append(f"関係: {node.relationship_type}")
        
        # エッジ情報（安全にアクセス）
        edge_id = getattr(node, 'edge_id', None)
        edge_label = getattr(node, 'edge_label', None)
        if edge_label:
            content_parts.append(f"エッジ: {edge_label}")
        
        return " | ".join(content_parts)
    
    def _calculate_graph_score(self, node) -> float:
        """グラフノードのスコアを計算"""
        base_score = 0.8  # ベーススコア
        
        # 距離による減点
        if node.distance > 1:
            base_score *= (1.0 / node.distance)
        
        # 関係の種類による調整
        if node.relationship_type in ['原料', '分類', '規定']:
            base_score *= 1.2
        elif node.relationship_type in ['関連', '含まれる']:
            base_score *= 1.1
        
        return min(base_score, 1.0)
    
    def _deduplicate_and_score(
        self, 
        documents: List[DocumentChunk], 
        vector_weight: float, 
        graph_weight: float, 
        keyword_weight: float
    ) -> List[DocumentChunk]:
        """重複除去とスコア計算"""
        # 重複除去（contentベース）
        seen_contents = set()
        unique_documents = []
        
        for doc in documents:
            content = getattr(doc, 'content', '') or getattr(doc, 'text', '')
            content_key = content[:100] if content else str(id(doc))  # 最初の100文字で重複判定
            if content_key not in seen_contents:
                seen_contents.add(content_key)
                unique_documents.append(doc)
        
        # スコア計算
        for doc in unique_documents:
            search_type = getattr(doc, 'search_type', None)
            current_score = getattr(doc, 'score', 0.5)
            
            if search_type == SearchType.VECTOR:
                doc.score = current_score * vector_weight
            elif search_type == SearchType.GRAPH:
                doc.score = current_score * graph_weight
            elif search_type == SearchType.KEYWORD:
                doc.score = current_score * keyword_weight
            else:
                doc.score = current_score
        
        # スコア順にソート
        unique_documents.sort(key=lambda x: getattr(x, 'score', 0.5), reverse=True)
        
        return unique_documents
    
    def _select_final_chunks(self, documents: List[DocumentChunk], max_chunks: int) -> List[DocumentChunk]:
        """最終チャンクを選択"""
        # 上位max_chunks件を選択
        selected = documents[:max_chunks]
        
        # 多様性を確保（同じソースからの重複を避ける）
        diverse_chunks = []
        seen_sources = set()
        
        for chunk in selected:
            source_key = f"{chunk.search_type}_{chunk.source}"
            if source_key not in seen_sources or len(diverse_chunks) < max_chunks // 2:
                diverse_chunks.append(chunk)
                seen_sources.add(source_key)
        
        return diverse_chunks[:max_chunks]
    
    async def get_health_status(self) -> Dict[str, Any]:
        """ヘルスステータスを取得"""
        try:
            status = {
                "hybrid_rag_initialized": self._initialized,
                "gremlin_connected": False,
                "vector_search_available": False,
                "keyword_search_available": False
            }
            
            if self._initialized:
                status["gremlin_connected"] = await self.gremlin_service.get_health_status()
                status["vector_search_available"] = True  # 仮実装
                status["keyword_search_available"] = True  # 仮実装
            
            return status
            
        except Exception as e:
            return {
                "hybrid_rag_initialized": False,
                "error": str(e)
            }
    
    async def _select_effective_documents(self, documents: List[DocumentChunk], query: str, max_documents: int = 10) -> List[DocumentChunk]:
        """10つの関連条文を効果的に選抜"""
        if not documents:
            return []
        
        # 1. 重複除去（同じ法令名の条文を統合）
        unique_documents = self._remove_duplicate_regulations(documents)
        
        # 2. 関連性スコアリング（質問に対する関連性を計算）
        scored_documents = self._calculate_relevance_scores(unique_documents, query)
        
        # 3. 多様性を確保した選択（異なる法令・条文から選択）
        diverse_documents = self._select_diverse_documents(scored_documents, max_documents)
        
        # 4. 最終的な10つの条文を選択
        final_documents = self._select_final_regulations(diverse_documents, max_documents)
        
        logger.info(f"効果的選抜完了: {len(documents)}件 -> {len(final_documents)}件")
        return final_documents
    
    def _remove_duplicate_regulations(self, documents: List[DocumentChunk]) -> List[DocumentChunk]:
        """重複する法令条文を除去"""
        seen_regulations = set()
        unique_documents = []
        
        for doc in documents:
            # 法令名で重複チェック
            regulation_key = self._extract_regulation_key(doc)
            if regulation_key not in seen_regulations:
                seen_regulations.add(regulation_key)
                unique_documents.append(doc)
        
        logger.info(f"重複除去: {len(documents)}件 -> {len(unique_documents)}件")
        return unique_documents
    
    def _extract_regulation_key(self, doc: DocumentChunk) -> str:
        """法令条文のキーを抽出"""
        # メタデータから法令名を取得
        if hasattr(doc, 'metadata') and doc.metadata:
            metadata = doc.metadata
            pref_label = metadata.get('prefLabel', '') if isinstance(metadata, dict) else getattr(metadata, 'prefLabel', '')
            section_label = metadata.get('section_label', '') if isinstance(metadata, dict) else getattr(metadata, 'section_label', '')
        else:
            pref_label = ''
            section_label = ''
        
        # 法令名と条文番号でキーを作成
        if pref_label and section_label:
            return f"{pref_label}_{section_label}"
        elif pref_label:
            return pref_label
        else:
            return getattr(doc, 'id', str(id(doc)))
    
    def _calculate_relevance_scores(self, documents: List[DocumentChunk], query: str) -> List[DocumentChunk]:
        """質問に対する関連性スコアを計算"""
        query_keywords = self._extract_keywords(query)
        
        for doc in documents:
            # 既存のスコアに加えて関連性スコアを計算
            relevance_score = self._calculate_document_relevance(doc, query_keywords)
            current_score = getattr(doc, 'score', 0.5)  # デフォルトスコア
            doc.score = current_score * 0.7 + relevance_score * 0.3  # 重み付け
            
        return documents
    
    def _calculate_document_relevance(self, doc: DocumentChunk, query_keywords: List[str]) -> float:
        """文書の関連性スコアを計算"""
        # コンテンツの取得
        content = getattr(doc, 'content', '') or getattr(doc, 'text', '')
        text = content.lower() if content else ''
        
        # メタデータの取得
        if hasattr(doc, 'metadata') and doc.metadata:
            metadata = doc.metadata
            if isinstance(metadata, dict):
                pref_label = metadata.get('prefLabel', '')
                section_label = metadata.get('section_label', '')
            else:
                pref_label = getattr(metadata, 'prefLabel', '')
                section_label = getattr(metadata, 'section_label', '')
        else:
            pref_label = ''
            section_label = ''
        
        # キーワードマッチング
        keyword_matches = sum(1 for keyword in query_keywords if keyword.lower() in text)
        keyword_score = keyword_matches / len(query_keywords) if query_keywords else 0
        
        # 法令名の関連性
        pref_label_lower = pref_label.lower()
        regulation_score = 0.5 if any(keyword.lower() in pref_label_lower for keyword in query_keywords) else 0
        
        # 条文の重要度（条文番号が小さいほど重要）
        section_score = self._calculate_section_importance(section_label)
        
        return (keyword_score * 0.5 + regulation_score * 0.3 + section_score * 0.2)
    
    def _calculate_section_importance(self, section_label: str) -> float:
        """条文の重要度を計算"""
        if not section_label:
            return 0.5
        
        # 条文番号を抽出
        import re
        numbers = re.findall(r'\d+', section_label)
        if numbers:
            first_number = int(numbers[0])
            # 条文番号が小さいほど重要（1-10: 1.0, 11-50: 0.8, 51-100: 0.6, 100+: 0.4）
            if first_number <= 10:
                return 1.0
            elif first_number <= 50:
                return 0.8
            elif first_number <= 100:
                return 0.6
            else:
                return 0.4
        
        return 0.5
    
    def _select_diverse_documents(self, documents: List[DocumentChunk], max_documents: int) -> List[DocumentChunk]:
        """多様性を確保した文書選択"""
        if len(documents) <= max_documents:
            return documents
        
        # スコアでソート
        sorted_docs = sorted(documents, key=lambda x: getattr(x, 'score', 0.5), reverse=True)
        
        selected = []
        used_regulations = set()
        
        # 高スコアから順に選択し、異なる法令から選ぶ
        for doc in sorted_docs:
            if len(selected) >= max_documents:
                break
                
            regulation_key = self._extract_regulation_key(doc)
            if regulation_key not in used_regulations:
                selected.append(doc)
                used_regulations.add(regulation_key)
        
        # まだ足りない場合は残りから選択
        if len(selected) < max_documents:
            remaining = [doc for doc in sorted_docs if doc not in selected]
            selected.extend(remaining[:max_documents - len(selected)])
        
        return selected
    
    def _select_final_regulations(self, documents: List[DocumentChunk], max_documents: int) -> List[DocumentChunk]:
        """最終的な10つの条文を選択"""
        if len(documents) <= max_documents:
            return documents
        
        # 最終的なスコアでソート
        final_docs = sorted(documents, key=lambda x: getattr(x, 'score', 0.5), reverse=True)
        
        return final_docs[:max_documents]
