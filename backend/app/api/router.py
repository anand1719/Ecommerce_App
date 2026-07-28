from fastapi import APIRouter

from app.api.routes import auth, health, kafka, products, sales, ws


api_router = APIRouter()
api_router.include_router(health.router)
api_router.include_router(auth.router)
api_router.include_router(kafka.router)
api_router.include_router(products.router)
api_router.include_router(sales.router)
api_router.include_router(ws.router)
