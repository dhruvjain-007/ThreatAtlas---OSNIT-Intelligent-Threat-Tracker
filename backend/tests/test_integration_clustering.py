import pytest
from datetime import datetime, timezone
import numpy as np

from app.ingestion.rss_collector import RSSCollector
from app.intelligence.service import intelligence_service
from app.schemas.raw_post import RawPostResponse
from app.db.repositories.event import EventRepository
from app.schemas.event import EventResponse
from app.schemas.common import GeoJSONPoint

class MockSentenceTransformer:
    def _encode_single(self, text):
        if "explosion" in text.lower():
            return np.array([1.0, 0.0, 0.0])
        elif "humanitarian" in text.lower():
            return np.array([0.0, 1.0, 0.0])
        else:
            return np.array([0.5, 0.5, 0.5])

    def encode(self, text_or_texts):
        if isinstance(text_or_texts, str):
            return self._encode_single(text_or_texts)
        else:
            return [self._encode_single(t) for t in text_or_texts]

@pytest.fixture
def mock_semantic_model(mocker):
    return mocker.patch("app.intelligence.clustering.get_semantic_model", return_value=MockSentenceTransformer())

@pytest.fixture
def mock_geocoder(mocker):
    def fake_geocode(loc_name):
        loc = loc_name.lower()
        if "paris" in loc:
            return (48.8566, 2.3522, "fr")
        elif "lyon" in loc:
            return (45.7640, 4.8357, "fr")
        return (0.0, 0.0, "unknown")
    return mocker.patch("app.nlp.service.geocode", side_effect=fake_geocode)

class InMemoryEventRepo:
    def __init__(self):
        self.events = []
        self.counter = 1

    async def list_events(self, limit=50):
        return self.events[:limit]

    async def create(self, event_create):
        evt = EventResponse(
            id=str(self.counter),
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
            **event_create.model_dump()
        )
        self.events.append(evt)
        self.counter += 1
        return evt

    async def update(self, event_id, event_update):
        for idx, evt in enumerate(self.events):
            if evt.id == event_id:
                dump = evt.model_dump()
                dump.update(event_update.model_dump(exclude_unset=True))
                updated = EventResponse(**dump)
                self.events[idx] = updated
                return updated
        return None

@pytest.mark.asyncio
async def test_sha256_deduplication():
    collector = RSSCollector()
    
    feed_entry_1 = {
        "title": "Humanitarian crisis escalates",
        "published": "2026-09-17T10:00:00Z",
        "summary": "Reports of a severe humanitarian crisis."
    }
    feed_entry_2 = {
        "title": "Humanitarian crisis escalates",
        "published": "2026-09-17T10:00:00Z",
        "summary": "Reports of a severe humanitarian crisis."
    }
    
    res1 = collector.normalize_entry(feed_entry_1, "Mock Source")
    res2 = collector.normalize_entry(feed_entry_2, "Mock Source")
    
    assert res1.source_specific_id == res2.source_specific_id
    assert len(res1.source_specific_id) == 64  # SHA-256 length

@pytest.mark.asyncio
async def test_integration_clustering_pipeline(mock_semantic_model, mock_geocoder, mocker):
    mocker.patch("app.intelligence.service.publish_event", return_value=None)
    mocker.patch("app.intelligence.service.dispatch_webhooks_for_event", return_value=None)

    repo = InMemoryEventRepo()
    
    # 1. First payload (creates new event)
    post1 = RawPostResponse(
        id="post_1",
        source="RSS",
        source_specific_id="hash1",
        text="A massive explosion was reported in Paris today involving a T-72.",
        url="",
        original_timestamp=datetime(2026, 9, 17, 10, 0, 0, tzinfo=timezone.utc),
        processing_status="pending",
        collected_at=datetime.now(timezone.utc),
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc)
    )
    
    res1 = await intelligence_service.process_post(post1, event_repo=repo)
    
    assert res1["action"] == "created"
    evt1 = res1["event"]
    assert evt1.location_name == "Paris"
    assert evt1.location.coordinates == [2.3522, 48.8566] # lng, lat
    assert "explosion" in evt1.entities.get("event_types", []) or evt1.event_type == "explosion"
    assert "T-72" in evt1.entities.get("equipment", [])
    
    # 2. Second payload, same meaning, same place -> should cluster
    post2 = RawPostResponse(
        id="post_2",
        source="RSS",
        source_specific_id="hash2",
        text="Explosion spotted near Eiffel Tower in Paris.",
        url="",
        original_timestamp=datetime(2026, 9, 17, 10, 30, 0, tzinfo=timezone.utc),
        processing_status="pending",
        collected_at=datetime.now(timezone.utc),
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc)
    )
    
    res2 = await intelligence_service.process_post(post2, event_repo=repo)
    assert res2["action"] == "merged"
    assert res2["event_id"] == evt1.id
    
    # 3. Third payload, same meaning, but in Lyon -> should NOT cluster (Haversine threshold kicks in)
    post3 = RawPostResponse(
        id="post_3",
        source="RSS",
        source_specific_id="hash3",
        text="A massive explosion was reported in Lyon.",
        url="",
        original_timestamp=datetime(2026, 9, 17, 10, 45, 0, tzinfo=timezone.utc),
        processing_status="pending",
        collected_at=datetime.now(timezone.utc),
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc)
    )
    
    res3 = await intelligence_service.process_post(post3, event_repo=repo)
    assert res3["action"] == "created"
    assert res3["event_id"] != evt1.id
