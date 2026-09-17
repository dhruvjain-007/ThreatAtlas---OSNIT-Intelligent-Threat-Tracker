import pytest
import datetime
from unittest.mock import AsyncMock, patch, MagicMock
from app.intelligence.service import intelligence_service
from app.schemas.raw_post import RawPostResponse
from app.nlp.schemas import NLPResult, Location

@pytest.fixture
def base_post():
    return RawPostResponse(
        id="post1",
        source="telegram",
        source_specific_id="123",
        text="A new event happened.",
        original_timestamp=datetime.datetime(2023, 1, 1, 12, 0, tzinfo=datetime.timezone.utc),
        collected_at=datetime.datetime(2023, 1, 1, 12, 1, tzinfo=datetime.timezone.utc),
        processing_status="pending",
        created_at=datetime.datetime(2023, 1, 1, 12, 5, tzinfo=datetime.timezone.utc),
        updated_at=datetime.datetime(2023, 1, 1, 12, 5, tzinfo=datetime.timezone.utc),
    )

@pytest.mark.asyncio
async def test_process_post_uses_temporal_fallback_without_location(base_post):
    mock_event_repo = AsyncMock()
    mock_event_repo.list_events.return_value = []
    
    nlp_res = NLPResult(
        original_text=base_post.text,
        cleaned_text=base_post.text,
        entities=[],
        locations=[],
        organizations=[],
        equipment=[],
        event_types=[],
    )
    
    with patch("app.intelligence.service.find_best_matching_event", return_value=None):
        await intelligence_service.process_post(
            raw_post=base_post,
            event_repo=mock_event_repo,
            nlp_result=nlp_res,
        )
        
    mock_event_repo.list_events.assert_called_once()
    kwargs = mock_event_repo.list_events.call_args.kwargs
    assert kwargs.get("limit") == 50
    assert kwargs.get("start_date") == base_post.original_timestamp - datetime.timedelta(seconds=86400)
    assert kwargs.get("end_date") == base_post.original_timestamp + datetime.timedelta(seconds=86400)
    assert kwargs.get("bbox") is None

@pytest.mark.asyncio
async def test_process_post_uses_bbox_with_location(base_post):
    mock_event_repo = AsyncMock()
    mock_event_repo.list_events.return_value = []
    
    nlp_res = NLPResult(
        original_text=base_post.text,
        cleaned_text=base_post.text,
        entities=[],
        locations=[Location(name="Kyiv", lat=50.45, lng=30.52, confidence="high")],
        organizations=[],
        equipment=[],
        event_types=[],
    )
    
    with patch("app.intelligence.service.find_best_matching_event", return_value=None):
        await intelligence_service.process_post(
            raw_post=base_post,
            event_repo=mock_event_repo,
            nlp_result=nlp_res,
        )
        
    mock_event_repo.list_events.assert_called_once()
    kwargs = mock_event_repo.list_events.call_args.kwargs
    assert kwargs.get("limit") == 50
    assert kwargs.get("start_date") == base_post.original_timestamp - datetime.timedelta(seconds=86400)
    assert kwargs.get("end_date") == base_post.original_timestamp + datetime.timedelta(seconds=86400)
    
    bbox = kwargs.get("bbox")
    assert bbox is not None
    assert len(bbox) == 4
    min_lon, min_lat, max_lon, max_lat = bbox
    assert min_lon < 30.52 < max_lon
    assert min_lat < 50.45 < max_lat

@pytest.mark.asyncio
async def test_process_post_handles_empty_candidates(base_post):
    mock_event_repo = AsyncMock()
    # Empty candidates should not break anything
    mock_event_repo.list_events.return_value = []
    
    nlp_res = NLPResult(
        original_text=base_post.text,
        cleaned_text=base_post.text,
        entities=[],
        locations=[],
        organizations=[],
        equipment=[],
        event_types=[],
    )
    
    with patch("app.intelligence.service.find_best_matching_event", return_value=None):
        result = await intelligence_service.process_post(
            raw_post=base_post,
            event_repo=mock_event_repo,
            nlp_result=nlp_res,
        )
        
    assert result["action"] == "created"
