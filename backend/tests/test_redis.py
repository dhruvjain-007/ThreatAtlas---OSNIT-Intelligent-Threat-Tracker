import pytest
import asyncio
from unittest.mock import AsyncMock, patch, MagicMock
from app.core.redis import listen_redis_events, get_redis_client

@pytest.mark.asyncio
async def test_redis_listener_exponential_backoff(mocker):
    # Mock redis_async.from_url to always raise an exception
    mocker.patch("app.core.redis.redis_async.from_url", side_effect=Exception("Redis down"))

    # We want to track the delays passed to asyncio.sleep
    sleep_calls = []

    async def mock_sleep(delay):
        sleep_calls.append(delay)
        if len(sleep_calls) >= 3:
            # Cancel the task to break out of the infinite loop
            raise asyncio.CancelledError()

    mocker.patch("asyncio.sleep", side_effect=mock_sleep)

    # Run the listener. It should catch the Exception 3 times, sleep, and then break on CancelledError
    await listen_redis_events()

    # Verify exponential backoff: 1.0, 2.0, 4.0
    assert sleep_calls == [1.0, 2.0, 4.0]

@pytest.mark.asyncio
async def test_redis_listener_success_resets_backoff(mocker):
    # Scenario: 
    # 1. First connection fails (delay becomes 2.0)
    # 2. Second connection succeeds (resets delay to 1.0, then we cancel to exit)
    
    call_count = 0
    
    mock_pubsub = MagicMock()
    mock_pubsub.subscribe = AsyncMock()
    # To avoid hanging in async for, make listen() return an empty async iterator
    async def empty_iterator():
        if False: yield
        raise asyncio.CancelledError() # Break out after success
        
    mock_pubsub.listen = empty_iterator
    
    mock_client = MagicMock()
    mock_client.pubsub.return_value = mock_pubsub
    mock_client.aclose = AsyncMock()

    def mock_from_url(*args, **kwargs):
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            raise Exception("Initial failure")
        return mock_client

    mocker.patch("app.core.redis.redis_async.from_url", side_effect=mock_from_url)

    sleep_calls = []
    async def mock_sleep(delay):
        sleep_calls.append(delay)

    mocker.patch("asyncio.sleep", side_effect=mock_sleep)

    await listen_redis_events()

    # The first failure caused a sleep of 1.0.
    # The second attempt succeeded, reset the delay to 1.0, then threw CancelledError to exit.
    assert sleep_calls == [1.0]

