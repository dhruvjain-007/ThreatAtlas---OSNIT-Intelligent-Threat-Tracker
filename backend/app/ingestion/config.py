from typing import List
from pydantic import BaseModel, HttpUrl, Field


class RSSFeedConfig(BaseModel):
    """Configuration for a single public RSS feed source."""

    name: str = Field(..., description="Human-readable name of the feed source")
    url: str = Field(..., description="HTTP/HTTPS URL of the RSS XML feed")
    enabled: bool = Field(default=True, description="Whether to include feed in ingestion runs")


# Default legitimate public RSS sources for defensive threat monitoring
DEFAULT_RSS_FEEDS: List[RSSFeedConfig] = [
    RSSFeedConfig(
        name="Al Jazeera Breaking News",
        url="https://www.aljazeera.com/xml/rss/all.xml",
    ),
    RSSFeedConfig(
        name="BBC World News",
        url="https://feeds.bbci.co.uk/news/world/rss.xml",
    ),
    RSSFeedConfig(
        name="UN News Global Perspective",
        url="https://news.un.org/feed/subscribe/en/news/all/rss.xml",
    ),
    RSSFeedConfig(
        name="CrisisWatch International",
        url="https://www.crisisgroup.org/rss-feed",
    ),
    RSSFeedConfig(
        name="Defense Blog",
        url="https://defence-blog.com/feed/",
    ),
    RSSFeedConfig(
        name="Defense News",
        url="https://www.defensenews.com/arc/outboundfeeds/rss/",
    ),
    RSSFeedConfig(
        name="Reuters World",
        url="https://feeds.bbci.co.uk/news/world/rss.xml",
    ),
    RSSFeedConfig(
        name="ReliefWeb Crisis Reports",
        url="https://reliefweb.int/updates/rss.xml",
    ),
    RSSFeedConfig(
        name="US Naval Institute News",
        url="https://news.usni.org/feed",
    ),
    RSSFeedConfig(
        name="UK MOD / Security Announcements",
        url="https://www.gov.uk/government/organisations/ministry-of-defence.atom",
    ),
]
