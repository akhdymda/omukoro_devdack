from pydantic_settings import BaseSettings
from typing import Optional
from functools import lru_cache
import logging

logger = logging.getLogger(__name__)

class Settings(BaseSettings):
    """アプリケーション設定管理クラス"""
    
    # アプリケーション基本設定
    app_name: str = "Omukoro Risk Analysis API"
    app_version: str = "1.0.0"
    debug: bool = False
    environment: str = "development"
    
    # サーバー設定
    host: str = "0.0.0.0"
    port: int = 8000
    
    # セキュリティ設定
    secret_key: str = "your-secret-key-change-in-production"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    
    # MySQL設定
    database_host: Optional[str] = None
    database_port: int = 3306
    database_user: Optional[str] = None
    database_password: Optional[str] = None
    database_name: Optional[str] = None
    database_ssl: bool = True
    database_charset: str = "utf8mb4"
    database_autocommit: bool = True
    
    # 後方互換性のためのプロパティ
    @property
    def mysql_host(self) -> Optional[str]:
        return self.database_host
    
    @property
    def mysql_port(self) -> int:
        return self.database_port
    
    @property
    def mysql_user(self) -> Optional[str]:
        return self.database_user
    
    @property
    def mysql_password(self) -> Optional[str]:
        return self.database_password
    
    @property
    def mysql_database(self) -> Optional[str]:
        return self.database_name
    
    @property
    def mysql_ssl_disabled(self) -> bool:
        return not self.database_ssl
    
    @property
    def mysql_charset(self) -> str:
        return self.database_charset
    
    @property
    def mysql_autocommit(self) -> bool:
        return self.database_autocommit
    
    # Redis設定
    redis_host: str = "localhost"
    redis_port: int = 6379
    redis_db: int = 0
    redis_password: Optional[str] = None
    redis_decode_responses: bool = True
    
    # OpenAI設定
    openai_api_key: Optional[str] = None
    openai_timeout: int = 30
    openai_max_retries: int = 3
    
    # Cosmos DB設定（オプショナル）
    mongodb_connection_string: Optional[str] = None
    mongo_db: str = "vector_legal_rag"
    mongo_collection: str = "alctax_act_chunks"
    mongo_timeout: int = 10
    
    # ログ設定
    log_level: str = "INFO"
    log_format: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    
    # タイムゾーン設定
    timezone: str = "Asia/Tokyo"
    
    # CORS設定
    cors_origins: list[str] = [
        "https://aps-omu-01.azurewebsites.net",  # 本番環境のフロントエンド
        "http://localhost:3000",  # 開発環境用
        "http://localhost:3001"   # 開発環境用
    ]
    cors_allow_credentials: bool = True
    cors_allow_methods: list[str] = ["GET", "POST", "PUT", "DELETE", "OPTIONS"]
    cors_allow_headers: list[str] = ["*"]
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False
        extra = "ignore"
        
        @classmethod
        def parse_env_var(cls, field_name: str, raw_val: str):
            if field_name == "cors_origins":
                # 環境変数が文字列の場合、カンマ区切りで分割
                if raw_val.startswith('[') and raw_val.endswith(']'):
                    # JSON配列形式の場合
                    import json
                    try:
                        return json.loads(raw_val)
                    except json.JSONDecodeError:
                        pass
                # カンマ区切りの文字列の場合
                return [origin.strip() for origin in raw_val.split(',')]
            return raw_val
    
    def get_mysql_config(self) -> dict:
        """MySQL接続設定を取得"""
        if not all([self.mysql_host, self.mysql_user, self.mysql_password, self.mysql_database]):
            logger.warning("MySQL接続情報が不完全です")
            return {}
            
        return {
            'host': self.mysql_host,
            'port': self.mysql_port,
            'user': self.mysql_user,
            'password': self.mysql_password,
            'database': self.mysql_database,
            'charset': self.mysql_charset,
            'autocommit': self.mysql_autocommit,
            'ssl': {'ssl_disabled': self.mysql_ssl_disabled},
            'ssl_verify_cert': False,
            'ssl_verify_identity': False
        }
    
    def get_redis_config(self) -> dict:
        """Redis接続設定を取得"""
        config = {
            'host': self.redis_host,
            'port': self.redis_port,
            'db': self.redis_db,
            'decode_responses': self.redis_decode_responses
        }
        if self.redis_password:
            config['password'] = self.redis_password
        return config
    
    def is_mysql_configured(self) -> bool:
        """MySQL設定が完全かチェック"""
        return all([self.mysql_host, self.mysql_user, self.mysql_password, self.mysql_database])
    
    def is_redis_configured(self) -> bool:
        """Redis設定が完全かチェック"""
        return bool(self.redis_host)
    
    def is_openai_configured(self) -> bool:
        """OpenAI設定が完全かチェック"""
        return bool(self.openai_api_key and self.openai_api_key != "test_key_for_integration_testing")

@lru_cache()
def get_settings() -> Settings:
    """設定インスタンスを取得（キャッシュ付き）"""
    settings = Settings()
    
    # CORS設定のデバッグログ
    logger.info(f"CORS設定 - origins: {settings.cors_origins}")
    logger.info(f"CORS設定 - allow_credentials: {settings.cors_allow_credentials}")
    logger.info(f"CORS設定 - allow_methods: {settings.cors_allow_methods}")
    logger.info(f"CORS設定 - allow_headers: {settings.cors_allow_headers}")
    
    return settings

# グローバル設定インスタンス
settings = get_settings()
