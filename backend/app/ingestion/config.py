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
        name="Al Jazeera World",
        url="https://www.aljazeera.com/xml/rss/all.xml",
    ),
    RSSFeedConfig(
        name="BBC World News",
        url="https://feeds.bbci.co.uk/news/world/rss.xml",
    ),
    RSSFeedConfig(
        name="The Guardian World",
        url="https://www.theguardian.com/world/rss",
    ),
    RSSFeedConfig(
        name="CrisisWatch International",
        url="https://www.crisisgroup.org/rss",
    ),
    RSSFeedConfig(
        name="Defense One",
        url="https://www.defenseone.com/rss/all/",
    ),
    RSSFeedConfig(
        name="Defense News",
        url="https://www.defensenews.com/arc/outboundfeeds/rss/",
    ),
    RSSFeedConfig(
        name="France 24 World",
        url="https://www.france24.com/en/rss",
    ),
    RSSFeedConfig(
        name="UK MOD / Security Announcements",
        url="https://www.gov.uk/government/organisations/ministry-of-defence.atom",
    ),
]
