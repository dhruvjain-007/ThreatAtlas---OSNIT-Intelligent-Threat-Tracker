import httpx
import sqlite3
import time
import os
import re
import logging
from typing import Any, Dict, List, Optional, Tuple
from app.db.session import get_database
from app.core.config import settings, ROOT_DIR

USER_AGENT = "ThreatAtlas/1.0 (Student Project)"
NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"
logger = logging.getLogger("threat_atlas.ingestion")

# Standard country centroid coordinates: (latitude, longitude, iso2_country_code)
# Focused on global crisis zones, conflict borders, and sovereign nations.
COUNTRY_CENTROIDS: Dict[str, Tuple[float, float, str]] = {
    # High-frequency conflict and crisis regions
    "lebanon": (33.8547, 35.8623, "lb"),
    "taiwan": (23.6978, 120.9605, "tw"),
    "ukraine": (48.3794, 31.1656, "ua"),
    "russia": (61.5240, 105.3188, "ru"),
    "israel": (31.0461, 34.8516, "il"),
    "palestine": (31.9522, 35.2332, "ps"),
    "gaza": (31.3547, 34.3088, "ps"),
    "west bank": (31.9522, 35.2332, "ps"),
    "syria": (34.8021, 38.9968, "sy"),
    "iran": (32.4279, 53.6880, "ir"),
    "iraq": (33.2232, 43.6793, "iq"),
    "yemen": (15.5527, 48.5164, "ye"),
    "sudan": (12.8628, 30.2176, "sd"),
    "south sudan": (6.8770, 31.3070, "ss"),
    "somalia": (5.1521, 46.1996, "so"),
    "myanmar": (21.9162, 95.9560, "mm"),
    "burma": (21.9162, 95.9560, "mm"),
    "afghanistan": (33.9391, 67.7100, "af"),
    "pakistan": (30.3753, 69.3451, "pk"),
    "india": (20.5937, 78.9629, "in"),
    "china": (35.8617, 104.1954, "cn"),
    "north korea": (40.3399, 127.5101, "kp"),
    "dprk": (40.3399, 127.5101, "kp"),
    "south korea": (35.9078, 127.7669, "kr"),
    "korea": (35.9078, 127.7669, "kr"),
    "armenia": (40.0691, 45.0382, "am"),
    "azerbaijan": (40.1431, 47.5769, "az"),
    "georgia": (42.3154, 43.3569, "ge"),
    "belarus": (53.7098, 27.9534, "by"),
    "turkey": (38.9637, 35.2433, "tr"),
    "turkiye": (38.9637, 35.2433, "tr"),
    "libya": (26.3351, 17.2283, "ly"),
    "niger": (17.6078, 8.0817, "ne"),
    "mali": (17.5707, -3.9962, "ml"),
    "burkina faso": (12.2383, -1.5616, "bf"),
    "chad": (15.4542, 18.7322, "td"),
    "ethiopia": (9.1450, 40.4897, "et"),
    "eritrea": (15.1794, 39.7823, "er"),
    "djibouti": (11.8251, 42.5903, "dj"),
    "congo": (-4.0383, 21.7587, "cd"),
    "drc": (-4.0383, 21.7587, "cd"),
    "nigeria": (9.0820, 8.6753, "ng"),
    "mozambique": (-18.6657, 35.5296, "mz"),
    "central african republic": (6.6111, 20.9394, "cf"),

    # Global and regional powers
    "united states": (37.0902, -95.7129, "us"),
    "usa": (37.0902, -95.7129, "us"),
    "united kingdom": (55.3781, -3.4360, "gb"),
    "britain": (55.3781, -3.4360, "gb"),
    "uk": (55.3781, -3.4360, "gb"),
    "france": (46.2276, 2.2137, "fr"),
    "germany": (51.1657, 10.4515, "de"),
    "poland": (51.9194, 19.1451, "pl"),
    "japan": (36.2048, 138.2529, "jp"),
    "philippines": (12.8797, 121.7740, "ph"),
    "vietnam": (14.0583, 108.2772, "vn"),
    "indonesia": (-0.7893, 113.9213, "id"),
    "malaysia": (4.2105, 101.9758, "my"),
    "australia": (-25.2744, 133.7751, "au"),
    "egypt": (26.8206, 30.8025, "eg"),
    "saudi arabia": (23.8859, 45.0792, "sa"),
    "jordan": (30.5852, 36.2384, "jo"),
    "kuwait": (29.3117, 47.4818, "kw"),
    "qatar": (25.3548, 51.1839, "qa"),
    "bahrain": (26.0667, 50.5577, "bh"),
    "united arab emirates": (23.4241, 53.8478, "ae"),
    "uae": (23.4241, 53.8478, "ae"),
    "oman": (21.5126, 55.9233, "om"),
    "cyprus": (35.1264, 33.4299, "cy"),
    "greece": (39.0742, 21.8243, "gr"),
    "italy": (41.8719, 12.5674, "it"),
    "spain": (40.4637, -3.7492, "es"),
    "canada": (56.1304, -106.3468, "ca"),
    "mexico": (23.6345, -102.5528, "mx"),
    "colombia": (4.5709, -74.2973, "co"),
    "venezuela": (6.4238, -66.5897, "ve"),
    "brazil": (-14.2350, -51.9253, "br"),
    "argentina": (-38.4161, -63.6167, "ar"),
    "sweden": (60.1282, 18.6435, "se"),
    "finland": (61.9241, 25.7482, "fi"),
    "norway": (60.4720, 8.4689, "no"),
    "estonia": (58.5953, 25.0136, "ee"),
    "latvia": (56.8796, 24.6032, "lv"),
    "lithuania": (55.1694, 23.8813, "lt"),
    "moldova": (47.4116, 28.3699, "md"),
    "romania": (45.9432, 24.9668, "ro"),
    "serbia": (44.0165, 21.0059, "rs"),
    "kosovo": (42.6026, 20.9030, "xk"),
    "kenya": (-0.0236, 37.9062, "ke"),
}

# Sub-tokens that require case-sensitive matching to avoid false positives (e.g. "us" as pronoun)
CASE_SENSITIVE_ACRONYMS: Dict[str, str] = {
    "US": "united states",
    "USA": "united states",
    "UK": "united kingdom",
    "UAE": "united arab emirates",
    "DRC": "drc",
    "DPRK": "north korea",
}

# Regex for case-insensitive country matching, excluding short 2-3 letter ambiguous acronyms
_GENERAL_COUNTRY_NAMES = [
    k for k in COUNTRY_CENTROIDS.keys()
    if k not in ("us", "uk", "drc", "uae", "dprk")
]
COUNTRY_NAME_PATTERN: re.Pattern = re.compile(
    r"\b(?:" + "|".join(re.escape(k) for k in sorted(_GENERAL_COUNTRY_NAMES, key=len, reverse=True)) + r")\b",
    re.IGNORECASE,
)


def get_country_centroid(location_name: str) -> Optional[Tuple[float, float, str]]:
    """
    Look up standard country centroid coordinates by country name or code.
    Returns (lat, lng, country_code) or None.
    """
    if not location_name:
        return None

    normalized = location_name.strip().lower()

    # Exact dictionary match
    if normalized in COUNTRY_CENTROIDS:
        return COUNTRY_CENTROIDS[normalized]

    # Check case-sensitive acronyms
    raw_stripped = location_name.strip()
    if raw_stripped in CASE_SENSITIVE_ACRONYMS:
        mapped = CASE_SENSITIVE_ACRONYMS[raw_stripped]
        return COUNTRY_CENTROIDS.get(mapped)

    return None


def find_country_in_text(text: str) -> Optional[Tuple[str, float, float, str]]:
    """
    Scans freeform text for country names or uppercase acronyms.
    Returns (display_name, lat, lng, country_code) or None.
    """
    if not text:
        return None

    # 1. Check uppercase acronyms first
    for acronym, full_key in CASE_SENSITIVE_ACRONYMS.items():
        if re.search(r"\b" + re.escape(acronym) + r"\b", text):
            lat, lng, cc = COUNTRY_CENTROIDS[full_key]
            return (acronym, lat, lng, cc)

    # 2. Check general country names (longest match first)
    match = COUNTRY_NAME_PATTERN.search(text)
    if match:
        matched_str = match.group(0).lower()
        if matched_str in COUNTRY_CENTROIDS:
            lat, lng, cc = COUNTRY_CENTROIDS[matched_str]
            return (match.group(0).title(), lat, lng, cc)

    return None


def fallback_country_geocode(doc_ents: List[Any], text: str) -> Optional[Tuple[str, float, float, str]]:
    """
    Fallback mechanism when specific city NER geocoding fails.
    First checks extracted entity mentions, then scans the raw text for country names.
    Returns (country_name, lat, lng, country_code) or None.
    """
    # 1. Check NER entities
    if doc_ents:
        for ent in doc_ents:
            ent_label = getattr(ent, "label_", "")
            ent_text = getattr(ent, "text", str(ent)).strip()
            if ent_label in ("GPE", "LOC", ""):
                centroid = get_country_centroid(ent_text)
                if centroid:
                    logger.info("Country NER entity fallback resolved '%s' to centroid %s", ent_text, centroid)
                    return (ent_text.title(), centroid[0], centroid[1], centroid[2])

    # 2. Check raw text mentions
    text_match = find_country_in_text(text)
    if text_match:
        logger.info("Country text mention fallback resolved '%s' to centroid (%.4f, %.4f)", text_match[0], text_match[1], text_match[2])
        return text_match

    return None


async def geocode(location_name: str) -> Optional[Tuple[float, float, Optional[str]]]:
    """
    Geocodes a location name to (lat, lng, country_code).
    Fallback sequence: SQLite GeoNames cache -> MongoDB geocache -> Country centroids -> Nominatim API.
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
    cache = None
    try:
        db = get_database()
        cache = db.geocache
        cached = await cache.find_one({"name": normalized_name})
        if cached:
            if cached.get("not_found"):
                centroid = get_country_centroid(normalized_name)
                if centroid:
                    return centroid
                return None
            return (cached["lat"], cached["lng"], cached.get("country_code"))
    except Exception as e:
        logger.debug("MongoDB geocache unavailable: %s", e)

    # 3. Direct Country Centroid Lookup (instant offline resolution for country-level mentions)
    centroid = get_country_centroid(normalized_name)
    if centroid:
        logger.info("Direct country centroid hit for '%s'", normalized_name)
        if cache is not None:
            try:
                await cache.insert_one({"name": normalized_name, "lat": centroid[0], "lng": centroid[1], "country_code": centroid[2]})
            except Exception:
                pass
        return centroid

    # 4. Query Nominatim
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
                if cache is not None:
                    try:
                        await cache.insert_one({"name": normalized_name, "lat": lat, "lng": lng, "country_code": country_code})
                    except Exception:
                        pass
                return (lat, lng, country_code)
            else:
                # Cache miss
                if cache is not None:
                    try:
                        await cache.insert_one({"name": normalized_name, "not_found": True})
                    except Exception:
                        pass
                return None

        except Exception as e:
            logger.warning("Geocoding error for '%s': %s", location_name, e)
            return None


__all__ = [
    "geocode",
    "COUNTRY_CENTROIDS",
    "get_country_centroid",
    "find_country_in_text",
    "fallback_country_geocode",
]
