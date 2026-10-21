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
    events_created: Optional[int] = Field(default=None, description="Number of new events created")
    events_merged: Optional[int] = Field(default=None, description="Number of posts merged into existing events")
    events_ignored: Optional[int] = Field(default=None, description="Number of posts ignored because they were not threat-relevant")
    errors: Optional[int] = Field(default=None, description="Number of posts that failed during processing")


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
        process_stats = await intelligence_service.process_pending_batch(
            db=db,
            limit=limit,
            batch_size=batch_size,
        )
        logger.info(
            "Background intelligence processing finished: processed=%d, created=%d, merged=%d",
            process_stats.get("processed_count", 0),
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
    1. Ingests all active RSS feeds to pull latest raw posts.
    2. Runs text cleaning, NER, EntityRuler, Geocoding, and Event Clustering on pending posts.
    3. Broadcasts new/updated events via WebSockets.
    4. Returns HTTP 202 Accepted immediately.
    """
    db = get_database()
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
    background_tasks.add_task(
        _run_ingest_and_process,
        db=db,
        limit=limit,
        batch_size=batch_size,
    )
    return ProcessPendingResponse(status="ingestion_and_processing_started")


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


