import httpx
import pytest
import respx

import fastpi.services.news as news_module
from fastpi.config import Settings


@pytest.mark.asyncio
async def test_news_service_extracts_articles(monkeypatch) -> None:
    target = news_module.ScrapeTarget(
        name="TestSource",
        url="https://testsource.example/",
        limit=3,
    )
    monkeypatch.setattr(news_module, "SCRAPE_TARGETS", (target,))

    html = """
    <html>
      <body>
        <article>
          <a href="/article-1">First crypto update</a>
          <time datetime="2024-05-20T12:34:00Z"></time>
          <p>Summary about the first article.</p>
        </article>
        <article>
          <a href="https://external.com/article-2">Second crypto insight</a>
          <time>May 21, 2024 09:15 UTC</time>
        </article>
      </body>
    </html>
    """

    settings = Settings()
    async with httpx.AsyncClient() as client:
        service = news_module.NewsService(settings=settings, client=client)
        with respx.mock(assert_all_called=True) as mock:
            mock.get("https://testsource.example/").respond(200, text=html)
            aggregate = await service.fetch_all(limit_per_source=2)

    assert len(aggregate.feeds) == 1
    feed = aggregate.feeds[0]
    assert feed.source == "TestSource"
    assert len(feed.items) == 2
    first = feed.items[0]
    assert first.title == "First crypto update"
    assert str(first.url) == "https://testsource.example/article-1"
    assert first.published_at is not None


@pytest.mark.asyncio
async def test_news_service_fetches_cryptopanic_rss(monkeypatch) -> None:
    target = news_module.ScrapeTarget(
        name="CryptoPanic",
        url="https://cryptopanic.com/news/rss/",
        limit=2,
    )
    monkeypatch.setattr(news_module, "SCRAPE_TARGETS", (target,))

    rss = """<?xml version="1.0" encoding="UTF-8"?>
    <rss version="2.0">
      <channel>
        <title>Crypto News</title>
        <item>
          <title>Market sentiment flips</title>
          <link>https://cryptopanic.com/news/market-sentiment</link>
          <pubDate>Mon, 20 May 2024 15:20:00 +0000</pubDate>
          <description>Quick summary.</description>
        </item>
      </channel>
    </rss>
    """

    settings = Settings()
    async with httpx.AsyncClient() as client:
        service = news_module.NewsService(settings=settings, client=client)
        with respx.mock(assert_all_called=True) as mock:
            mock.get("https://cryptopanic.com/news/rss/").respond(200, text=rss)
            aggregate = await service.fetch_all(limit_per_source=2)

    assert len(aggregate.feeds) == 1
    feed = aggregate.feeds[0]
    assert feed.source == "CryptoPanic"
    assert len(feed.items) == 1
    item = feed.items[0]
    assert item.title == "Market sentiment flips"
    assert str(item.url) == "https://cryptopanic.com/news/market-sentiment"
    assert item.published_at is not None
