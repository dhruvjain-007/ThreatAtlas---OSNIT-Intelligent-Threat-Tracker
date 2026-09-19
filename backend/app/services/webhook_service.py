import logging
import socket
import ipaddress
from urllib.parse import urlparse
import httpx
from typing import Optional, List, Dict, Any
from app.schemas.event import EventResponse
from app.schemas.webhook import WebhookAlertResponse
from app.db.repositories.webhook import WebhookRepository
from app.db.session import get_database

try:
    from httpcore._backends.auto import AutoBackend
except ImportError:
    # Fallback if httpcore internal paths change
    AutoBackend = None

logger = logging.getLogger("threat_atlas.webhooks")

class SecurityValidationError(Exception):
    pass

def validate_webhook_url(url: str) -> str:
    """
    Strict URL validation to prevent SSRF.
    Validates scheme and resolves hostname to ensure it's a public IP.
    """
    if not url.startswith(("http://", "https://")):
        raise SecurityValidationError("URL scheme must be http or https.")

    parsed = urlparse(url)
    hostname = parsed.hostname
    if not hostname:
        raise SecurityValidationError("URL must contain a valid hostname.")

    if parsed.username or parsed.password:
        raise SecurityValidationError("Credentials in webhook URLs are not permitted.")

    if parsed.port and parsed.port not in (80, 443):
        raise SecurityValidationError("Only ports 80 and 443 are allowed.")

    try:
        # Resolve hostname. This returns a list of (family, type, proto, canonname, sockaddr)
        addr_info = socket.getaddrinfo(hostname, parsed.port or 80)
    except socket.gaierror as e:
        raise SecurityValidationError(f"Could not resolve hostname: {str(e)}")

    for res in addr_info:
        ip = res[4][0]
        try:
            ip_obj = ipaddress.ip_address(ip)
        except ValueError:
            continue

        if ip_obj.is_private or ip_obj.is_loopback or ip_obj.is_multicast or \
           ip_obj.is_link_local or ip_obj.is_unspecified:
            raise SecurityValidationError(f"URL resolves to a non-public IP address: {ip}")

        # Return the first safe IP found
        return ip

    raise SecurityValidationError("Could not find a valid IP address.")

class SafeNetworkBackend:
    """
    A custom httpcore network backend that forces connections to a specific pre-resolved IP.
    This prevents DNS Rebinding TOCTOU SSRF vulnerabilities where httpx's internal DNS
    resolution might fetch a different IP than the one we validated.
    """
    def __init__(self, safe_ip: str):
        self.backend = AutoBackend()
        self.safe_ip = safe_ip

    async def connect_tcp(self, host: str, port: int, timeout: Optional[float] = None, local_address: Optional[str] = None, **kwargs) -> Any:
        # Override the destination host IP but leave SNI/TLS verification intact
        return await self.backend.connect_tcp(self.safe_ip, port, timeout=timeout, local_address=local_address, **kwargs)

    async def connect_unix_socket(self, *args, **kwargs) -> Any:
        return await self.backend.connect_unix_socket(*args, **kwargs)

    async def sleep(self, *args, **kwargs) -> Any:
        return await self.backend.sleep(*args, **kwargs)

def _build_discord_payload(event: EventResponse) -> dict:
    color = 15158332 if event.threat_level in ["High", "Critical"] else 16776960

    return {
        "content": f"**New {event.threat_level} Severity Threat Alert**",
        "embeds": [{
            "title": event.title,
            "description": event.summary or "No summary available",
            "color": color,
            "fields": [
                {"name": "Threat Score", "value": str(round(event.threat_score, 1)), "inline": True},
                {"name": "Credibility", "value": str(round(event.credibility_score, 1)), "inline": True},
                {"name": "Country", "value": (event.country_code.upper() if event.country_code else "Unknown"), "inline": True},
                {"name": "Location", "value": event.location_name or "Unknown", "inline": True},
                {"name": "Event Type", "value": event.event_type or "Unknown", "inline": True},
                {"name": "Timestamp", "value": event.event_timestamp.strftime('%Y-%m-%d %H:%M UTC'), "inline": True},
            ],
            "footer": {"text": f"ThreatAtlas Intelligence | Event ID: {event.id}"}
        }]
    }

def _build_slack_payload(event: EventResponse) -> dict:
    return {
        "text": f"*New {event.threat_level} Severity Threat Alert*\n*{event.title}*",
        "blocks": [
            {
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": f"{event.threat_level} Severity Threat: {event.title}"
                }
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": event.summary or "No summary available"
                }
            },
            {
                "type": "section",
                "fields": [
                    {"type": "mrkdwn", "text": f"*Threat Score:*\n{round(event.threat_score, 1)}"},
                    {"type": "mrkdwn", "text": f"*Credibility:*\n{round(event.credibility_score, 1)}"},
                    {"type": "mrkdwn", "text": f"*Country:*\n{event.country_code.upper() if event.country_code else 'Unknown'}"},
                    {"type": "mrkdwn", "text": f"*Location:*\n{event.location_name or 'Unknown'}"},
                ]
            },
            {
                "type": "context",
                "elements": [
                    {"type": "plain_text", "text": f"ThreatAtlas Intelligence | Event ID: {event.id}"}
                ]
            }
        ]
    }

def _build_generic_payload(event: EventResponse) -> dict:
    return {
        "event_id": str(event.id),
        "title": event.title,
        "summary": event.summary,
        "threat_level": event.threat_level,
        "threat_score": event.threat_score,
        "credibility_score": event.credibility_score,
        "event_type": event.event_type,
        "timestamp": event.event_timestamp.isoformat(),
        "location_name": event.location_name,
        "country_code": event.country_code,
        "coordinates": event.location.coordinates if event.location and event.location.coordinates else None
    }

def is_event_matching_webhook(event: EventResponse, webhook: WebhookAlertResponse, intersecting_ids: set) -> bool:
    """Returns True if the event satisfies the webhook's geofence and threat conditions."""
    if not webhook.is_active:
        return False

    # Threat Level Matching
    if webhook.min_threat_level in ["High", "Critical"]:
        # Only High and Critical are supported right now, and both should match High/Critical events.
        if event.threat_level not in ["High", "Critical"]:
            return False

    # Country matching
    if webhook.countries:
        if not event.country_code:
            return False
        if event.country_code.lower() not in webhook.countries:
            return False

    # Bounding Box matching
    if webhook.bbox:
        if not event.location or not event.location.coordinates or len(event.location.coordinates) < 2:
            return False

        lng = event.location.coordinates[0]
        lat = event.location.coordinates[1]

        min_lon, min_lat = webhook.bbox[0]
        max_lon, max_lat = webhook.bbox[1]

        if not (min_lon <= lng <= max_lon and min_lat <= lat <= max_lat):
            return False

    # Polygon geometry matching (MongoDB $geoIntersects evaluated in the caller)
    if webhook.geometry:
        if str(webhook.id) not in intersecting_ids:
            return False

    return True

async def dispatch_webhook(webhook: WebhookAlertResponse, event: EventResponse) -> bool:
    """Dispatches a single webhook safely without raising exceptions."""
    try:
        safe_ip = validate_webhook_url(webhook.url)
    except SecurityValidationError as e:
        logger.error(f"Webhook {webhook.id} SSRF validation failed: {e}")
        return False

    if webhook.provider == "discord":
        payload = _build_discord_payload(event)
    elif webhook.provider == "slack":
        payload = _build_slack_payload(event)
    else:
        payload = _build_generic_payload(event)

    try:
        if AutoBackend is not None:
            transport = httpx.AsyncHTTPTransport(retries=0)
            transport._pool._network_backend = SafeNetworkBackend(safe_ip)
            client_kwargs = {"transport": transport, "timeout": 3.0, "follow_redirects": False}
        else:
            client_kwargs = {"timeout": 3.0, "follow_redirects": False}

        async with httpx.AsyncClient(**client_kwargs) as client:
            response = await client.post(webhook.url, json=payload)
            response.raise_for_status()
            logger.info(f"Webhook {webhook.id} delivered successfully (Status {response.status_code})")
            return True
    except httpx.TimeoutException:
        logger.error(f"Webhook {webhook.id} delivery timed out.")
    except httpx.HTTPError as e:
        logger.error(f"Webhook {webhook.id} HTTP error: {e}")
    except Exception as e:
        logger.error(f"Webhook {webhook.id} unexpected error: {e}")

    return False

async def dispatch_webhooks_for_event(event: EventResponse) -> None:
    """
    Evaluates all active webhooks for a newly created event and dispatches them asynchronously.
    Exceptions are suppressed so this never crashes the caller pipeline.
    """
    try:
        if event.threat_level not in ["High", "Critical"]:
            return

        db = get_database()
        repo = WebhookRepository(db)

        active_webhooks = await repo.list_webhooks(active_only=True)
        if not active_webhooks:
            return

        intersecting_ids = set()
        if event.location and event.location.coordinates and len(event.location.coordinates) >= 2:
            lng = event.location.coordinates[0]
            lat = event.location.coordinates[1]

            # MongoDB $geoIntersects query
            cursor = db.webhooks.find({
                "is_active": True,
                "geometry": {
                    "$geoIntersects": {
                        "$geometry": {
                            "type": "Point",
                            "coordinates": [lng, lat]
                        }
                    }
                }
            }, {"_id": 1})

            docs = await cursor.to_list(length=1000)
            intersecting_ids = {str(doc["_id"]) for doc in docs}

        for webhook in active_webhooks:
            if is_event_matching_webhook(event, webhook, intersecting_ids):
                # We could dispatch them concurrently, but sequential awaiting in a background task
                # is fine for MVP. The outer caller runs this whole function via create_task.
                await dispatch_webhook(webhook, event)
    except Exception as e:
        logger.error(f"Error evaluating webhooks for event {event.id}: {e}", exc_info=True)
