from functools import lru_cache
from pydantic import Field, HttpUrl
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="", extra="ignore")

    http_timeout: float = Field(10.0, gt=0, alias="HTTP_TIMEOUT")
    http_max_connections: int = Field(20, ge=1, alias="HTTP_MAX_CONNECTIONS")
    http_max_keepalive: int = Field(10, ge=1, alias="HTTP_MAX_KEEPALIVE")
    http_user_agent: str = Field(
        "FastPI/0.1 (+https://example.com; contact=admin@example.com)",
        alias="HTTP_USER_AGENT",
    )

    bybit_base_url: HttpUrl = Field("https://api.bybit.com", alias="BYBIT_BASE_URL")
    binance_base_url: HttpUrl = Field("https://api.binance.com", alias="BINANCE_BASE_URL")
    coincap_base_url: HttpUrl = Field(
        "https://api.coincap.io/v2", alias="COINCAP_BASE_URL"
    )
    coincap_api_key: str | None = Field(default=None, alias="COINCAP_API_KEY")
    coinmarketcap_api_key: str | None = Field(
        default=None, alias="COINMARKETCAP_API_KEY"
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()
