import pytest
import httpx
from datetime import datetime, timezone
from pydantic import ValidationError
from app.schemas.webhook import WebhookAlertCreate, WebhookAlertUpdate
from app.schemas.event import EventResponse, GeoJSONPoint
from fastapi.testclient import TestClient
from main import app
from app.services.webhook_service import (
    validate_webhook_url, SecurityValidationError, is_event_matching_webhook, dispatch_webhook, dispatch_webhooks_for_event
)

@pytest.fixture
def client():
    return TestClient(app)

@pytest.fixture
def sample_event():
    return EventResponse(
        id="111111111111111111111111",
        title="Test Event",
        summary="Test summary",
        raw_post_ids=[],
        source_ids=[],
        threat_level="High",
        threat_score=95.0,
        credibility_score=90.0,
        event_type="kinetic",
        country_code="ua",
        location=GeoJSONPoint(coordinates=[30.0, 50.0]),
        event_timestamp=datetime.now(timezone.utc),
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc)
    )

def test_schema_valid_webhook():
    w = WebhookAlertCreate(url="https://example.com/webhook", provider="discord", min_threat_level="High", countries=["UA", " RU "])
    assert w.countries == ["ua", "ru"]

def test_schema_invalid_url():
    with pytest.raises(ValidationError):
        WebhookAlertCreate(url="ftp://example.com", provider="slack")

def test_schema_invalid_bbox():
    with pytest.raises(ValidationError):
        # min_lon > max_lon
        WebhookAlertCreate(url="https://example.com", provider="generic", bbox=[[40.0, 40.0], [30.0, 50.0]])

def test_security_validation_ssrf(mocker):
    # Test valid URL
    mocker.patch("socket.getaddrinfo", return_value=[(None, None, None, None, ("8.8.8.8", 80))])
    validate_webhook_url("https://safe-domain.com")

    # Test loopback IP
    mocker.patch("socket.getaddrinfo", return_value=[(None, None, None, None, ("127.0.0.1", 80))])
    with pytest.raises(SecurityValidationError, match="non-public IP address"):
        validate_webhook_url("https://malicious.com")

    # Test metadata service IP
    mocker.patch("socket.getaddrinfo", return_value=[(None, None, None, None, ("169.254.169.254", 80))])
    with pytest.raises(SecurityValidationError, match="non-public IP address"):
        validate_webhook_url("https://cloud-metadata.internal")

@pytest.mark.asyncio
async def test_dns_rebinding_protection_at_transport(mocker, sample_event):
    """
    Ensures that the SafeNetworkBackend actually forces httpx to connect
    to the pre-validated IP, completely ignoring any secondary DNS resolution.
    """
    from app.services.webhook_service import SafeNetworkBackend, AutoBackend

    # 1. We have a webhook URL targeting 'malicious-rebind.com'
    w = WebhookAlertCreate(url="https://malicious-rebind.com", provider="generic").model_dump()
    w["is_active"] = True
    w["_id"] = "222222222222222222222222"
    w["created_at"] = datetime.now(timezone.utc)
    w["updated_at"] = datetime.now(timezone.utc)
    from app.schemas.webhook import WebhookAlertResponse
    webhook = WebhookAlertResponse(**w)

    # 2. Mock validate_webhook_url to return our safe IP ('8.8.8.8')
    mocker.patch("app.services.webhook_service.validate_webhook_url", return_value="8.8.8.8")

    # 3. We must mock the transport's actual connection at httpx level,
    # but to prove AutoBackend was used with 8.8.8.8, we can mock
    # AutoBackend.connect_tcp directly and provide a fake stream.

    class FakeStream:
        async def __aenter__(self): return self
        async def __aexit__(self, *args): pass
        def get_extra_info(self, name): return None
        async def read(self, *args, **kwargs): return b""
        async def write(self, *args, **kwargs): pass
        async def aclose(self): pass

    mock_connect = mocker.AsyncMock(return_value=FakeStream())
    mocker.patch.object(AutoBackend, "connect_tcp", mock_connect)

    # 5. Dispatch
    await dispatch_webhook(webhook, sample_event)

    # 6. Verify that the inner socket connection received "8.8.8.8" regardless of "malicious-rebind.com"
    mock_connect.assert_called_once()
    args, kwargs = mock_connect.call_args
    assert args[0] == "8.8.8.8"  # Since it's patched on the class/method, args[0] is the host if not bound

def test_matching_threat_level(sample_event):
    w = WebhookAlertCreate(url="https://x", provider="slack").model_dump()
    w["is_active"] = True
    w["_id"] = "222222222222222222222222"
    w["created_at"] = datetime.now(timezone.utc)
    w["updated_at"] = datetime.now(timezone.utc)
    from app.schemas.webhook import WebhookAlertResponse
    webhook = WebhookAlertResponse(**w)

    assert is_event_matching_webhook(sample_event, webhook, set()) == True

    sample_event.threat_level = "Medium"
    assert is_event_matching_webhook(sample_event, webhook, set()) == False

def test_matching_country(sample_event):
    w = WebhookAlertCreate(url="https://x", provider="slack", countries=["ru"]).model_dump()
    w["is_active"] = True
    w["_id"] = "222222222222222222222222"
    w["created_at"] = datetime.now(timezone.utc)
    w["updated_at"] = datetime.now(timezone.utc)
    from app.schemas.webhook import WebhookAlertResponse
    webhook = WebhookAlertResponse(**w)

    assert is_event_matching_webhook(sample_event, webhook, set()) == False  # event is UA

    webhook.countries = ["ua"]
    assert is_event_matching_webhook(sample_event, webhook, set()) == True

def test_matching_bbox(sample_event):
    w = WebhookAlertCreate(url="https://x", provider="slack", bbox=[[20.0, 40.0], [40.0, 60.0]]).model_dump()
    w["is_active"] = True
    w["_id"] = "222222222222222222222222"
    w["created_at"] = datetime.now(timezone.utc)
    w["updated_at"] = datetime.now(timezone.utc)
    from app.schemas.webhook import WebhookAlertResponse
    webhook = WebhookAlertResponse(**w)

    # Event is at 30.0, 50.0 (inside)
    assert is_event_matching_webhook(sample_event, webhook, set()) == True

    # Move event outside
    sample_event.location.coordinates = [0.0, 0.0]
    assert is_event_matching_webhook(sample_event, webhook, set()) == False

    # Missing location
    sample_event.location = None
    assert is_event_matching_webhook(sample_event, webhook, set()) == False

@pytest.mark.asyncio
async def test_dispatch_delivery_failure_isolation(mocker, sample_event):
    w = WebhookAlertCreate(url="https://safe-domain.com", provider="generic").model_dump()
    w["is_active"] = True
    w["_id"] = "222222222222222222222222"
    w["created_at"] = datetime.now(timezone.utc)
    w["updated_at"] = datetime.now(timezone.utc)
    from app.schemas.webhook import WebhookAlertResponse
    webhook = WebhookAlertResponse(**w)

    mocker.patch("app.services.webhook_service.validate_webhook_url", return_value=None)

    class MockClient:
        async def __aenter__(self): return self
        async def __aexit__(self, *args): pass
        async def post(self, *args, **kwargs):
            raise httpx.TimeoutException("Timeout")

    mocker.patch("httpx.AsyncClient", return_value=MockClient())

    # Should safely return False without raising
    result = await dispatch_webhook(webhook, sample_event)
    assert result == False

@pytest.mark.asyncio
async def test_crud_endpoints(client, mocker):
    mocker.patch("app.api.v1.endpoints.events.get_database")
    mocker.patch("app.api.v1.endpoints.webhooks.get_database")
    # Actually need a real DB or mocked repo
    # To test easily without real DB, mock the WebhookRepository
    from app.schemas.webhook import WebhookAlertResponse
    fake_webhook = WebhookAlertResponse(
        _id="333333333333333333333333",
        url="https://test.com",
        provider="discord",
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc)
    )

    mocker.patch("app.api.v1.endpoints.webhooks.WebhookRepository.create", new_callable=mocker.AsyncMock, return_value=fake_webhook)
    mocker.patch("app.api.v1.endpoints.webhooks.WebhookRepository.list_webhooks", new_callable=mocker.AsyncMock, return_value=[fake_webhook])
    mocker.patch("app.api.v1.endpoints.webhooks.WebhookRepository.delete", new_callable=mocker.AsyncMock, return_value=True)

    # Mock validate_url
    mocker.patch("app.api.v1.endpoints.webhooks.validate_webhook_url", return_value=None)

    res = client.post("/api/v1/webhooks", json={"url": "https://test.com", "provider": "discord"})
    assert res.status_code == 201

    res = client.get("/api/v1/webhooks")
    assert res.status_code == 200
    assert len(res.json()) == 1

    res = client.delete("/api/v1/webhooks/333333333333333333333333")
    assert res.status_code == 204

def test_schema_valid_polygon():
    w = WebhookAlertCreate(
        url="https://example.com",
        provider="generic",
        geometry={
            "type": "Polygon",
            "coordinates": [[[10.0, 10.0], [20.0, 10.0], [20.0, 20.0], [10.0, 20.0], [10.0, 10.0]]]
        }
    )
    assert w.geometry["type"] == "Polygon"

def test_schema_invalid_polygon():
    # Not closed
    with pytest.raises(ValueError):
        WebhookAlertCreate(
            url="https://example.com",
            provider="generic",
            geometry={
                "type": "Polygon",
                "coordinates": [[[10.0, 10.0], [20.0, 10.0], [20.0, 20.0], [10.0, 20.0]]]
            }
        )
    # Not enough points
    with pytest.raises(ValueError):
        WebhookAlertCreate(
            url="https://example.com",
            provider="generic",
            geometry={
                "type": "Polygon",
                "coordinates": [[[10.0, 10.0], [20.0, 10.0], [10.0, 10.0]]]
            }
        )
    # Invalid type
    with pytest.raises(ValueError):
        WebhookAlertCreate(
            url="https://example.com",
            provider="generic",
            geometry={
                "type": "Point",
                "coordinates": [10.0, 10.0]
            }
        )

def test_matching_polygon(sample_event):
    w_data = WebhookAlertCreate(
        url="https://x",
        provider="slack",
        geometry={
            "type": "Polygon",
            "coordinates": [[[20.0, 40.0], [40.0, 40.0], [40.0, 60.0], [20.0, 60.0], [20.0, 40.0]]]
        }
    ).model_dump()
    w_data["_id"] = "507f1f77bcf86cd799439011"
    w_data["created_at"] = sample_event.created_at
    w_data["updated_at"] = sample_event.updated_at

    from app.schemas.webhook import WebhookAlertResponse
    webhook = WebhookAlertResponse(**w_data)

    # In Python, we evaluate polygons based on intersecting_ids

    # Event inside intersecting_ids -> match
    assert is_event_matching_webhook(sample_event, webhook, {"507f1f77bcf86cd799439011"}) == True

    # Event outside intersecting_ids -> no match
    assert is_event_matching_webhook(sample_event, webhook, set()) == False
