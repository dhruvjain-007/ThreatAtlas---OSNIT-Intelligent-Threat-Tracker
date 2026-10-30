import logging
import asyncio
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.events import EVENT_JOB_ERROR, EVENT_JOB_EXECUTED
from apscheduler.jobstores.base import ConflictingIdError
from app.db.session import get_database
from app.ingestion.service import IngestionService
from app.intelligence.service import intelligence_service
from app.core.config import settings

logger = logging.getLogger("threat_atlas.worker")

# We keep a module-level instance of the scheduler
scheduler = AsyncIOScheduler()

async def scheduled_ingestion_and_processing_job():
    """
    The background job that runs ingestion and intelligence processing.
    """
    logger.info("Scheduled ingestion job started")

    try:
        db = get_database()

        # 1. Clean up stale/non-existent threats
        try:
            from app.api.v1.endpoints.intelligence import cleanup_stale_threats
            await cleanup_stale_threats(db)
        except Exception as exc:
            logger.debug("cleanup_stale_threats skipped in worker: %s", exc)

        # 2. Ingest all configured feeds
        ingestion_service = IngestionService(db)
        ingest_stats = await ingestion_service.ingest_all_feeds()
        logger.info(
            "Scheduled ingestion completed: %d attempted, %d succeeded, %d failed.",
            ingest_stats.feeds_attempted,
            ingest_stats.feeds_succeeded,
            ingest_stats.feeds_failed,
        )

        # 2. Process pending intelligence posts
        process_stats = await intelligence_service.process_pending_batch(db=db, limit=500)
        logger.info(
            "Scheduled intelligence processing completed: %d processed, %d created, %d merged, %d ignored, %d errors.",
            process_stats.get("processed_count", 0),
            process_stats.get("events_created", 0),
            process_stats.get("events_merged", 0),
            process_stats.get("events_ignored", 0),
            process_stats.get("errors", 0),
        )

    except Exception as exc:
        logger.error("Scheduled ingestion job failed: %s", str(exc), exc_info=True)


def start_scheduler():
    """
    Start the APScheduler for background jobs.
    Called during FastAPI lifespan startup after DB initialization.
    """
    interval_minutes = 15

    try:
        scheduler.add_job(
            scheduled_ingestion_and_processing_job,
            "interval",
            minutes=interval_minutes,
            id="threat_atlas_ingestion_job",
            max_instances=1,  # Prevent overlapping executions
            replace_existing=True,
            misfire_grace_time=300,  # 5 minutes
            coalesce=True,  # Roll multiple misfires into a single execution
        )
        logger.info(f"Registered ingestion job to run every {interval_minutes} minutes.")
    except ConflictingIdError:
        logger.warning("Job already exists, skipping addition.")

    scheduler.start()
    logger.info("APScheduler started successfully.")

def stop_scheduler():
    """
    Stop the APScheduler gracefully.
    Called during FastAPI lifespan shutdown.
    """
    if scheduler.running:
        scheduler.shutdown(wait=True)
        logger.info("APScheduler stopped gracefully.")
