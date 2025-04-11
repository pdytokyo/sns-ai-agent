from fastapi import FastAPI
from app.main_final import app, init_db
from app.routes import setup_routes

init_db()
setup_routes(app)
