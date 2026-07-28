import asyncio
import json
import logging
from datetime import date, datetime, timezone
from decimal import Decimal
from typing import Any
from uuid import uuid4

from aiokafka import AIOKafkaConsumer, AIOKafkaProducer

from app.core.config import Settings, get_settings
from app.services.event_bus import event_bus


logger = logging.getLogger(__name__)


class KafkaProducerService:
    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()
        self._producer = None
        self._started = False

    @property
    def is_enabled(self) -> bool:
        return self.settings.kafka_enabled

    @property
    def is_started(self) -> bool:
        return self._started

    async def start(self) -> None:
        if not self.settings.kafka_enabled:
            return

        try:
            from aiokafka import AIOKafkaProducer
        except ImportError as exc:
            message = "Kafka is enabled but aiokafka is not installed."
            if self.settings.kafka_fail_fast:
                raise RuntimeError(message) from exc
            logger.warning(message)
            return

        self._producer = AIOKafkaProducer(
            bootstrap_servers=self.settings.kafka_bootstrap_servers,
            client_id=self.settings.kafka_client_id,
            value_serializer=lambda value: json.dumps(value, default=_json_default).encode("utf-8"),
            key_serializer=lambda value: value.encode("utf-8") if value else None,
        )

        try:
            await self._producer.start()
        except Exception:
            self._producer = None
            if self.settings.kafka_fail_fast:
                raise
            logger.exception("Kafka producer could not connect; events will not be published.")
            return

        self._started = True
        logger.info("Kafka producer started.")

    async def stop(self) -> None:
        if self._producer is not None:
            await self._producer.stop()
        self._producer = None
        self._started = False

    async def publish(self, topic: str, event_type: str, payload: dict, key: str | None = None) -> bool:
        if not self._started or self._producer is None:
            return False

        event = {
            "event_id": str(uuid4()),
            "event_type": event_type,
            "source": self.settings.kafka_client_id,
            "occurred_at": datetime.now(timezone.utc),
            "payload": payload,
        }

        try:
            await self._producer.send_and_wait(topic, value=event, key=key)
        except Exception:
            logger.exception("Kafka event publish failed: %s", event_type)
            return False

        return True


class KafkaConsumerService:
    """Consumes messages from Kafka topics and publishes them to the event bus."""

    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()
        self._consumer = None
        self._task: asyncio.Task[Any] | None = None
        self._started = False

    @property
    def is_started(self) -> bool:
        return self._started

    async def start(self) -> None:
        if not self.settings.kafka_enabled:
            logger.info("Kafka is disabled; consumer will not start.")
            return

        try:
            from aiokafka import AIOKafkaConsumer
        except ImportError as exc:
            logger.warning("Kafka consumer: aiokafka is not installed.")
            if self.settings.kafka_fail_fast:
                raise RuntimeError("Kafka is enabled but aiokafka is not installed.") from exc
            return

        topics = [
            self.settings.kafka_products_topic,
            self.settings.kafka_sales_topic,
        ]

        self._consumer = AIOKafkaConsumer(
            *topics,
            bootstrap_servers=self.settings.kafka_bootstrap_servers,
            client_id=f"{self.settings.kafka_client_id}-consumer",
            group_id=f"{self.settings.kafka_client_id}-group",
            value_deserializer=lambda v: json.loads(v.decode("utf-8")) if v else None,
            key_deserializer=lambda v: v.decode("utf-8") if v else None,
            auto_offset_reset="latest",
        )

        try:
            await self._consumer.start()
        except Exception:
            self._consumer = None
            if self.settings.kafka_fail_fast:
                raise
            logger.exception("Kafka consumer could not connect.")
            return

        self._started = True
        self._task = asyncio.create_task(self._consume_loop())
        logger.info("Kafka consumer started. Subscribed to: %s", topics)

    async def stop(self) -> None:
        self._started = False
        if self._task is not None:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            self._task = None
        if self._consumer is not None:
            await self._consumer.stop()
            self._consumer = None
        logger.info("Kafka consumer stopped.")

    async def _consume_loop(self) -> None:
        if self._consumer is None:
            return

        try:
            async for msg in self._consumer:
                if not self._started:
                    break

                event: dict[str, Any] = {
                    "topic": msg.topic,
                    "partition": msg.partition,
                    "offset": msg.offset,
                    "key": msg.key,
                    "value": msg.value,
                    "timestamp": msg.timestamp,
                }
                await event_bus.publish(event)
        except asyncio.CancelledError:
            logger.info("Kafka consumer loop cancelled.")
        except Exception:
            logger.exception("Error in Kafka consumer loop.")


def _json_default(value):
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, datetime | date):
        return value.isoformat()
    return str(value)


kafka_service = KafkaProducerService()
kafka_consumer_service = KafkaConsumerService()