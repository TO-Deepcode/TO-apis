import asyncio
from collections.abc import Awaitable, Callable
from typing import TypeVar

import httpx

from .config import get_settings

T = TypeVar("T")

_client: httpx.AsyncClient | None = None
_client_lock = asyncio.Lock()


async def get_http_client() -> httpx.AsyncClient:
    global _client

    if _client is None:
        async with _client_lock:
            if _client is None:
                settings = get_settings()
                limits = httpx.Limits(
                    max_connections=settings.http_max_connections,
                    max_keepalive_connections=settings.http_max_keepalive,
                )
                _client = httpx.AsyncClient(
                    timeout=settings.http_timeout,
                    limits=limits,
                    headers={"User-Agent": settings.http_user_agent},
                )
    return _client


async def with_http_client(fn: Callable[[httpx.AsyncClient], Awaitable[T]]) -> T:
    client = await get_http_client()
    return await fn(client)


async def shutdown_http_client() -> None:
    global _client
    if _client is not None:
        await _client.aclose()
        _client = None
