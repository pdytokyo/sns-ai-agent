from fastapi import APIRouter

def setup_routes(app):
    router = APIRouter()

    @router.get("/")
    async def root():
        return {"message": "Hello, World!"}

    app.include_router(router)
