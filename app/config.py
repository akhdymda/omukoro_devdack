from pydantic_settings import BaseSettings
import os

class Settings(BaseSettings):
    # OpenAI API設定
    openai_api_key: str = os.getenv("OPENAI_API_KEY", "")
    
    # アプリケーション設定
    secret_key: str = os.getenv("SECRET_KEY", "your-secret-key")
    algorithm: str = os.getenv("ALGORITHM", "HS256")
    access_token_expire_minutes: int = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "30"))
    
    # Redis設定
    redis_host: str = os.getenv("REDIS_HOST", "localhost")
    redis_port: int = int(os.getenv("REDIS_PORT", "6379"))
    redis_db: int = int(os.getenv("REDIS_DB", "0"))
    
    # CORS設定
    frontend_url: str = os.getenv("FRONTEND_URL", "http://localhost:3000")
    
    # 環境設定
    environment: str = os.getenv("ENVIRONMENT", "development")
    
    class Config:
        case_sensitive = False

settings = Settings() 