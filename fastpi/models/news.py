from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field, HttpUrl


class NewsArticle(BaseModel):
    source: str = Field(description="Publisher name")
    title: str = Field(description="Article headline")
    url: HttpUrl = Field(description="Canonical article URL")
    published_at: datetime | None = Field(
        default=None, description="Publication timestamp in UTC if available"
    )
    summary: str | None = Field(default=None, description="Short teaser or dek")
    metadata: dict[str, Any] = Field(default_factory=dict)


class NewsFeed(BaseModel):
    source: str = Field(description="Publisher name")
    fetched_at: datetime = Field(description="UTC timestamp of the fetch")
    items: list[NewsArticle] = Field(default_factory=list)


class NewsAggregate(BaseModel):
    fetched_at: datetime = Field(description="UTC timestamp of the aggregation")
    feeds: list[NewsFeed] = Field(default_factory=list)
