from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.router import api_router
from app.core.config import get_settings
from app.db.base import Base
from app.db.session import engine
from app.models import product as product_models  # noqa: F401
from app.models import sale as sale_models  # noqa: F401
from app.models import user as user_models  # noqa: F401
from app.services.kafka import kafka_consumer_service, kafka_service


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    await kafka_service.start()
    await kafka_consumer_service.start()
    try:
        yield
    finally:
        await kafka_consumer_service.stop()
        await kafka_service.stop()


settings = get_settings()

app = FastAPI(
    title=settings.app_name,
    version="1.0.0",
    lifespan=lifespan,
)

app.include_router(api_router, prefix=settings.api_v1_prefix)
