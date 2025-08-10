from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
import os

from app.api.analysis import router as analysis_router
from app.api.health import router as health_router

# 環境変数を読み込み
load_dotenv()

app = FastAPI(
    title="Sherpath API",
    description="企画案の論点整理と相談先提案API",
    version="1.0.0",
)

# CORS設定
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ルーターを追加
app.include_router(analysis_router, prefix="/api", tags=["analysis"])
app.include_router(health_router, prefix="/api", tags=["health"])

@app.get("/")
async def root():
    return {"message": "Sherpath API is running"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000) 