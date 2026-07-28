from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.security import get_password_hash
from app.db.base import Base
from app.db.session import get_db
from app.main import app
from app.models.user import User, UserRole


test_engine = create_engine(
    "sqlite:///:memory:",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(bind=test_engine, autoflush=False, autocommit=False)


def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


def setup_client():
    Base.metadata.create_all(bind=test_engine)
    app.dependency_overrides[get_db] = override_get_db
    return TestClient(app)


def teardown_client():
    app.dependency_overrides.clear()
    Base.metadata.drop_all(bind=test_engine)


def create_admin_user() -> None:
    db = TestingSessionLocal()
    try:
        db.add(
            User(
                email="admin@example.com",
                hashed_password=get_password_hash("AdminPass123"),
                full_name="Admin User",
                role=UserRole.ADMIN,
            )
        )
        db.commit()
    finally:
        db.close()


def register_customer(client: TestClient) -> dict:
    response = client.post(
        "/api/v1/auth/register",
        json={
            "email": "customer@example.com",
            "password": "StrongPass123",
            "full_name": "Customer User",
        },
    )
    assert response.status_code == 201
    return response.json()


def login_admin(client: TestClient) -> dict:
    response = client.post(
        "/api/v1/auth/login",
        json={"email": "admin@example.com", "password": "AdminPass123"},
    )
    assert response.status_code == 200
    return response.json()


def create_product(client: TestClient, admin_tokens: dict) -> dict:
    response = client.post(
        "/api/v1/products",
        headers={"Authorization": f"Bearer {admin_tokens['access_token']}"},
        json={
            "sku": "SKU-100",
            "name": "Wireless Mouse",
            "description": "Ergonomic ecommerce sample product",
            "price": "25.50",
            "stock_quantity": 10,
            "is_active": True,
        },
    )
    assert response.status_code == 201
    return response.json()


def test_admin_can_manage_products_and_customer_cannot():
    client = setup_client()
    try:
        create_admin_user()
        customer_tokens = register_customer(client)
        admin_tokens = login_admin(client)

        denied = client.post(
            "/api/v1/products",
            headers={"Authorization": f"Bearer {customer_tokens['access_token']}"},
            json={
                "sku": "SKU-101",
                "name": "Denied Product",
                "price": "10.00",
                "stock_quantity": 5,
            },
        )
        assert denied.status_code == 403

        product = create_product(client, admin_tokens)
        assert product["sku"] == "SKU-100"

        update = client.patch(
            f"/api/v1/products/{product['id']}",
            headers={"Authorization": f"Bearer {admin_tokens['access_token']}"},
            json={"price": "27.99", "stock_quantity": 12},
        )
        assert update.status_code == 200
        assert update.json()["price"] == "27.99"
        assert update.json()["stock_quantity"] == 12

        listing = client.get(
            "/api/v1/products",
            headers={"Authorization": f"Bearer {customer_tokens['access_token']}"},
        )
        assert listing.status_code == 200
        assert len(listing.json()) == 1

        delete = client.delete(
            f"/api/v1/products/{product['id']}",
            headers={"Authorization": f"Bearer {admin_tokens['access_token']}"},
        )
        assert delete.status_code == 200

        listing_after_delete = client.get(
            "/api/v1/products",
            headers={"Authorization": f"Bearer {customer_tokens['access_token']}"},
        )
        assert listing_after_delete.status_code == 200
        assert listing_after_delete.json() == []
    finally:
        teardown_client()


def test_protected_product_and_sales_endpoints_require_jwt():
    client = setup_client()
    try:
        product_create = client.post(
            "/api/v1/products",
            json={
                "sku": "SKU-LOCKED",
                "name": "Locked Product",
                "price": "10.00",
                "stock_quantity": 5,
            },
        )
        assert product_create.status_code == 401

        product_list = client.get("/api/v1/products")
        assert product_list.status_code == 401

        product_detail = client.get("/api/v1/products/missing-product")
        assert product_detail.status_code == 401

        sales_list = client.get("/api/v1/sales")
        assert sales_list.status_code == 401

        sale_create = client.post(
            "/api/v1/sales",
            json={"items": [{"product_id": "missing-product", "quantity": 1}]},
        )
        assert sale_create.status_code == 401
    finally:
        teardown_client()


def test_customer_can_create_sale_and_cancel_pending_sale_restores_stock():
    client = setup_client()
    try:
        create_admin_user()
        customer_tokens = register_customer(client)
        admin_tokens = login_admin(client)
        product = create_product(client, admin_tokens)

        sale = client.post(
            "/api/v1/sales",
            headers={"Authorization": f"Bearer {customer_tokens['access_token']}"},
            json={
                "items": [{"product_id": product["id"], "quantity": 2}],
                "tax_amount": "2.00",
                "discount_amount": "1.00",
            },
        )
        assert sale.status_code == 201
        assert sale.json()["subtotal"] == "51.00"
        assert sale.json()["total_amount"] == "52.00"
        assert sale.json()["items"][0]["quantity"] == 2

        product_after_sale = client.get(
            f"/api/v1/products/{product['id']}",
            headers={"Authorization": f"Bearer {customer_tokens['access_token']}"},
        )
        assert product_after_sale.status_code == 200
        assert product_after_sale.json()["stock_quantity"] == 8

        customer_sales = client.get(
            "/api/v1/sales",
            headers={"Authorization": f"Bearer {customer_tokens['access_token']}"},
        )
        assert customer_sales.status_code == 200
        assert len(customer_sales.json()) == 1

        cancel = client.delete(
            f"/api/v1/sales/{sale.json()['id']}",
            headers={"Authorization": f"Bearer {customer_tokens['access_token']}"},
        )
        assert cancel.status_code == 200

        cancelled_sale = client.get(
            f"/api/v1/sales/{sale.json()['id']}",
            headers={"Authorization": f"Bearer {customer_tokens['access_token']}"},
        )
        assert cancelled_sale.status_code == 200
        assert cancelled_sale.json()["status"] == "cancelled"

        product_after_cancel = client.get(
            f"/api/v1/products/{product['id']}",
            headers={"Authorization": f"Bearer {customer_tokens['access_token']}"},
        )
        assert product_after_cancel.status_code == 200
        assert product_after_cancel.json()["stock_quantity"] == 10
    finally:
        teardown_client()


def test_admin_can_update_sale_status():
    client = setup_client()
    try:
        create_admin_user()
        customer_tokens = register_customer(client)
        admin_tokens = login_admin(client)
        product = create_product(client, admin_tokens)

        sale = client.post(
            "/api/v1/sales",
            headers={"Authorization": f"Bearer {customer_tokens['access_token']}"},
            json={"items": [{"product_id": product["id"], "quantity": 1}]},
        )
        assert sale.status_code == 201

        status_update = client.patch(
            f"/api/v1/sales/{sale.json()['id']}/status",
            headers={"Authorization": f"Bearer {admin_tokens['access_token']}"},
            json={"status": "paid"},
        )
        assert status_update.status_code == 200
        assert status_update.json()["status"] == "paid"
    finally:
        teardown_client()
