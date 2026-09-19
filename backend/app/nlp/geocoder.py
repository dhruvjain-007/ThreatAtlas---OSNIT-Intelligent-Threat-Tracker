import httpx
import sqlite3
import time
import os
import logging
from typing import Optional, Tuple
from app.db.session import get_database
from app.core.config import settings, ROOT_DIR

USER_AGENT = "ThreatAtlas/1.0 (Student Project)"
NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"
logger = logging.getLogger("threat_atlas.ingestion")

async def geocode(location_name: str) -> Optional[Tuple[float, float, Optional[str]]]:
    """
    Geocodes a location name to (lat, lng, country_code).
    Fallback sequence: SQLite GeoNames cache -> MongoDB geocache -> Nominatim API.
    Returns (lat, lng, country_code) or None if not found.
    """
    if not location_name:
        return None

    normalized_name = location_name.strip().lower()

    # 1. Check Offline SQLite GeoNames Cache
    db_path = os.path.join(ROOT_DIR, settings.GEONAMES_DB_PATH)
    if os.path.exists(db_path):
        try:
            start_time = time.perf_counter()
            with sqlite3.connect(db_path) as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT lat, lng, country_code FROM geonames WHERE LOWER(name) = ? LIMIT 1",
                    (normalized_name,)
                )
                row = cursor.fetchone()

            elapsed_ms = (time.perf_counter() - start_time) * 1000.0

            if row:
                logger.info("SQLite GeoNames hit for '%s' in %.2fms", normalized_name, elapsed_ms)
                return (float(row[0]), float(row[1]), row[2])
            else:
                logger.debug("SQLite GeoNames miss for '%s' in %.2fms", normalized_name, elapsed_ms)
        except Exception as e:
            logger.warning("SQLite GeoNames cache error for '%s': %s", normalized_name, e)

    # 2. Check MongoDB Cache
    db = get_database()
    cache = db.geocache
    cached = await cache.find_one({"name": normalized_name})
    if cached:
        if cached.get("not_found"):
            return None
        return (cached["lat"], cached["lng"], cached.get("country_code"))

    # 3. Query Nominatim
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(
                NOMINATIM_URL,
                params={"q": location_name, "format": "json", "limit": 1, "addressdetails": 1},
                headers={"User-Agent": USER_AGENT},
                timeout=5.0
            )
            response.raise_for_status()
            data = response.json()

            if data and len(data) > 0:
                lat = float(data[0]["lat"])
                lng = float(data[0]["lon"])

                # Extract country code
                country_code = data[0].get("address", {}).get("country_code")
                if country_code:
                    country_code = country_code.lower()

                # Save to cache
                await cache.insert_one({"name": normalized_name, "lat": lat, "lng": lng, "country_code": country_code})
                return (lat, lng, country_code)
            else:
                # Cache miss
                await cache.insert_one({"name": normalized_name, "not_found": True})
                return None

        except Exception as e:
            # On error, fail gracefully and don't cache
            print(f"Geocoding error for '{location_name}': {e}")
            return None
