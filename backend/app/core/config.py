from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = Field(default="Ecommerce Authentication API", alias="APP_NAME")
    api_v1_prefix: str = "/api/v1"
    environment: str = Field(default="local", alias="ENVIRONMENT")
    database_url: str = Field(default="sqlite:///./ecommerce_auth.db", alias="DATABASE_URL")
    secret_key: str = Field(default="change-this-secret-in-production", alias="SECRET_KEY")
    algorithm: str = "HS256"
    access_token_expire_minutes: int = Field(default=30, alias="ACCESS_TOKEN_EXPIRE_MINUTES")
    refresh_token_expire_days: int = Field(default=7, alias="REFRESH_TOKEN_EXPIRE_DAYS")
    kafka_enabled: bool = Field(default=False, alias="KAFKA_ENABLED")
    kafka_bootstrap_servers: str = Field(default="localhost:9092", alias="KAFKA_BOOTSTRAP_SERVERS")
    kafka_client_id: str = Field(default="ecommerce-api", alias="KAFKA_CLIENT_ID")
    kafka_products_topic: str = Field(default="ecommerce.products", alias="KAFKA_PRODUCTS_TOPIC")
    kafka_sales_topic: str = Field(default="ecommerce.sales", alias="KAFKA_SALES_TOPIC")
    kafka_fail_fast: bool = Field(default=False, alias="KAFKA_FAIL_FAST")

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")


@lru_cache
def get_settings() -> Settings:
    return Settings()
