import logging
from typing import Optional
from pydantic import BaseModel, Field
from fastapi import APIRouter, BackgroundTasks, status
from app.db.session import get_database
from app.intelligence.service import intelligence_service

logger = logging.getLogger("threat_atlas.api.intelligence")

router = APIRouter()


class ProcessPendingResponse(BaseModel):
    status: str = Field(default="processing_started", description="Status of the background processing task")
    processed_count: Optional[int] = Field(default=None, description="Number of raw posts processed")
    events_created: Optional[int] = Field(default=None, description="Number of new events created")
    events_merged: Optional[int] = Field(default=None, description="Number of posts merged into existing events")
    events_ignored: Optional[int] = Field(default=None, description="Number of posts ignored because they were not threat-relevant")
    errors: Optional[int] = Field(default=None, description="Number of posts that failed during processing")


@router.post(
    "/process-pending",
    response_model=ProcessPendingResponse,
    status_code=status.HTTP_202_ACCEPTED,
    response_model_exclude_none=True,
    summary="Trigger Batch NLP & Intelligence Processing",
)
async def process_pending_posts(
    background_tasks: BackgroundTasks,
    limit: int = 100,
    batch_size: int = 5,
):
    """
    Executes the end-to-end processing pipeline on pending RawPosts asynchronously in the background:
    1. Queues background task processing items in small chunks (default batch size = 5).
    2. Runs text cleaning, NER, EntityRuler, and Geocoding via NLPService.
    3. Runs Threat Scoring, Credibility Scoring, and Event Clustering via IntelligenceService.
    4. Runs garbage collection after each batch chunk to maintain a low RAM footprint on 512MB tiers.
    5. Returns HTTP 202 Accepted immediately to prevent timeout errors (502 Bad Gateway) on Render.
    """
    db = get_database()
    background_tasks.add_task(
        intelligence_service.process_pending_batch,
        db=db,
        limit=limit,
        batch_size=batch_size,
    )
    return ProcessPendingResponse(status="processing_started")

