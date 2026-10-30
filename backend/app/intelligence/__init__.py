"""
Intelligence module for duplicate detection, event clustering, threat scoring, and credibility logic.
"""

from .config import (
    ACTION_WEIGHTS,
    EQUIPMENT_WEIGHTS,
    LOCATION_SENSITIVITY_WEIGHTS,
    SOURCE_RELIABILITY_MAP,
    get_threat_level,
)
from .threat_scorer import calculate_threat_score, is_post_relevant
from .credibility_scorer import calculate_credibility_score
from .clustering import compute_similarity, find_best_matching_event, haversine_distance_km
from .service import IntelligenceService, intelligence_service
from .geocoding import COUNTRY_CENTROIDS, get_country_centroid, fallback_country_geocode
from .preprocessing import CONFLICT_KEYWORDS, is_conflict_relevant

__all__ = [
    "ACTION_WEIGHTS",
    "EQUIPMENT_WEIGHTS",
    "LOCATION_SENSITIVITY_WEIGHTS",
    "SOURCE_RELIABILITY_MAP",
    "get_threat_level",
    "calculate_threat_score",
    "is_post_relevant",
    "calculate_credibility_score",
    "compute_similarity",
    "find_best_matching_event",
    "haversine_distance_km",
    "IntelligenceService",
    "intelligence_service",
    "COUNTRY_CENTROIDS",
    "get_country_centroid",
    "fallback_country_geocode",
    "CONFLICT_KEYWORDS",
    "is_conflict_relevant",
]
