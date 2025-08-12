import json
import hashlib
from typing import Optional
from app.config import settings
import logging

logger = logging.getLogger(__name__)

class CacheService:
    """Redisを使用したキャッシュサービス"""
    
    def __init__(self):
        self.redis_client = None
        self._initialize_redis()
    
    def _initialize_redis(self):
        """Redis接続を初期化"""
        try:
            import redis
            self.redis_client = redis.from_url(settings.redis_url)
            # 接続テスト
            self.redis_client.ping()
            logger.info("Redis接続完了")
        except Exception as e:
            logger.warning(f"Redis接続失敗: {e}")
            self.redis_client = None
    
    async def get_analysis_result(self, text: str) -> Optional[dict]:
        """分析結果をキャッシュから取得"""
        if not self.redis_client:
            return None
        
        try:
            cache_key = self._generate_cache_key(text)
            cached_data = self.redis_client.get(cache_key)
            
            if cached_data:
                return json.loads(cached_data)
            
            return None
            
        except Exception as e:
            logger.error(f"キャッシュ取得エラー: {e}")
            return None
    
    async def set_analysis_result(self, text: str, result: dict, ttl: int = 3600):
        """分析結果をキャッシュに保存"""
        if not self.redis_client:
            return
        
        try:
            cache_key = self._generate_cache_key(text)
            self.redis_client.setex(
                cache_key,
                ttl,
                json.dumps(result, ensure_ascii=False)
            )
            logger.debug(f"キャッシュ保存完了: {cache_key}")
            
        except Exception as e:
            logger.error(f"キャッシュ保存エラー: {e}")
    
    def _generate_cache_key(self, text: str) -> str:
        """キャッシュキーを生成"""
        hash_object = hashlib.md5(text.encode())
        return f"analysis_{hash_object.hexdigest()}"
    
    def get_health_status(self) -> dict:
        """ヘルスチェック用の状態を取得"""
        try:
            if self.redis_client:
                self.redis_client.ping()
                return {"redis_connected": True}
            else:
                return {"redis_connected": False}
        except Exception:
            return {"redis_connected": False}
