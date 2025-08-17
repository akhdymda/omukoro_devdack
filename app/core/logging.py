"""
ログ設定管理
"""
import logging
import sys
from typing import Optional
from app.config import settings

def setup_logging(log_level: Optional[str] = None) -> None:
    """ログ設定をセットアップ"""
    level = log_level or settings.log_level
    
    # ログレベルの設定
    log_level_mapping = {
        "DEBUG": logging.DEBUG,
        "INFO": logging.INFO,
        "WARNING": logging.WARNING,
        "ERROR": logging.ERROR,
        "CRITICAL": logging.CRITICAL
    }
    
    numeric_level = log_level_mapping.get(level.upper(), logging.INFO)
    
    # ログフォーマットの設定
    formatter = logging.Formatter(
        settings.log_format,
        datefmt="%Y-%m-%d %H:%M:%S"
    )
    
    # ルートロガーの設定
    root_logger = logging.getLogger()
    root_logger.setLevel(numeric_level)
    
    # コンソールハンドラーの設定
    if not root_logger.handlers:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(numeric_level)
        console_handler.setFormatter(formatter)
        root_logger.addHandler(console_handler)
    
    # 外部ライブラリのログレベルを調整
    logging.getLogger("uvicorn").setLevel(logging.WARNING)
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("fastapi").setLevel(logging.WARNING)
    
    # デバッグモードでない場合はライブラリのログを抑制
    if not settings.debug:
        logging.getLogger("pymongo").setLevel(logging.WARNING)
        logging.getLogger("redis").setLevel(logging.WARNING)
        logging.getLogger("urllib3").setLevel(logging.WARNING)

def get_logger(name: str) -> logging.Logger:
    """ロガーを取得"""
    return logging.getLogger(name)