import asyncio
import json
import logging
from typing import Any, Dict, Optional
import redis.asyncio as redis_async
from app.core.config import settings
from app.websockets.manager import ws_manager

logger = logging.getLogger("threat_atlas.redis")

REDIS_CHANNEL = "events_channel"
redis_client: Optional[redis_async.Redis] = None


async def get_redis_client() -> Optional[redis_async.Redis]:
    """Get or initialize async Redis client."""
    global redis_client
    if redis_client is None:
        try:
            redis_client = redis_async.from_url(
                settings.REDIS_URL,
                encoding="utf-8",
                decode_responses=True,
                socket_timeout=3.0,
            )
        except Exception as exc:
            logger.warning("Redis initialization notice: %s. Continuing with in-memory WS broadcast.", exc)
            return None
    return redis_client


async def publish_event(event_data: Dict[str, Any], action: str = "created") -> None:
    """
    Publish event update to Redis channel and broadcast directly via WebSocket manager.
    action: 'created' | 'merged' | 'updated'
    """
    event_type = f"EVENT_{action.upper()}"
    payload = {
        "type": event_type,
        "action": action,
        "event": event_data,
    }

    # 1. Direct in-memory WS broadcast (guarantees local delivery)
    await ws_manager.broadcast_json(payload)

    # 2. Redis Pub/Sub broadcast for multi-worker synchronization
    try:
        r = await get_redis_client()
        if r:
            await r.publish(REDIS_CHANNEL, json.dumps(payload))
            logger.info("Published %s to Redis channel '%s'", event_type, REDIS_CHANNEL)
    except Exception as exc:
        logger.debug("Redis publish notice: %s", exc)


async def listen_redis_events() -> None:
    """Background task listening to Redis Pub/Sub channel and forwarding to WebSockets."""
    while True:
        try:
            # Dedicated pubsub client with no socket timeout for idle connections
            pubsub_client = redis_async.from_url(
                settings.REDIS_URL,
                encoding="utf-8",
                decode_responses=True,
            )
            pubsub = pubsub_client.pubsub()
            await pubsub.subscribe(REDIS_CHANNEL)
            logger.info("Subscribed to Redis Pub/Sub channel '%s'", REDIS_CHANNEL)

            async for message in pubsub.listen():
                if message and message.get("type") == "message":
                    data_str = message.get("data")
                    if data_str:
                        try:
                            data = json.loads(data_str)
                            await ws_manager.broadcast_json(data)
                        except Exception as parse_err:
                            logger.warning("Error parsing Redis message payload: %s", parse_err)
        
        except asyncio.CancelledError:
            logger.info("Redis Pub/Sub listener task cancelled.")
            break
        except Exception as exc:
            logger.warning("Redis Pub/Sub listener error: %s. Retrying in 5 seconds...", exc)
            await asyncio.sleep(5)
        finally:
            if 'pubsub_client' in locals():
                await pubsub_client.close()
