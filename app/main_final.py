from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from dotenv import load_dotenv
import os

load_dotenv()

app = FastAPI()

# 静的ファイルの設定 (修正版)
app.mount("/static", StaticFiles(directory="app/static"), name="static")

def init_db():
    # データベース初期化処理
    pass

@app.get("/health")
async def health_check():
    return {"status": "ok"}
