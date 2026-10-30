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
    errors: Optional[int] = Field(default=None, description="Number of posts that failed during processing")


class ReprocessAllResponse(BaseModel):
    status: str = Field(default="reprocessing_started", description="Status of the reprocessing task")
    unlocked_count: int = Field(..., description="Number of previously filtered/failed articles unlocked")


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
    1. If pending count is 0, unlocks up to 50 ignored posts so sync always evaluates real data.
    2. Ingests all active RSS feeds to pull latest raw posts.
    3. Runs text cleaning, NER, EntityRuler, Geocoding, and Event Clustering on pending posts.
    4. Broadcasts new/updated events via WebSockets.
    5. Returns HTTP 202 Accepted immediately.
    """
    db = get_database()
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
        return ProcessPendingResponse(status="ingestion_and_processing_started")
    else:
        background_tasks.add_task(
            intelligence_service.process_pending_batch,
            db=db,
            limit=limit,
            batch_size=batch_size,
        )
        return ProcessPendingResponse(status="processing_started")


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
    return ProcessPendingResponse(status="ingestion_and_processing_started")


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
    Resets all previously ignored and failed articles back to 'pending' state
    and triggers batch intelligence processing through the latest NLP and geocoding rules.
    """
    db = get_database()
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
