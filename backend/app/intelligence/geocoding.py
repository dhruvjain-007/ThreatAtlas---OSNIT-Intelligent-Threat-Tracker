"""
Intelligence Geocoding Module.
Exports standard country centroid coordinates and country-level fallback detection.
"""
from app.nlp.geocoder import (
    COUNTRY_CENTROIDS,
    get_country_centroid,
    find_country_in_text,
    fallback_country_geocode,
    geocode,
)

__all__ = [
    "COUNTRY_CENTROIDS",
    "get_country_centroid",
    "find_country_in_text",
    "fallback_country_geocode",
    "geocode",
]
