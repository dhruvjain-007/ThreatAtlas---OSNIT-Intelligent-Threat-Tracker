import logging
from typing import Optional
from pydantic import BaseModel, Field
from fastapi import APIRouter, BackgroundTasks, status
from app.db.session import get_database
from app.intelligence.service import intelligence_service
from app.db.repositories.event import EventRepository
from app.schemas.event import EventCreate, EventResponse
from app.schemas.common import GeoJSONPoint, utc_now
from app.core.redis import publish_event

from datetime import datetime, timezone, timedelta
from bson import ObjectId
from app.core.config import settings

logger = logging.getLogger("threat_atlas.api.intelligence")

router = APIRouter()


class ProcessPendingResponse(BaseModel):
    status: str = Field(default="ingestion_and_processing_started", description="Status of the background task")
    processed_count: Optional[int] = Field(default=None, description="Number of raw posts processed")
    passed_relevance: Optional[int] = Field(default=None, description="Number of posts that passed threat-relevance")
    geocoded_count: Optional[int] = Field(default=None, description="Number of events geocoded into map coordinates")
    events_created: Optional[int] = Field(default=None, description="Number of new events created")
    events_merged: Optional[int] = Field(default=None, description="Number of posts merged into existing events")
    events_ignored: Optional[int] = Field(default=None, description="Number of posts ignored because they were not threat-relevant")
    deleted_events: Optional[int] = Field(default=None, description="Number of stale threats deleted from database")
    deleted_posts: Optional[int] = Field(default=None, description="Number of stale raw posts deleted from database")
    errors: Optional[int] = Field(default=None, description="Number of posts that failed during processing")


class ReprocessAllResponse(BaseModel):
    status: str = Field(default="reprocessing_started", description="Status of the reprocessing task")
    unlocked_count: int = Field(..., description="Number of previously filtered/failed articles unlocked")
    deleted_events: Optional[int] = Field(default=None, description="Number of stale threats deleted from database")
    deleted_posts: Optional[int] = Field(default=None, description="Number of stale raw posts deleted from database")


class CleanupStaleResponse(BaseModel):
    status: str = Field(default="stale_threats_cleaned", description="Status of cleanup task")
    deleted_events: int = Field(default=0, description="Number of stale threats deleted from database")
    deleted_posts: int = Field(default=0, description="Number of stale raw posts deleted from database")


async def cleanup_stale_threats(db, retention_hours: Optional[int] = None) -> dict:
    """
    Purges stale and expired threats from MongoDB:
    1. Removes all events and raw posts dated on or before October 22, 2026.
    2. Removes any events and raw posts older than `retention_hours` (default settings.THREAT_RETENTION_HOURS, e.g. 48h).
    3. Removes orphaned events whose source raw posts no longer exist in the raw_posts collection.
    4. Broadcasts deletion WebSocket messages for any removed events so the UI immediately updates.
    """
    hours = retention_hours if retention_hours is not None else settings.THREAT_RETENTION_HOURS
    now = utc_now()
    retention_cutoff = now - timedelta(hours=hours)
    oct_cutoff = datetime(2026, 10, 22, 23, 59, 59, tzinfo=timezone.utc)

    deleted_events_count = 0
    deleted_posts_count = 0

    try:
        # 1. Identify stale events (older than cutoff or from October 22nd and earlier)
        event_query = {
            "$or": [
                {"event_timestamp": {"$lte": oct_cutoff}},
                {"event_timestamp": {"$lt": retention_cutoff}},
                {"created_at": {"$lte": oct_cutoff}},
            ]
        }
        cursor = db.events.find(event_query, {"_id": 1})
        docs = await cursor.to_list(length=2000)
        eids_to_delete = [doc["_id"] for doc in docs]

        if eids_to_delete:
            del_res = await db.events.delete_many({"_id": {"$in": eids_to_delete}})
            deleted_events_count += getattr(del_res, "deleted_count", 0)
            for eid in eids_to_delete:
                try:
                    await publish_event({"id": str(eid)}, action="deleted")
                except Exception:
                    pass

        # 2. Identify and delete stale raw posts
        post_query = {
            "$or": [
                {"original_timestamp": {"$lte": oct_cutoff}},
                {"original_timestamp": {"$lt": retention_cutoff}},
                {"collected_at": {"$lte": oct_cutoff}},
            ]
        }
        del_post_res = await db.raw_posts.delete_many(post_query)
        deleted_posts_count += getattr(del_post_res, "deleted_count", 0)

        # 3. Clean up orphaned events (events whose raw_post_ids no longer exist in raw_posts)
        try:
            remaining_events = await db.events.find({}, {"_id": 1, "raw_post_ids": 1}).to_list(length=1000)
            orphaned_ids = []
            for ev in remaining_events:
                pids = ev.get("raw_post_ids", [])
                if not pids:
                    orphaned_ids.append(ev["_id"])
                else:
                    valid_oids = [ObjectId(p) for p in pids if ObjectId.is_valid(p)]
                    str_pids = [str(p) for p in pids]
                    count = await db.raw_posts.count_documents({
                        "$or": [{"_id": {"$in": valid_oids + str_pids}}, {"source_specific_id": {"$in": str_pids}}]
                    })
                    if count == 0:
                        orphaned_ids.append(ev["_id"])

            if orphaned_ids:
                del_orphans = await db.events.delete_many({"_id": {"$in": orphaned_ids}})
                deleted_events_count += getattr(del_orphans, "deleted_count", 0)
                for oid in orphaned_ids:
                    try:
                        await publish_event({"id": str(oid)}, action="deleted")
                    except Exception:
                        pass
        except Exception as exc:
            logger.debug("Orphaned events check skipped or failed: %s", exc)

        logger.info(
            "Cleaned up stale threats: %d events deleted, %d raw posts deleted (cutoff: %s)",
            deleted_events_count,
            deleted_posts_count,
            retention_cutoff.isoformat(),
        )
    except Exception as exc:
        logger.warning("cleanup_stale_threats encountered error: %s", exc)

    return {
        "deleted_events": deleted_events_count,
        "deleted_posts": deleted_posts_count,
    }


async def unlock_ignored_posts(db, limit: int = 50) -> int:
    """Unlock up to `limit` ignored posts back to 'pending' state."""
    try:
        filter_query = {
            "$or": [
                {"processing_status": "ignored"},
                {"status": "ignored"},
            ]
        }
        cursor = db.raw_posts.find(filter_query, {"_id": 1}).limit(limit)
        docs = await cursor.to_list(length=limit)
        if not docs:
            return 0
        ids_to_unlock = [d["_id"] for d in docs]
        res = await db.raw_posts.update_many(
            {"_id": {"$in": ids_to_unlock}},
            {"$set": {"processing_status": "pending", "status": "pending", "updated_at": utc_now()}},
        )
        logger.info("Automatically unlocked %d ignored posts for re-evaluation", res.modified_count)
        return res.modified_count
    except Exception as exc:
        logger.debug("unlock_ignored_posts skipped or failed: %s", exc)
        return 0


async def _run_ingest_and_process(db, limit: int = 100, batch_size: int = 5) -> None:
    """Run RSS ingestion followed immediately by intelligence NLP and clustering processing."""
    # 1. Clean up stale/non-existent threats before fetching new feeds
    try:
        await cleanup_stale_threats(db)
    except Exception as exc:
        logger.debug("cleanup_stale_threats in _run_ingest_and_process skipped: %s", exc)

    try:
        from app.ingestion.service import IngestionService
        ingestion_service = IngestionService(db)
        stats = await ingestion_service.ingest_all_feeds()
        logger.info(
            "Background ingestion finished: attempted=%d, succeeded=%d, inserted=%d",
            stats.feeds_attempted,
            stats.feeds_succeeded,
            stats.entries_inserted,
        )
    except Exception as exc:
        logger.error("Background ingestion failed: %s", exc, exc_info=True)

    try:
        # If no pending posts exist, automatically unlock up to 50 ignored posts
        try:
            pending_count = await db.raw_posts.count_documents({
                "$or": [
                    {"processing_status": "pending"},
                    {"status": "pending"},
                ]
            })
            if pending_count == 0:
                await unlock_ignored_posts(db, limit=50)
        except Exception as exc:
            logger.debug("Could not check pending count during ingestion: %s", exc)

        process_stats = await intelligence_service.process_pending_batch(
            db=db,
            limit=limit,
            batch_size=batch_size,
        )
        logger.info(
            "Background intelligence processing finished: processed=%d, passed_relevance=%d, geocoded=%d, created=%d, merged=%d",
            process_stats.get("processed_count", 0),
            process_stats.get("passed_relevance", 0),
            process_stats.get("geocoded_count", 0),
            process_stats.get("events_created", 0),
            process_stats.get("events_merged", 0),
        )
    except Exception as exc:
        logger.error("Background intelligence processing failed: %s", exc, exc_info=True)


@router.post(
    "/process-pending",
    response_model=ProcessPendingResponse,
    status_code=status.HTTP_202_ACCEPTED,
    response_model_exclude_none=True,
    summary="Trigger Combined Ingestion & Batch Intelligence Processing",
)
async def process_pending_posts(
    background_tasks: BackgroundTasks,
    limit: int = 100,
    batch_size: int = 5,
    ingest: bool = True,
):
    """
    Executes the end-to-end ingestion and processing pipeline asynchronously:
    1. Deletes stale and non-existent threats from earlier dates.
    2. If pending count is 0, unlocks up to 50 ignored posts so sync always evaluates real data.
    3. Ingests all active RSS feeds to pull latest raw posts.
    4. Runs text cleaning, NER, EntityRuler, Geocoding, and Event Clustering on pending posts.
    5. Broadcasts new/updated events via WebSockets.
    6. Returns HTTP 202 Accepted immediately.
    """
    db = get_database()
    cleanup_stats = {}
    try:
        cleanup_stats = await cleanup_stale_threats(db)
    except Exception as exc:
        logger.debug("cleanup_stale_threats in process_pending skipped: %s", exc)

    try:
        pending_count = await db.raw_posts.count_documents({
            "$or": [
                {"processing_status": "pending"},
                {"status": "pending"},
            ]
        })
        if pending_count == 0:
            await unlock_ignored_posts(db, limit=50)
    except Exception as exc:
        logger.debug("Could not check pending count in process_pending: %s", exc)

    if ingest:
        background_tasks.add_task(
            _run_ingest_and_process,
            db=db,
            limit=limit,
            batch_size=batch_size,
        )
        return ProcessPendingResponse(
            status="ingestion_and_processing_started",
            deleted_events=cleanup_stats.get("deleted_events"),
            deleted_posts=cleanup_stats.get("deleted_posts"),
        )
    else:
        background_tasks.add_task(
            intelligence_service.process_pending_batch,
            db=db,
            limit=limit,
            batch_size=batch_size,
        )
        return ProcessPendingResponse(
            status="processing_started",
            deleted_events=cleanup_stats.get("deleted_events"),
            deleted_posts=cleanup_stats.get("deleted_posts"),
        )


@router.post(
    "/ingest-and-process",
    response_model=ProcessPendingResponse,
    status_code=status.HTTP_202_ACCEPTED,
    response_model_exclude_none=True,
    summary="Trigger Combined Ingestion & Batch Intelligence Processing",
)
async def ingest_and_process_posts(
    background_tasks: BackgroundTasks,
    limit: int = 100,
    batch_size: int = 5,
):
    """Explicit endpoint for running feed ingestion followed by batch processing."""
    db = get_database()
    cleanup_stats = {}
    try:
        cleanup_stats = await cleanup_stale_threats(db)
    except Exception as exc:
        logger.debug("cleanup_stale_threats in ingest_and_process skipped: %s", exc)

    try:
        pending_count = await db.raw_posts.count_documents({
            "$or": [
                {"processing_status": "pending"},
                {"status": "pending"},
            ]
        })
        if pending_count == 0:
            await unlock_ignored_posts(db, limit=50)
    except Exception as exc:
        logger.debug("Could not check pending count in ingest_and_process: %s", exc)

    background_tasks.add_task(
        _run_ingest_and_process,
        db=db,
        limit=limit,
        batch_size=batch_size,
    )
    return ProcessPendingResponse(
        status="ingestion_and_processing_started",
        deleted_events=cleanup_stats.get("deleted_events"),
        deleted_posts=cleanup_stats.get("deleted_posts"),
    )


@router.post(
    "/reprocess-all",
    response_model=ReprocessAllResponse,
    status_code=status.HTTP_200_OK,
    summary="Unlock All Ignored and Failed Posts and Re-evaluate",
)
async def reprocess_all_posts(
    background_tasks: BackgroundTasks,
    limit: int = 500,
    batch_size: int = 5,
):
    """
    Purges stale threats (from October 21st and earlier or older than retention cutoff),
    resets all remaining ignored and failed articles back to 'pending' state,
    and triggers batch intelligence processing through the latest NLP and geocoding rules.
    """
    db = get_database()
    cleanup_stats = {}
    try:
        cleanup_stats = await cleanup_stale_threats(db)
    except Exception as exc:
        logger.debug("cleanup_stale_threats in reprocess_all_posts skipped: %s", exc)

    filter_query = {
        "$or": [
            {"status": {"$in": ["ignored", "failed"]}},
            {"processing_status": {"$in": ["ignored", "failed"]}},
        ]
    }
    update_doc = {
        "$set": {
            "status": "pending",
            "processing_status": "pending",
            "updated_at": utc_now(),
        }
    }
    modified_count = 0
    try:
        result = await db.raw_posts.update_many(filter_query, update_doc)
        modified_count = getattr(result, "modified_count", 0)
        logger.info("Reprocess-all unlocked %d raw posts for re-evaluation", modified_count)
    except Exception as exc:
        logger.warning("Error running update_many in reprocess_all_posts: %s", exc)

    background_tasks.add_task(
        intelligence_service.process_pending_batch,
        db=db,
        limit=limit,
        batch_size=batch_size,
    )

    return ReprocessAllResponse(
        status="reprocessing_started",
        unlocked_count=modified_count,
        deleted_events=cleanup_stats.get("deleted_events", 0),
        deleted_posts=cleanup_stats.get("deleted_posts", 0),
    )


@router.post(
    "/cleanup-stale",
    response_model=CleanupStaleResponse,
    status_code=status.HTTP_200_OK,
    summary="Delete Stale Threats and Expired Articles",
)
async def cleanup_stale_endpoint(retention_hours: Optional[int] = None):
    """Explicitly deletes threats older than retention cutoff (e.g. 48 hours) or from October 22 and earlier."""
    db = get_database()
    result = await cleanup_stale_threats(db, retention_hours=retention_hours)
    return CleanupStaleResponse(
        status="stale_threats_cleaned",
        deleted_events=result.get("deleted_events", 0),
        deleted_posts=result.get("deleted_posts", 0),
    )


@router.post(
    "/test-event",
    response_model=EventResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Dispatch a Sample High-Severity Threat Event for Real-Time Verification",
)
async def dispatch_test_threat_event():
    """
    Creates a sample high-severity conflict event in MongoDB and broadcasts it
    directly to Redis pub/sub and connected WebSocket clients.
    Useful for instantly validating live pin drops on the Cesium 3D globe.
    """
    db = get_database()
    now = utc_now()
    repo = EventRepository(db)

    test_event = EventCreate(
        title="Air defense interception reported near Odesa",
        summary="Multiple kinetic air defense interceptions reported engaging hostile drone vectors approaching maritime infrastructure near Odesa.",
        raw_post_ids=[],
        source_ids=["liveuamap", "reuters"],
        event_type="conflict",
        entities={
            "locations": ["Odesa", "Black Sea"],
            "organizations": ["Ukrainian Air Force", "Armed Forces of Ukraine"],
            "equipment": ["Air Defense", "Shahed-136", "S-300"],
        },
        location_name="Odesa, Ukraine",
        location=GeoJSONPoint(coordinates=[30.7326, 46.4825]),
        country_code="UA",
        event_timestamp=now,
        threat_score=82.0,
        threat_level="High",
        credibility_score=88.0,
        corroboration_count=2,
        score_breakdown={
            "threat": {
                "action_score": 35.0,
                "equipment_score": 25.0,
                "location_score": 10.0,
                "frequency_score": 12.0,
                "total": 82.0,
            },
            "credibility": {
                "max_base_source_reliability": 85.0,
                "independent_source_count": 2,
                "corroboration_bonus": 3.0,
                "total": 88.0,
            },
        },
    )

    created_event = await repo.create(test_event)

    # Broadcast to WebSockets and Redis Pub/Sub
    await publish_event(created_event.model_dump(), action="created")

    return created_event
