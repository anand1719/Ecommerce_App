import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.base import Base
from app.db.session import get_db
from app.main import app


test_engine = create_engine(
    "sqlite:///:memory:",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(bind=test_engine, autoflush=False, autocommit=False)


@pytest.fixture()
def client():
    Base.metadata.create_all(bind=test_engine)

    def override_get_db():
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()
    Base.metadata.drop_all(bind=test_engine)


def register_customer(client: TestClient, email: str = "buyer@example.com") -> dict:
    response = client.post(
        "/api/v1/auth/register",
        json={
            "email": email,
            "password": "StrongPass123",
            "full_name": "Buyer One",
        },
    )
    assert response.status_code == 201
    return response.json()


def test_register_returns_tokens_and_profile_is_available(client: TestClient):
    tokens = register_customer(client)

    profile = client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {tokens['access_token']}"},
    )

    assert profile.status_code == 200
    assert profile.json()["email"] == "buyer@example.com"
    assert profile.json()["role"] == "customer"


def test_duplicate_registration_is_rejected(client: TestClient):
    register_customer(client)

    response = client.post(
        "/api/v1/auth/register",
        json={
            "email": "BUYER@example.com",
            "password": "StrongPass123",
        },
    )

    assert response.status_code == 409


def test_login_refresh_and_logout_flow(client: TestClient):
    register_customer(client)

    login = client.post(
        "/api/v1/auth/login",
        json={"email": "buyer@example.com", "password": "StrongPass123"},
    )
    assert login.status_code == 200
    first_refresh_token = login.json()["refresh_token"]

    refresh = client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": first_refresh_token},
    )
    assert refresh.status_code == 200
    assert refresh.json()["refresh_token"] != first_refresh_token

    old_refresh_reuse = client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": first_refresh_token},
    )
    assert old_refresh_reuse.status_code == 401

    logout = client.post(
        "/api/v1/auth/logout",
        json={"refresh_token": refresh.json()["refresh_token"]},
    )
    assert logout.status_code == 200

    refresh_after_logout = client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": refresh.json()["refresh_token"]},
    )
    assert refresh_after_logout.status_code == 401


def test_change_password_revokes_refresh_tokens(client: TestClient):
    tokens = register_customer(client)

    response = client.post(
        "/api/v1/auth/change-password",
        headers={"Authorization": f"Bearer {tokens['access_token']}"},
        json={
            "current_password": "StrongPass123",
            "new_password": "EvenStronger123",
        },
    )
    assert response.status_code == 200

    old_login = client.post(
        "/api/v1/auth/login",
        json={"email": "buyer@example.com", "password": "StrongPass123"},
    )
    assert old_login.status_code == 401

    new_login = client.post(
        "/api/v1/auth/login",
        json={"email": "buyer@example.com", "password": "EvenStronger123"},
    )
    assert new_login.status_code == 200

    revoked_refresh = client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": tokens["refresh_token"]},
    )
    assert revoked_refresh.status_code == 401

