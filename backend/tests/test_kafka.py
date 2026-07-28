import asyncio
from types import SimpleNamespace

from fastapi.testclient import TestClient

from app.main import app
from app.services.kafka import KafkaProducerService


class FakeProducer:
    def __init__(self) -> None:
        self.messages = []

    async def send_and_wait(self, topic, value, key=None):
        self.messages.append({"topic": topic, "value": value, "key": key})


def test_kafka_status_endpoint_reports_disabled_by_default():
    with TestClient(app) as client:
        response = client.get("/api/v1/kafka/status")

    assert response.status_code == 200
    assert response.json()["enabled"] is False
    assert response.json()["started"] is False
    assert response.json()["topics"]["products"] == "ecommerce.products"


def test_kafka_publish_builds_standard_event_envelope():
    settings = SimpleNamespace(
        kafka_enabled=True,
        kafka_bootstrap_servers="localhost:9092",
        kafka_client_id="test-ecommerce-api",
        kafka_fail_fast=False,
    )
    service = KafkaProducerService(settings=settings)
    fake_producer = FakeProducer()
    service._producer = fake_producer
    service._started = True

    published = asyncio.run(
        service.publish(
            topic="ecommerce.products",
            event_type="product.created",
            payload={"id": "product-1"},
            key="product-1",
        )
    )

    assert published is True
    assert fake_producer.messages[0]["topic"] == "ecommerce.products"
    assert fake_producer.messages[0]["key"] == "product-1"
    assert fake_producer.messages[0]["value"]["event_type"] == "product.created"
    assert fake_producer.messages[0]["value"]["payload"] == {"id": "product-1"}

