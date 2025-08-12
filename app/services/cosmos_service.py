from pymongo import MongoClient
from rank_bm25 import BM25Okapi
import numpy as np
import re
import nltk
from typing import List, Dict, Any, Optional
from app.config import settings
import logging

logger = logging.getLogger(__name__)

class CosmosService:
    """Cosmos DB接続とベクトル検索機能を提供するサービス"""
    
    def __init__(self):
        self.client = None
        self.db = None
        self.collection = None
        self.bm25 = None
        self.id_to_idx = {}
        self.idx_to_id = {}
        self.all_texts = []
        self.all_ids = []
        
        # NLTK tokenizer 用リソース（初回のみ DL）
        try:
            nltk.download("punkt", quiet=True)
        except Exception as e:
            logger.warning(f"NLTK download failed: {e}")
        
        self._initialize_connection()
    
    def _initialize_connection(self):
        """Cosmos DB接続を初期化"""
        try:
            if not settings.mongodb_connection_string:
                logger.warning("MONGODB_CONNECTION_STRING環境変数が設定されていません。ダミーモードで動作します。")
                self._initialize_empty_bm25()
                return
            
            self.client = MongoClient(settings.mongodb_connection_string)
            self.db = self.client[settings.mongo_db]
            self.collection = self.db[settings.mongo_collection]
            
            # BM25インデックスを初期化
            self._initialize_bm25_index()
            
            logger.info(f"Cosmos DB接続完了: {settings.mongo_db}.{settings.mongo_collection}")
            
        except Exception as e:
            logger.error(f"Cosmos DB接続エラー: {e}")
            self._initialize_empty_bm25()
    
    def _initialize_bm25_index(self):
        """BM25インデックスを初期化"""
        try:
            # 全チャンクを取得して BM25 corpus 生成
            all_docs = list(self.collection.find({}, {"text": 1, "id": 1}))
            self.all_texts = [doc["text"] for doc in all_docs]
            self.all_ids = [doc["id"] for doc in all_docs]
            
            logger.info(f"MongoDB documents: {len(self.all_texts)}")
            
            if len(self.all_texts) > 0:
                tokenized_corpus = [self._tokenize(t) for t in self.all_texts]
                self.bm25 = BM25Okapi(tokenized_corpus)
                
                # id ↔ index 対応表
                self.id_to_idx = {doc_id: i for i, doc_id in enumerate(self.all_ids)}
                self.idx_to_id = {i: doc_id for i, doc_id in enumerate(self.all_ids)}
            else:
                logger.warning("データベースにドキュメントが存在しません")
                self._initialize_empty_bm25()
                
        except Exception as e:
            logger.error(f"BM25インデックス初期化エラー: {e}")
            self._initialize_empty_bm25()
    
    def _initialize_empty_bm25(self):
        """空の状態でBM25を初期化"""
        tokenized_corpus = [["ダミー", "テキスト"]]
        self.bm25 = BM25Okapi(tokenized_corpus)
        self.id_to_idx = {}
        self.idx_to_id = {}
    
    def _tokenize(self, text: str) -> List[str]:
        """
        極簡易トークナイザ:
        - 英数字は空白区切り
        - 日本語は 1 文字ずつ (BM25 は文字 N-gram でもそこそこ効く)
        """
        text = re.sub(r"\s+", " ", text.strip())
        tokens = []
        buf = ""
        for ch in text:
            if "\u3040" <= ch <= "\u30ff" or "\u4e00" <= ch <= "\u9fff":
                # 日本語なら 1 文字単位で push
                if buf:
                    tokens.append(buf)
                    buf = ""
                tokens.append(ch)
            else:
                # 英数字はまとめて
                if ch.isspace():
                    if buf:
                        tokens.append(buf)
                        buf = ""
                else:
                    buf += ch
        if buf:
            tokens.append(buf)
        return tokens
    
    def search_regulations(self, query: str, limit: int = 5) -> List[Dict[str, Any]]:
        """法令検索を実行"""
        try:
            if not self.bm25:
                logger.error("BM25インデックスが初期化されていません")
                return []
            
            # BM25検索
            query_tokens = self._tokenize(query)
            sparse_scores = self.bm25.get_scores(query_tokens)
            sparse_idxs = np.argsort(sparse_scores)[::-1][:limit]
            
            results = []
            for idx in sparse_idxs:
                if idx in self.idx_to_id:
                    chunk_id = self.idx_to_id[idx]
                    doc = self.collection.find_one({"id": chunk_id})
                    if doc:
                        # prefLabelを取得
                        pref_label = None
                        if "metadata" in doc and "prefLabel" in doc["metadata"]:
                            pref_label = doc["metadata"]["prefLabel"]
                        if not pref_label:
                            pref_label = f"法令チャンク {chunk_id}"
                        
                        # 法令テキストの最初の200文字を取得
                        regulation_text = doc["text"][:200] + "..." if len(doc["text"]) > 200 else doc["text"]
                        
                        results.append({
                            "id": chunk_id,
                            "text": regulation_text,
                            "prefLabel": pref_label,
                            "score": float(sparse_scores[idx])
                        })
            
            return results
            
        except Exception as e:
            logger.error(f"法令検索エラー: {e}")
            return []
    
    def get_regulation_by_id(self, regulation_id: str) -> Optional[Dict[str, Any]]:
        """IDで法令を取得"""
        try:
            doc = self.collection.find_one({"id": regulation_id})
            if doc:
                return {
                    "id": doc["id"],
                    "text": doc["text"],
                    "prefLabel": doc.get("metadata", {}).get("prefLabel", f"法令チャンク {regulation_id}")
                }
            return None
        except Exception as e:
            logger.error(f"法令取得エラー: {e}")
            return None
    
    def get_health_status(self) -> Dict[str, Any]:
        """ヘルスチェック用の状態を取得"""
        return {
            "mongodb_connected": self.client is not None,
            "documents_count": len(self.all_texts),
            "collection_name": self.collection.name if self.collection is not None else None,
            "bm25_initialized": self.bm25 is not None
        }
