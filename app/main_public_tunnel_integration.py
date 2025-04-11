from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
import os
import uvicorn
from dotenv import load_dotenv

from main_public_tunnel import app, init_db
from main_enhanced_routes import setup_routes

load_dotenv()

init_db()

os.makedirs("app/uploads", exist_ok=True)

if __name__ == "__main__":
    uvicorn.run("main_public_tunnel_integration:app", host="0.0.0.0", port=8000, reload=True)
