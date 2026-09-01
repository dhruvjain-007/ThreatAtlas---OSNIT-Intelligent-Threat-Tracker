from datetime import datetime
from typing import List, Optional
from bson import ObjectId
from fastapi import APIRouter, HTTPException, Query, status
from app.db.session import get_database
from app.db.repositories.event import EventRepository
from app.db.repositories.raw_post import RawPostRepository
from app.schemas.event import EventListResponse, EventResponse, EventGlobalMetrics
from app.schemas.raw_post import RawPostResponse

router = APIRouter()


def parse_and_validate_bbox(bbox_str: Optional[str]) -> Optional[List[float]]:
    """Parse comma-separated bbox string 'min_lon,min_lat,max_lon,max_lat' into float list."""
    if not bbox_str:
        return None
    try:
        parts = [float(p.strip()) for p in bbox_str.split(",")]
        if len(parts) != 4:
            raise ValueError("Must contain 4 coordinates.")
        min_lon, min_lat, max_lon, max_lat = parts
        if not (-180.0 <= min_lon <= 180.0 and -180.0 <= max_lon <= 180.0):
            raise ValueError("Longitude must be between -180 and 180.")
        if not (-90.0 <= min_lat <= 90.0 and -90.0 <= max_lat <= 90.0):
            raise ValueError("Latitude must be between -90 and 90.")
        if min_lon > max_lon or min_lat > max_lat:
            raise ValueError("min coordinates cannot be greater than max coordinates.")
        return parts
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid bbox parameter. Expected format 'min_lon,min_lat,max_lon,max_lat'. Reason: {exc}",
        )


@router.get("", response_model=EventListResponse, summary="List & Filter Intelligence Events")
async def list_events(
    limit: int = Query(default=50, ge=1, le=10000, description="Page limit (1-10000)"),
    skip: int = Query(default=0, ge=0, description="Page skip offset"),
    threat_level: Optional[str] = Query(default=None, description="Filter by threat level: Low, Medium, High"),
    min_threat_score: Optional[float] = Query(default=None, ge=0.0, le=100.0, description="Minimum threat score"),
    event_type: Optional[str] = Query(default=None, description="Filter by event category"),
    start_date: Optional[datetime] = Query(default=None, description="Start date (UTC ISO)"),
    end_date: Optional[datetime] = Query(default=None, description="End date (UTC ISO)"),
    bbox: Optional[str] = Query(default=None, description="Geospatial bounding box 'min_lon,min_lat,max_lon,max_lat'"),
    search: Optional[str] = Query(default=None, description="Text search in title or summary"),
    countries: Optional[str] = Query(default=None, description="Comma-separated ISO country codes (e.g. ua,ru)"),
):
    """Retrieve intelligence events with rich filtering, text search, geospatial bounding box, and pagination."""
    if threat_level and threat_level not in {"Low", "Medium", "High"}:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid threat_level value. Allowed values: Low, Medium, High.",
        )

    parsed_bbox = parse_and_validate_bbox(bbox)

    parsed_countries = None
    if countries:
        parsed_countries = list({c.strip().lower() for c in countries.split(",") if c.strip()})
        if not parsed_countries:
            parsed_countries = None

    db = get_database()
    event_repo = EventRepository(db)

    events = await event_repo.list_events(
        limit=limit,
        skip=skip,
        threat_level=threat_level,
        min_threat_score=min_threat_score,
        event_type=event_type,
        start_date=start_date,
        end_date=end_date,
        bbox=parsed_bbox,
        search=search,
        countries=parsed_countries,
    )
    total = await event_repo.count_events(
        threat_level=threat_level,
        min_threat_score=min_threat_score,
        event_type=event_type,
        start_date=start_date,
        end_date=end_date,
        bbox=parsed_bbox,
        search=search,
        countries=parsed_countries,
    )

    return EventListResponse(total=total, limit=limit, skip=skip, items=events)


@router.get("/export", summary="Export Events to PDF or STIX")
async def export_events(
    format: str = Query(..., description="Export format: 'pdf' or 'stix'"),
    threat_level: Optional[str] = Query(default=None, description="Filter by threat level: Low, Medium, High"),
    min_threat_score: Optional[float] = Query(default=None, ge=0.0, le=100.0, description="Minimum threat score"),
    event_type: Optional[str] = Query(default=None, description="Filter by event category"),
    start_date: Optional[datetime] = Query(default=None, description="Start date (UTC ISO)"),
    end_date: Optional[datetime] = Query(default=None, description="End date (UTC ISO)"),
    bbox: Optional[str] = Query(default=None, description="Geospatial bounding box 'min_lon,min_lat,max_lon,max_lat'"),
    search: Optional[str] = Query(default=None, description="Text search in title or summary"),
    countries: Optional[str] = Query(default=None, description="Comma-separated ISO country codes (e.g. ua,ru)"),
):
    """Export filtered intelligence events to PDF or STIX 2.1 format."""
    if format not in {"pdf", "stix"}:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Unsupported export format. Use 'pdf' or 'stix'."
        )

    if threat_level and threat_level not in {"Low", "Medium", "High"}:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid threat_level value. Allowed values: Low, Medium, High.",
        )

    parsed_bbox = parse_and_validate_bbox(bbox)

    parsed_countries = None
    if countries:
        parsed_countries = list({c.strip().lower() for c in countries.split(",") if c.strip()})
        if not parsed_countries:
            parsed_countries = None

    db = get_database()
    event_repo = EventRepository(db)

    # Use a safe absolute limit to prevent OOM
    events = await event_repo.list_events(
        limit=10000,
        skip=0,
        threat_level=threat_level,
        min_threat_score=min_threat_score,
        event_type=event_type,
        start_date=start_date,
        end_date=end_date,
        bbox=parsed_bbox,
        search=search,
        countries=parsed_countries,
    )

    from app.intelligence.export_service import generate_pdf, generate_stix_bundle
    from fastapi.responses import StreamingResponse
    import io

    if format == "pdf":
        pdf_bytes = generate_pdf(events)
        return StreamingResponse(
            io.BytesIO(pdf_bytes),
            media_type="application/pdf",
            headers={"Content-Disposition": 'attachment; filename="threatatlas_export.pdf"'}
        )
    else:
        stix_bytes = generate_stix_bundle(events)
        return StreamingResponse(
            io.BytesIO(stix_bytes),
            media_type="application/stix+json",
            headers={"Content-Disposition": 'attachment; filename="threatatlas_export.json"'}
        )


@router.get("/stats", response_model=EventGlobalMetrics, summary="Get Global Event Metrics")
async def get_global_metrics():
    """Retrieve global un-filtered counts for Total, High, Medium, and Low threat events."""
    db = get_database()
    event_repo = EventRepository(db)
    return await event_repo.get_global_metrics()


@router.get("/countries", response_model=List[str], summary="Get Available Countries")
async def get_countries():
    """Retrieve list of distinct country codes present in events."""
    db = get_database()
    event_repo = EventRepository(db)
    return await event_repo.get_distinct_countries()


@router.get("/{id}", response_model=EventResponse, summary="Get Single Intelligence Event")
async def get_event(id: str):
    """Retrieve detailed single event including threat breakdown, credibility, and entities."""
    if not ObjectId.is_valid(id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid Event ID format: '{id}'. Must be a valid 24-character hex string.",
        )

    db = get_database()
    event_repo = EventRepository(db)
    event = await event_repo.get_by_id(id)

    if not event:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Intelligence Event with ID '{id}' not found.",
        )
    return event


@router.get("/{id}/sources", response_model=List[RawPostResponse], summary="Get Contributing Raw Posts for Event")
async def get_event_sources(id: str):
    """Retrieve all RawPost documents that contributed to this intelligence event."""
    if not ObjectId.is_valid(id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid Event ID format: '{id}'. Must be a valid 24-character hex string.",
        )

    db = get_database()
    event_repo = EventRepository(db)
    raw_post_repo = RawPostRepository(db)

    event = await event_repo.get_by_id(id)
    if not event:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Intelligence Event with ID '{id}' not found.",
        )

    if not event.raw_post_ids:
        return []

    return await raw_post_repo.get_by_ids(event.raw_post_ids)
