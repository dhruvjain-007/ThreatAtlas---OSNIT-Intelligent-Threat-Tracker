import calendar
import hashlib
import logging
import time
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from bs4 import BeautifulSoup
import feedparser
import httpx
from app.schemas.common import utc_now
from app.schemas.raw_post import RawPostCreate

logger = logging.getLogger("threat_atlas.ingestion.rss")


def clean_html_text(raw_html: Optional[str]) -> str:
    """Strip HTML tags and normalize whitespace."""
    if not raw_html:
        return ""
    soup = BeautifulSoup(raw_html, "html.parser")
    text = soup.get_text(separator=" ")
    return " ".join(text.split()).strip()


def generate_source_specific_id(entry: Dict[str, Any], source_name: str) -> str:
    """Generate a deterministic unique ID for an RSS entry."""
    entry_id = entry.get("id") or entry.get("guid")
    if entry_id and isinstance(entry_id, str) and entry_id.strip():
        return entry_id.strip()

    link = entry.get("link")
    if link and isinstance(link, str) and link.strip():
        return hashlib.sha256(link.strip().encode("utf-8")).hexdigest()

    title = entry.get("title", "")
    published = entry.get("published", "")
    raw_str = f"{source_name}:{title}:{published}"
    return hashlib.sha256(raw_str.encode("utf-8")).hexdigest()


def parse_entry_timestamp(entry: Dict[str, Any]) -> datetime:
    """Extract and parse entry publication timestamp into UTC datetime."""
    struct_time = entry.get("published_parsed") or entry.get("updated_parsed")
    if struct_time:
        try:
            timestamp_sec = calendar.timegm(struct_time)
            return datetime.fromtimestamp(timestamp_sec, tz=timezone.utc)
        except (ValueError, OverflowError):
            pass
    return utc_now()


class RSSCollector:
    """Collector for fetching, parsing, and normalizing public RSS feeds."""

    def __init__(self, timeout_seconds: int = 10):
        self.timeout = timeout_seconds

    async def fetch_feed_entries(self, feed_url: str) -> tuple[Dict[str, Any], List[Dict[str, Any]]]:
        """Fetch raw XML content via httpx and parse with feedparser."""
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
            "Accept": "application/rss+xml, application/xml, text/xml, application/atom+xml, text/html, */*",
        }
        try:
            async with httpx.AsyncClient(timeout=self.timeout, follow_redirects=True) as client:
                response = await client.get(feed_url, headers=headers)
                response.raise_for_status()
                parsed = feedparser.parse(response.text)

                if parsed.bozo and not parsed.entries:
                    logger.warning("Feedparser warning for '%s': %s", feed_url, parsed.bozo_exception)
                    return {}, []

                feed_meta = parsed.get("feed", {})
                entries = parsed.get("entries", [])
                return feed_meta, entries
        except httpx.HTTPError as exc:
            logger.error("HTTP error fetching RSS feed '%s': %s", feed_url, str(exc))
            return {}, []
        except Exception as exc:
            logger.error("Unexpected error fetching RSS feed '%s': %s", feed_url, str(exc))
            return {}, []

    def normalize_entry(
        self,
        entry: Dict[str, Any],
        source_name: str,
        feed_meta: Optional[Dict[str, Any]] = None,
    ) -> Optional[RawPostCreate]:
        """Normalize an RSS entry dictionary into a validated RawPostCreate schema."""
        title = clean_html_text(entry.get("title", ""))

        content_text = ""
        entry_content = entry.get("content")
        if isinstance(entry_content, list):
            pieces = []
            for c in entry_content:
                if isinstance(c, dict):
                    val = c.get("value")
                    if val and isinstance(val, str):
                        pieces.append(val)
            if pieces:
                content_text = clean_html_text("\n\n".join(pieces))

        summary = clean_html_text(entry.get("summary") or entry.get("description") or "")
        body = content_text if content_text else summary

        if title and body:
            full_text = f"{title}\n\n{body}"
        elif title:
            full_text = title
        elif body:
            full_text = body
        else:
            logger.warning("Skipping entry from '%s' with empty title and text content.", source_name)
            return None

        source_id = generate_source_specific_id(entry, source_name)
        url = entry.get("link")
        original_ts = parse_entry_timestamp(entry)

        feed_meta = feed_meta or {}
        language = entry.get("language") or feed_meta.get("language")
        author = entry.get("author") or feed_meta.get("title")

        media_list = []
        if "enclosures" in entry and isinstance(entry["enclosures"], list):
            for enc in entry["enclosures"]:
                media_list.append({
                    "url": enc.get("href") or enc.get("url"),
                    "type": enc.get("type"),
                    "length": enc.get("length"),
                })

        media_metadata = {"media": media_list} if media_list else None

        try:
            return RawPostCreate(
                source=source_name,
                source_specific_id=source_id,
                text=full_text,
                url=url,
                original_timestamp=original_ts,
                language=language,
                author=author,
                media_metadata=media_metadata,
                processing_status="pending",
            )
        except Exception as exc:
            logger.error("Failed to validate RawPostCreate for entry in '%s': %s", source_name, str(exc))
            return None
