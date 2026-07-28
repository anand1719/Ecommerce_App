from app.core.config import get_settings
from app.models.product import Product
from app.models.sale import Sale
from app.services.kafka import KafkaProducerService, kafka_service


def product_payload(product: Product) -> dict:
    return {
        "id": product.id,
        "sku": product.sku,
        "name": product.name,
        "description": product.description,
        "price": product.price,
        "stock_quantity": product.stock_quantity,
        "is_active": product.is_active,
        "created_at": product.created_at,
        "updated_at": product.updated_at,
    }


def sale_payload(sale: Sale) -> dict:
    return {
        "id": sale.id,
        "customer_id": sale.customer_id,
        "status": sale.status.value,
        "subtotal": sale.subtotal,
        "tax_amount": sale.tax_amount,
        "discount_amount": sale.discount_amount,
        "total_amount": sale.total_amount,
        "items": [
            {
                "id": item.id,
                "product_id": item.product_id,
                "quantity": item.quantity,
                "unit_price": item.unit_price,
                "line_total": item.line_total,
            }
            for item in sale.items
        ],
        "created_at": sale.created_at,
        "updated_at": sale.updated_at,
    }


async def publish_product_event(
    event_type: str,
    product: Product,
    producer: KafkaProducerService = kafka_service,
) -> bool:
    settings = get_settings()
    return await producer.publish(
        topic=settings.kafka_products_topic,
        event_type=event_type,
        payload=product_payload(product),
        key=product.id,
    )


async def publish_sale_event(
    event_type: str,
    sale: Sale,
    producer: KafkaProducerService = kafka_service,
) -> bool:
    settings = get_settings()
    return await producer.publish(
        topic=settings.kafka_sales_topic,
        event_type=event_type,
        payload=sale_payload(sale),
        key=sale.id,
    )

