from fastapi import APIRouter

from app.core.config import get_settings
from app.services.kafka import kafka_service


router = APIRouter(prefix="/kafka", tags=["Kafka"])


@router.get("/status")
def kafka_status() -> dict:
    settings = get_settings()
    return {
        "enabled": settings.kafka_enabled,
        "started": kafka_service.is_started,
        "bootstrap_servers": settings.kafka_bootstrap_servers,
        "topics": {
            "products": settings.kafka_products_topic,
            "sales": settings.kafka_sales_topic,
        },
    }

