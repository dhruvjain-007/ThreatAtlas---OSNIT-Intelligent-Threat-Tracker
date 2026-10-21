import logging
from typing import Optional
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
from pymongo import GEOSPHERE, IndexModel, ASCENDING, DESCENDING
from app.core.config import settings

logger = logging.getLogger("threat_atlas.db")


class DatabaseSession:
    client: Optional[AsyncIOMotorClient] = None
    db: Optional[AsyncIOMotorDatabase] = None


db_session = DatabaseSession()


def get_database() -> AsyncIOMotorDatabase:
    """Return active database instance."""
    if db_session.db is None:
        raise RuntimeError("Database connection is not initialized. Ensure connect_to_mongo() has been called.")
    return db_session.db


import re

def mask_mongodb_uri(uri: str) -> str:
    """
    Sanitize MongoDB URI before logging by replacing credentials with '****'.
    Example: mongodb+srv://user:pass@cluster.mongodb.net/... -> mongodb+srv://user:****@cluster.mongodb.net/...
    """
    if not uri:
        return ""
    return re.sub(r":([^@/]+)@", r":****@", uri)


async def connect_to_mongo() -> None:
    """Initialize MongoDB connection pool on startup."""
    masked_uri = mask_mongodb_uri(settings.MONGO_URI)
    logger.info("Connecting to MongoDB at %s...", masked_uri)
    db_session.client = AsyncIOMotorClient(
        settings.MONGO_URI,
        uuidRepresentation="standard",
    )
    db_session.db = db_session.client[settings.MONGO_DB_NAME]
    logger.info("MongoDB connection established to database: %s", settings.MONGO_DB_NAME)


async def close_mongo_connection() -> None:
    """Close MongoDB connection pool on shutdown."""
    if db_session.client:
        logger.info("Closing MongoDB connection...")
        db_session.client.close()
        db_session.client = None
        db_session.db = None
        logger.info("MongoDB connection closed.")


async def init_db() -> None:
    """Initialize required MongoDB collections and indexes idempotently."""
    db = get_database()

    # RawPosts Collection Indexes
    raw_posts_indexes = [
        IndexModel(
            [("source", ASCENDING), ("source_specific_id", ASCENDING)],
            name="idx_raw_posts_source_unique_id",
            unique=True,
        ),
        IndexModel(
            [("original_timestamp", DESCENDING)],
            name="idx_raw_posts_original_timestamp",
        ),
        IndexModel(
            [("processing_status", ASCENDING)],
            name="idx_raw_posts_processing_status",
        ),
    ]

    # Events Collection Indexes
    events_indexes = [
        IndexModel(
            [("event_timestamp", DESCENDING)],
            name="idx_events_timestamp",
        ),
        IndexModel(
            [("threat_level", ASCENDING)],
            name="idx_events_threat_level",
        ),
        IndexModel(
            [("event_type", ASCENDING)],
            name="idx_events_type",
        ),
        IndexModel(
            [("source_ids", ASCENDING)],
            name="idx_events_source_ids",
        ),
        IndexModel(
            [("location", GEOSPHERE)],
            name="idx_events_location_2dsphere",
        ),
        IndexModel(
            [("country_code", ASCENDING)],
            name="idx_events_country_code",
        ),
    ]

    # Webhooks Collection Indexes
    webhooks_indexes = [
        IndexModel(
            [("is_active", ASCENDING)],
            name="idx_webhooks_is_active",
        ),
    ]

    try:
        logger.info("Creating indexes for raw_posts collection...")
        await db.raw_posts.create_indexes(raw_posts_indexes)
        logger.info("Creating indexes for events collection...")
        await db.events.create_indexes(events_indexes)
        logger.info("Creating indexes for webhooks collection...")
        await db.webhooks.create_indexes(webhooks_indexes)
        logger.info("MongoDB indexes created successfully.")
    except Exception as e:
        logger.warning("Index creation notice/warning: %s", str(e))
