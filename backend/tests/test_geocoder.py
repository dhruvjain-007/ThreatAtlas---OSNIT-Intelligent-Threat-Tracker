import pytest
from app.nlp.geocoder import geocode

@pytest.mark.asyncio
async def test_geocode_success_with_country(mocker):
    # Mock httpx.AsyncClient.get
    mock_response = mocker.Mock()
    mock_response.raise_for_status = mocker.Mock()
    mock_response.json.return_value = [
        {
            "lat": "48.8566",
            "lon": "2.3522",
            "address": {
                "country_code": "FR"
            }
        }
    ]

    mock_client_instance = mocker.Mock()
    mock_client_instance.get = mocker.AsyncMock(return_value=mock_response)

    # httpx.AsyncClient is an async context manager
    mock_client_instance.__aenter__ = mocker.AsyncMock(return_value=mock_client_instance)
    mock_client_instance.__aexit__ = mocker.AsyncMock(return_value=None)

    mocker.patch("httpx.AsyncClient", return_value=mock_client_instance)

    # Mock DB cache miss
    mock_db = mocker.patch("app.nlp.geocoder.get_database")
    mock_cache = mocker.Mock()
    mock_cache.find_one = mocker.AsyncMock(return_value=None)
    mock_cache.insert_one = mocker.AsyncMock()
    mock_db.return_value.geocache = mock_cache

    res = await geocode("Paris")
    assert res is not None
    lat, lng, cc = res
    assert lat == 48.8566
    assert lng == 2.3522
    assert cc == "fr"  # lowercased

@pytest.mark.asyncio
async def test_geocode_success_without_country(mocker):
    # Mock httpx.AsyncClient.get
    mock_response = mocker.Mock()
    mock_response.raise_for_status = mocker.Mock()
    mock_response.json.return_value = [
        {
            "lat": "48.8566",
            "lon": "2.3522"
        }
    ]

    mock_client_instance = mocker.Mock()
    mock_client_instance.get = mocker.AsyncMock(return_value=mock_response)
    mock_client_instance.__aenter__ = mocker.AsyncMock(return_value=mock_client_instance)
    mock_client_instance.__aexit__ = mocker.AsyncMock(return_value=None)

    mocker.patch("httpx.AsyncClient", return_value=mock_client_instance)

    # Mock DB cache miss
    mock_db = mocker.patch("app.nlp.geocoder.get_database")
    mock_cache = mocker.Mock()
    mock_cache.find_one = mocker.AsyncMock(return_value=None)
    mock_cache.insert_one = mocker.AsyncMock()
    mock_db.return_value.geocache = mock_cache

    res = await geocode("Somewhere")
    assert res is not None
    lat, lng, cc = res
    assert lat == 48.8566
    assert lng == 2.3522
    assert cc is None

@pytest.mark.asyncio
async def test_geocode_sqlite_hit(mocker):
    # Mock settings.GEONAMES_DB_PATH to something that exists
    mocker.patch("os.path.exists", return_value=True)

    mock_conn = mocker.Mock()
    mock_cursor = mocker.Mock()
    # Return a mocked row (lat, lng, country_code)
    mock_cursor.fetchone.return_value = (51.5074, -0.1278, "gb")
    mock_conn.cursor.return_value = mock_cursor

    mock_sqlite_connect = mocker.patch("sqlite3.connect")
    mock_sqlite_connect.return_value.__enter__.return_value = mock_conn

    res = await geocode("London")
    assert res is not None
    lat, lng, cc = res
    assert lat == 51.5074
    assert lng == -0.1278
    assert cc == "gb"
    mock_sqlite_connect.assert_called_once()
    mock_cursor.execute.assert_called_once()

@pytest.mark.asyncio
async def test_geocode_sqlite_miss_fallback_to_mongo(mocker):
    mocker.patch("os.path.exists", return_value=True)

    mock_conn = mocker.Mock()
    mock_cursor = mocker.Mock()
    mock_cursor.fetchone.return_value = None  # Miss
    mock_conn.cursor.return_value = mock_cursor

    mocker.patch("sqlite3.connect").return_value.__enter__.return_value = mock_conn

    # Mock DB cache hit
    mock_db = mocker.patch("app.nlp.geocoder.get_database")
    mock_cache = mocker.Mock()
    mock_cache.find_one = mocker.AsyncMock(return_value={"lat": 40.7128, "lng": -74.0060, "country_code": "us"})
    mock_db.return_value.geocache = mock_cache

    res = await geocode("New York")
    assert res is not None
    lat, lng, cc = res
    assert lat == 40.7128
    assert lng == -74.0060
    assert cc == "us"

@pytest.mark.asyncio
async def test_geocode_sqlite_missing_db(mocker):
    mocker.patch("os.path.exists", return_value=False)

    mock_sqlite_connect = mocker.patch("sqlite3.connect")

    # Mock DB cache hit
    mock_db = mocker.patch("app.nlp.geocoder.get_database")
    mock_cache = mocker.Mock()
    mock_cache.find_one = mocker.AsyncMock(return_value={"lat": 40.7128, "lng": -74.0060, "country_code": "us"})
    mock_db.return_value.geocache = mock_cache

    res = await geocode("New York")
    assert res is not None
    mock_sqlite_connect.assert_not_called()
