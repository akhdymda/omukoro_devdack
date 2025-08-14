from pydantic_settings import BaseSettings
from typing import Optional
import os

class Settings(BaseSettings):
    # OpenAI設定
    openai_api_key: Optional[str] = None
    
    # Cosmos DB設定
    mongodb_connection_string: Optional[str] = None
    mongo_db: str = "vector_legal_rag"
    mongo_collection: str = "alctax_act_chunks"

    # アプリケーション設定
    secret_key: str = os.getenv("SECRET_KEY", "your-secret-key")
    algorithm: str = os.getenv("ALGORITHM", "HS256")
    access_token_expire_minutes: int = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "30"))
    
    # Redis設定
    redis_host: str = os.getenv("REDIS_HOST", "localhost")
    redis_port: int = int(os.getenv("REDIS_PORT", "6379"))
    redis_db: int = int(os.getenv("REDIS_DB", "0"))
    
    # MySQL設定
    mysql_host: Optional[str] = None
    mysql_port: int = 3306
    mysql_user: Optional[str] = None
    mysql_password: Optional[str] = None
    mysql_database: Optional[str] = None
    
    # アプリケーション設定
    app_name: str = "Sherpath API"
    app_version: str = "1.0.0"
    debug: bool = False
    
    
    class Config:
        env_file = ".env"
        extra = "ignore"  # 追加の環境変数を無視

settings = Settings()
