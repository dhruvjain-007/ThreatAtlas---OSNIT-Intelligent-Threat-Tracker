import math
import logging
from datetime import datetime
from typing import Dict, List, Optional, Set, Tuple, Any
from app.nlp.schemas import NLPResult, Location
from app.schemas.event import EventResponse
from app.intelligence.config import (
    MAX_SPATIAL_DISTANCE_KM,
    MAX_TEMPORAL_WINDOW_SECONDS,
    MIN_CLUSTER_MATCH_SCORE,
)

logger = logging.getLogger("threat_atlas.intelligence.clustering")

# Lazy loaded semantic model
_semantic_model_initialized = False
_semantic_model = None

def get_semantic_model() -> Optional[Any]:
    global _semantic_model, _semantic_model_initialized
    if not _semantic_model_initialized:
        _semantic_model_initialized = True

        from app.intelligence.config import ENABLE_SEMANTIC_EMBEDDINGS
        if not ENABLE_SEMANTIC_EMBEDDINGS:
            logger.info("Semantic embeddings disabled (ENABLE_SEMANTIC_EMBEDDINGS=False). Relying on high-speed Jaccard and spatio-temporal clustering (<5MB RAM).")
            _semantic_model = None
            return None

        try:
            from sentence_transformers import SentenceTransformer
            logger.info("Loading semantic embedding model (sentence-transformers/all-MiniLM-L6-v2)...")
            _semantic_model = SentenceTransformer('all-MiniLM-L6-v2')
        except ImportError:
            logger.warning("sentence-transformers not installed. Semantic clustering will fallback to Jaccard.")
            _semantic_model = None
        except Exception as e:
            logger.error("Failed to load semantic model: %s. Falling back to Jaccard.", e)
            _semantic_model = None
    return _semantic_model

def compute_semantic_similarity(embedding_a: Any, embedding_b: Any) -> float:
    """Compute cosine similarity between two precomputed embeddings."""
    import numpy as np
    if embedding_a is None or embedding_b is None:
        return 0.0
    try:
        # Cosine similarity
        sim = np.dot(embedding_a, embedding_b) / (np.linalg.norm(embedding_a) * np.linalg.norm(embedding_b))
        return float(max(0.0, min(1.0, sim)))
    except Exception as e:
        logger.error("Error computing semantic similarity: %s", e)
        return 0.0

def haversine_distance_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Calculate the Great-Circle distance between two points on Earth in kilometers."""
    R = 6371.0  # Earth radius in km
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat / 2) ** 2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon / 2) ** 2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return R * c

def jaccard_similarity(set_a: Set[str], set_b: Set[str]) -> float:
    """Calculate Jaccard similarity coefficient between two sets."""
    if not set_a and not set_b:
        return 0.0
    union = set_a.union(set_b)
    if not union:
        return 0.0
    intersection = set_a.intersection(set_b)
    return len(intersection) / len(union)

def extract_text_tokens(text: str) -> Set[str]:
    """Tokenize clean text into lowercased words for lightweight similarity comparison."""
    if not text:
        return set()
    words = text.lower().split()
    stop_words = {"the", "a", "an", "in", "on", "at", "and", "or", "to", "of", "for", "with", "by", "is", "are", "was", "were"}
    return {w.strip(".,!?:;\"'()") for w in words if len(w) > 2 and w not in stop_words}

def compute_similarity(
    post_text: str,
    post_time: datetime,
    post_location: Optional[Tuple[float, float]],
    post_entities: Set[str],
    post_embedding: Optional[Any],
    candidate_embedding: Optional[Any],
    event: EventResponse,
) -> float:
    """
    Compute a deterministic composite similarity match score between a post and an existing Event.
    Returns 0.0 if hard constraints fail (e.g. >50km distance or >24h time difference).
    """
    # 1. Temporal Check
    event_time = event.event_timestamp
    time_diff_seconds = abs((post_time - event_time).total_seconds())
    if time_diff_seconds > MAX_TEMPORAL_WINDOW_SECONDS:
        return 0.0
    time_score = 1.0 - (time_diff_seconds / MAX_TEMPORAL_WINDOW_SECONDS)

    # 2. Spatial / Geographic Check
    event_coords = None
    if event.location and event.location.coordinates and len(event.location.coordinates) == 2:
        # GeoJSON is [lng, lat]
        event_coords = (event.location.coordinates[1], event.location.coordinates[0])

    spatial_match = None
    if post_location and event_coords:
        dist_km = haversine_distance_km(post_location[0], post_location[1], event_coords[0], event_coords[1])
        if dist_km > MAX_SPATIAL_DISTANCE_KM:
            # Case 5 & Case 3 Hard rejection: Different locations / >50km apart MUST NOT merge
            return 0.0
        spatial_match = 1.0 - (dist_km / MAX_SPATIAL_DISTANCE_KM)

    # 3. Entity Similarity
    event_entities: Set[str] = set()
    if event.entities:
        for cat_list in event.entities.values():
            event_entities.update(item.lower() for item in cat_list)
    entity_sim = jaccard_similarity(post_entities, event_entities)

    # 4. Text Similarity (Semantic + Jaccard)
    event_text = f"{event.title} {event.summary or ''}"
    text_tokens_post = extract_text_tokens(post_text)
    text_tokens_event = extract_text_tokens(event_text)
    jaccard_sim = jaccard_similarity(text_tokens_post, text_tokens_event)

    if post_embedding is not None and candidate_embedding is not None:
        semantic_sim = compute_semantic_similarity(post_embedding, candidate_embedding)
        # Augment Jaccard: blend Semantic and Jaccard smoothly. 70/30 weighting gives priority to semantic meaning while maintaining some exact word overlap value.
        text_sim = (0.7 * semantic_sim) + (0.3 * jaccard_sim)
    else:
        text_sim = jaccard_sim

    # Composite Weighted Scoring
    if spatial_match is not None:
        score = 0.35 * spatial_match + 0.25 * time_score + 0.20 * entity_sim + 0.20 * text_sim
    else:
        score = 0.40 * time_score + 0.30 * entity_sim + 0.30 * text_sim

    return round(score, 4)

def find_best_matching_event(
    post_text: str,
    post_time: datetime,
    nlp_result: NLPResult,
    candidate_events: List[EventResponse],
) -> Optional[Tuple[EventResponse, float]]:
    """
    Find the best matching candidate event for a given post and NLP result.
    Returns (best_event, score) if score >= MIN_CLUSTER_MATCH_SCORE, else None.
    """
    if not candidate_events:
        return None

    # Determine post primary location coords
    post_location: Optional[Tuple[float, float]] = None
    if nlp_result.locations:
        for loc in nlp_result.locations:
            if loc.confidence != "unknown" and (loc.lat != 0.0 or loc.lng != 0.0):
                post_location = (loc.lat, loc.lng)
                break

    # Gather all post extracted entity strings
    post_entities: Set[str] = set()
    post_entities.update(eq.lower() for eq in nlp_result.equipment)
    post_entities.update(ev.lower() for ev in nlp_result.event_types)
    post_entities.update(org.lower() for org in nlp_result.organizations)
    post_entities.update(loc.name.lower() for loc in nlp_result.locations)

    # Encode texts using model batching
    post_embedding = None
    candidate_embeddings = [None] * len(candidate_events)
    model = get_semantic_model()

    if model is not None:
        try:
            # 1. Encode incoming post
            post_embedding = model.encode(post_text)

            # 2. Extract and batch encode candidate texts
            candidate_texts = [f"{e.title} {e.summary or ''}" for e in candidate_events]
            candidate_embeddings = model.encode(candidate_texts)
        except Exception as e:
            logger.error("Failed to encode text for semantic clustering: %s", e)
            post_embedding = None
            candidate_embeddings = [None] * len(candidate_events)

    best_match: Optional[EventResponse] = None
    highest_score: float = 0.0

    for idx, event in enumerate(candidate_events):
        score = compute_similarity(
            post_text=post_text,
            post_time=post_time,
            post_location=post_location,
            post_entities=post_entities,
            post_embedding=post_embedding,
            candidate_embedding=candidate_embeddings[idx],
            event=event
        )
        if score > highest_score:
            highest_score = score
            best_match = event

    if best_match and highest_score >= MIN_CLUSTER_MATCH_SCORE:
        return (best_match, highest_score)
    return None
