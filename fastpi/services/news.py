from __future__ import annotations

import asyncio
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any
from urllib.parse import urljoin

import httpx
from bs4 import BeautifulSoup
from dateutil import parser as date_parser

from ..config import Settings, get_settings
from ..http_client import get_http_client
from ..models.news import NewsAggregate, NewsArticle, NewsFeed


@dataclass(slots=True)
class ScrapeTarget:
    name: str
    url: str
    limit: int = 6


SCRAPE_TARGETS: tuple[ScrapeTarget, ...] = (
    ScrapeTarget("CoinDesk", "https://www.coindesk.com/"),
    ScrapeTarget("The Block", "https://www.theblock.co/latest"),
    ScrapeTarget("Blockworks", "https://blockworks.co/news"),
    ScrapeTarget("Cointelegraph", "https://cointelegraph.com/"),
    ScrapeTarget("The Defiant", "https://thedefiant.io/latest"),
    ScrapeTarget("DL News", "https://www.dlnews.com/"),
    ScrapeTarget("Protos", "https://protos.com/"),
    ScrapeTarget("Decrypt", "https://decrypt.co/"),
    ScrapeTarget("Messari", "https://messari.io/news"),
    ScrapeTarget("Glassnode Insights", "https://insights.glassnode.com/"),
    ScrapeTarget("CryptoPanic", "https://cryptopanic.com/news/rss/"),
)


@dataclass(slots=True)
class NewsService:
    settings: Settings | None = None
    client: httpx.AsyncClient | None = None

    def __post_init__(self) -> None:
        if self.settings is None:
            self.settings = get_settings()

    async def fetch_all(self, limit_per_source: int = 6) -> NewsAggregate:
        client = self.client or await get_http_client()
        tasks = [
            self._fetch_target(client, target, limit_per_source)
            for target in SCRAPE_TARGETS
        ]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        feeds: list[NewsFeed] = []
        for target, result in zip(SCRAPE_TARGETS, results, strict=False):
            if isinstance(result, NewsFeed):
                feeds.append(result)
            else:
                message = str(result)
                feeds.append(
                    NewsFeed(
                        source=target.name,
                        fetched_at=datetime.now(timezone.utc),
                        items=[
                            NewsArticle(
                                source=target.name,
                                title="Failed to retrieve articles",
                                url="https://status.fastpi.dev/error",
                                summary=message,
                                published_at=None,
                                metadata={"error": message},
                            )
                        ],
                    )
                )
        return NewsAggregate(fetched_at=datetime.now(timezone.utc), feeds=feeds)

    async def _fetch_target(
        self,
        client: httpx.AsyncClient,
        target: ScrapeTarget,
        limit_per_source: int,
    ) -> NewsFeed:
        limit = min(limit_per_source, target.limit)
        if target.name == "CryptoPanic":
            return await self._fetch_cryptopanic_rss(client, target, limit)
        return await self._scrape_generic(client, target, limit)

    async def _scrape_generic(
        self,
        client: httpx.AsyncClient,
        target: ScrapeTarget,
        limit: int,
    ) -> NewsFeed:
        response = await client.get(target.url)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, "lxml")
        articles = self._extract_articles(soup, target.url, target.name, limit)
        return NewsFeed(
            source=target.name,
            fetched_at=datetime.now(timezone.utc),
            items=articles,
        )

    async def _fetch_cryptopanic_rss(
        self, client: httpx.AsyncClient, target: ScrapeTarget, limit: int
    ) -> NewsFeed:
        response = await client.get(
            target.url,
            headers={"Accept": "application/rss+xml, application/xml"},
        )
        response.raise_for_status()
        soup = BeautifulSoup(response.content, "xml")
        items: list[NewsArticle] = []
        seen: set[str] = set()
        for entry in soup.find_all("item"):
            title_tag = entry.find("title")
            link_tag = entry.find("link")
            if not title_tag or not link_tag:
                continue
            title = title_tag.get_text(strip=True)
            link = link_tag.get_text(strip=True)
            if not title or not link or link in seen:
                continue
            date_tag = entry.find("pubDate") or entry.find("dc:date")
            published = _parse_datetime(date_tag.get_text(strip=True) if date_tag else None)
            description_tag = entry.find("description")
            summary = description_tag.get_text(strip=True) if description_tag else None
            items.append(
                NewsArticle(
                    source=target.name,
                    title=title,
                    url=link,
                    summary=summary,
                    published_at=published,
                )
            )
            seen.add(link)
            if len(items) >= limit:
                break
        return NewsFeed(
            source=target.name,
            fetched_at=datetime.now(timezone.utc),
            items=items,
        )

    def _extract_articles(
        self,
        soup: BeautifulSoup,
        base_url: str,
        source: str,
        limit: int,
    ) -> list[NewsArticle]:
        articles: list[NewsArticle] = []
        seen: set[str] = set()

        for element in soup.find_all("article"):
            item = self._build_article_from_element(element, base_url, source)
            if item and item.url not in seen:
                articles.append(item)
                seen.add(str(item.url))
            if len(articles) >= limit:
                break

        if len(articles) < limit:
            fallback = soup.select("h2 a, h3 a, .headline a")
            for anchor in fallback:
                href = anchor.get("href")
                title = anchor.get_text(strip=True)
                if not href or not title or len(title) < 5:
                    continue
                absolute = urljoin(base_url, href)
                if not absolute.startswith("http"):
                    continue
                if absolute in seen:
                    continue
                articles.append(
                    NewsArticle(
                        source=source,
                        title=title,
                        url=absolute,
                        summary=None,
                        published_at=None,
                    )
                )
                seen.add(absolute)
                if len(articles) >= limit:
                    break

        return articles[:limit]

    def _build_article_from_element(
        self, element: Any, base_url: str, source: str
    ) -> NewsArticle | None:
        anchor = element.find("a", href=True)
        if not anchor:
            return None
        title = anchor.get_text(strip=True)
        if not title or len(title) < 5:
            return None
        href = urljoin(base_url, anchor.get("href"))
        if not href.startswith("http"):
            return None
        summary_tag = element.find("p")
        summary = summary_tag.get_text(strip=True) if summary_tag else None

        published = None
        time_tag = element.find("time")
        if time_tag:
            datetime_attr = (
                time_tag.get("datetime")
                or time_tag.get("data-datetime")
                or time_tag.get_text(strip=True)
            )
            published = _parse_datetime(datetime_attr)

        return NewsArticle(
            source=source,
            title=title,
            url=href,
            summary=summary,
            published_at=published,
        )


def _parse_datetime(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        parsed = date_parser.parse(value)
    except (ValueError, TypeError, OverflowError):
        return None
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)
