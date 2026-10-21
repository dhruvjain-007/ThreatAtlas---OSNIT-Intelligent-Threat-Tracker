import hashlib
import time
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock
import pytest
from app.ingestion.config import RSSFeedConfig
from app.ingestion.rss_collector import (
    RSSCollector,
    clean_html_text,
    generate_source_specific_id,
    parse_entry_timestamp,
)
from app.ingestion.service import IngestionService
from app.schemas.raw_post import RawPostCreate


def test_clean_html_text():
    html_input = "<p>Explosion <b>reported</b> near <a href='#'>center</a>.</p>"
    cleaned = clean_html_text(html_input)
    assert "Explosion" in cleaned and "center" in cleaned


def test_generate_source_specific_id_guid():
    entry = {"guid": "bbc_item_12345", "link": "http://example.com/12345"}
    source_id = generate_source_specific_id(entry, "BBC News")
    assert source_id == "bbc_item_12345"


def test_generate_source_specific_id_link_fallback():
    entry = {"link": "http://example.com/item/5678"}
    source_id = generate_source_specific_id(entry, "Test Source")
    expected = hashlib.sha256(b"http://example.com/item/5678").hexdigest()
    assert source_id == expected


def test_generate_source_specific_id_title_fallback():
    entry = {"title": "Breaking News", "published": "Wed, 12 Aug 2026 12:00:00 GMT"}
    source_id = generate_source_specific_id(entry, "Source A")
    expected_str = "Source A:Breaking News:Wed, 12 Aug 2026 12:00:00 GMT"
    expected = hashlib.sha256(expected_str.encode("utf-8")).hexdigest()
    assert source_id == expected


def test_parse_entry_timestamp_valid():
    struct_t = time.gmtime(1700000000)
    entry = {"published_parsed": struct_t}
    ts = parse_entry_timestamp(entry)
    assert ts.tzinfo is timezone.utc
    assert int(ts.timestamp()) == 1700000000


def test_parse_entry_timestamp_missing_fallback():
    entry = {}
    ts = parse_entry_timestamp(entry)
    assert ts is not None
    assert ts.tzinfo is timezone.utc


def test_normalize_entry_valid():
    collector = RSSCollector()
    entry = {
        "id": "item-001",
        "title": "Military exercise announced",
        "summary": "<p>Joint maneuvers scheduled for next week.</p>",
        "link": "https://news.example.com/article/001",
        "published": "Wed, 12 Aug 2026 10:00:00 GMT",
        "language": "en",
        "author": "Reporter A",
    }
    post_create = collector.normalize_entry(entry, "Example News")
    assert post_create is not None
    assert isinstance(post_create, RawPostCreate)
    assert post_create.source == "Example News"
    assert post_create.source_specific_id == "item-001"
    assert "Military exercise announced" in post_create.text
    assert post_create.processing_status == "pending"


def test_normalize_entry_empty_content():
    collector = RSSCollector()
    entry = {"id": "item-002", "title": "", "summary": ""}
    post_create = collector.normalize_entry(entry, "Empty Source")
    assert post_create is None


def test_normalize_entry_with_content():
    collector = RSSCollector()
    entry = {
        "id": "item-003",
        "title": "Atom Feed Entry",
        "content": [
            {"type": "text/html", "value": "<p>This is the <b>actual</b> content.</p>"}
        ]
    }
    post_create = collector.normalize_entry(entry, "Atom Source")
    assert post_create is not None
    assert "Atom Feed Entry" in post_create.text
    assert "This is the actual content." in post_create.text


def test_normalize_entry_fallback_to_summary():
    collector = RSSCollector()
    entry = {
        "id": "item-004",
        "title": "RSS Feed Entry",
        "summary": "This is a summary."
    }
    post_create = collector.normalize_entry(entry, "RSS Source")
    assert post_create is not None
    assert "RSS Feed Entry" in post_create.text
    assert "This is a summary." in post_create.text
    assert "content" not in entry



@pytest.mark.asyncio
async def test_ingestion_service_stats_and_deduplication():
    mock_db = MagicMock()
    mock_collection = MagicMock()
    mock_db.__getitem__.return_value = mock_collection

    mock_collector = MagicMock()
    mock_collector.fetch_feed_entries = AsyncMock(return_value=(
        {"title": "Mock Feed"},
        [
            {"id": "entry-1", "title": "First Entry", "summary": "Summary 1"},
            {"id": "entry-2", "title": "Second Entry", "summary": "Summary 2"},
        ]
    ))
    mock_collector.normalize_entry.side_effect = lambda entry, source, meta: RawPostCreate(
        source=source,
        source_specific_id=entry["id"],
        text=entry["title"],
        original_timestamp=datetime.now(timezone.utc),
    )

    mock_response = MagicMock(id="obj_123")
    service = IngestionService(mock_db, collector=mock_collector)
    service.repository.create = AsyncMock(side_effect=[mock_response, None])

    feed_cfg = RSSFeedConfig(name="Mock Feed", url="https://mock.example.com/rss")
    success, processed, inserted, duplicates, failed = await service.ingest_feed(feed_cfg)

    assert success is True
    assert processed == 2
    assert inserted == 1
    assert duplicates == 1
    assert failed == 0


@pytest.mark.asyncio
async def test_ingestion_service_feed_failure_isolation():
    mock_db = MagicMock()
    mock_collector = MagicMock()

    async def mock_fetch(url):
        if "bad" in url:
            return {}, []
        return {"title": "Good Feed"}, [{"id": "good-1", "title": "Good Entry"}]

    mock_collector.fetch_feed_entries = AsyncMock(side_effect=mock_fetch)
    mock_collector.normalize_entry.return_value = RawPostCreate(
        source="Good Feed",
        source_specific_id="good-1",
        text="Good Entry",
        original_timestamp=datetime.now(timezone.utc),
    )

    service = IngestionService(mock_db, collector=mock_collector)
    service.repository.create = AsyncMock(return_value=MagicMock(id="obj_good"))

    feeds = [
        RSSFeedConfig(name="Bad Feed", url="https://bad.example.com/rss"),
        RSSFeedConfig(name="Good Feed", url="https://good.example.com/rss"),
    ]

    stats = await service.ingest_all_feeds(feeds)
    assert stats.feeds_attempted == 2
    assert stats.feeds_succeeded == 1
    assert stats.feeds_failed == 1
    assert stats.entries_inserted == 1


def test_api_ingestion_endpoint():
    from main import app
    from fastapi.testclient import TestClient

    with TestClient(app) as client:
        res = client.post("/api/v1/ingestion/rss")
        assert res.status_code == 200
        data = res.json()
        assert "feeds_attempted" in data
        assert "entries_processed" in data


@pytest.mark.asyncio
async def test_fetch_feed_entries_headers(mocker):
    """Verify that RSSCollector sends standard browser headers to prevent 403 and 406 errors."""
    collector = RSSCollector()

    captured_headers = {}
    mock_resp = MagicMock()
    mock_resp.text = "<rss><channel><title>Test</title></channel></rss>"
    mock_resp.raise_for_status = MagicMock()

    async def mock_get(url, headers=None, **kwargs):
        nonlocal captured_headers
        captured_headers = headers or {}
        return mock_resp

    mock_client = MagicMock()
    mock_client.get = AsyncMock(side_effect=mock_get)
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=None)

    mocker.patch("httpx.AsyncClient", return_value=mock_client)

    meta, entries = await collector.fetch_feed_entries("https://example.com/rss.xml")
    assert "User-Agent" in captured_headers
    assert "Chrome/122.0.0.0" in captured_headers["User-Agent"]
    assert "application/rss+xml" in captured_headers["Accept"]

