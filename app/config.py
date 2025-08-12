from pydantic_settings import BaseSettings
from typing import Optional

class Settings(BaseSettings):
    # OpenAI設定
    openai_api_key: Optional[str] = None
    
    # Cosmos DB設定
    mongodb_connection_string: Optional[str] = None
    mongo_db: str = "vector_legal_rag"
    mongo_collection: str = "alctax_act_chunks"
    
    # Redis設定
    redis_url: str = "redis://localhost:6379"
    
    # アプリケーション設定
    app_name: str = "Sherpath API"
    app_version: str = "1.0.0"
    debug: bool = False
    
    # 追加設定項目（.envファイルに存在する場合）
    chroma_db_path: Optional[str] = None
    chroma_dir: Optional[str] = None
    chroma_collection: Optional[str] = None
    out_jsonl: Optional[str] = None
    mongo_coll: Optional[str] = None
    created_at: Optional[str] = None
    
    class Config:
        env_file = ".env"
        extra = "ignore"  # 追加の環境変数を無視

settings = Settings()
