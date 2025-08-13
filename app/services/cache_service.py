import pickle
from typing import Optional, Any
from app.config import settings
from redis.asyncio import Redis as AsyncRedis
import os
class CacheService:
    """
    Redis を使用したキャッシュサービス
    """
    
    def __init__(self):
        self._redis = None
    
    async def _get_redis(self):
        """
        Redis接続を取得（遅延初期化）
        """
        if self._redis is None:
            try:
                # 優先: REDIS_URL（例: rediss://:<password>@<host>:6380/0）
                redis_url = os.getenv("REDIS_URL", "")
                if redis_url:
                    self._redis = AsyncRedis.from_url(redis_url, decode_responses=False)
                else:
                    host = settings.redis_host
                    port = settings.redis_port
                    db = int(os.getenv("REDIS_DB", settings.redis_db))
                    password = os.getenv("REDIS_PASSWORD", "")
                    use_ssl = str(os.getenv("REDIS_SSL", "False")).lower() == "true"
                    self._redis = AsyncRedis(
                        host=host,
                        port=port,
                        db=db,
                        password=password or None,
                        ssl=use_ssl,
                        decode_responses=False,
                    )
                # 接続テスト
                await self._redis.ping()
            except Exception as e:
                print(f"Redis connection failed: {e}")
                # Redis接続に失敗した場合はメモリキャッシュにフォールバック
                self._redis = MemoryCache()
        
        return self._redis
    
    async def get(self, key: str) -> Optional[Any]:
        """
        キーに対応する値を取得
        
        Args:
            key: キー
            
        Returns:
            Any: 値（存在しない場合はNone）
        """
        try:
            redis_client = await self._get_redis()
            data = await redis_client.get(key)
            
            if data is None:
                return None
            
            # pickleでデシリアライゼーション
            return pickle.loads(data)
            
        except Exception as e:
            print(f"Cache get error: {e}")
            return None
    
    async def set(self, key: str, value: Any, expire_seconds: int = 3600) -> bool:
        """
        キーと値をキャッシュに保存
        
        Args:
            key: キー
            value: 値
            expire_seconds: 有効期限（秒）
            
        Returns:
            bool: 保存成功時True
        """
        try:
            redis_client = await self._get_redis()
            
            # pickleでシリアライゼーション
            data = pickle.dumps(value)
            
            await redis_client.setex(key, expire_seconds, data)
            return True
            
        except Exception as e:
            print(f"Cache set error: {e}")
            return False
    
    async def delete(self, key: str) -> bool:
        """
        キーを削除
        
        Args:
            key: キー
            
        Returns:
            bool: 削除成功時True
        """
        try:
            redis_client = await self._get_redis()
            result = await redis_client.delete(key)
            return result > 0
            
        except Exception as e:
            print(f"Cache delete error: {e}")
            return False

class MemoryCache:
    """
    Redisが利用できない場合のメモリキャッシュ
    """
    
    def __init__(self):
        self._cache = {}
    
    async def get(self, key: str) -> Optional[Any]:
        return self._cache.get(key)
    
    async def setex(self, key: str, seconds: int, value: Any) -> None:
        self._cache[key] = value
        # 簡易実装のため有効期限は実装しない
    
    async def delete(self, key: str) -> int:
        if key in self._cache:
            del self._cache[key]
            return 1
        return 0
    
    async def ping(self) -> bool:
        return True 