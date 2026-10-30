from typing import Dict, Tuple

# Keyword / Action severity weights (0-40 scale contribution)
ACTION_WEIGHTS: Dict[str, float] = {
    "airstrike": 35.0,
    "explosion": 30.0,
    "bombing": 30.0,
    "offensive": 25.0,
    "attack": 25.0,
    "shelling": 25.0,
    "strike": 25.0,
    "strikes": 25.0,
    "clashes": 20.0,
    "clash": 20.0,
    "combat": 20.0,
    "ambush": 25.0,
    "assault": 25.0,
    "skirmish": 20.0,
    "riot": 20.0,
    "intercept": 20.0,
    "patrol": 15.0,
    "casualty": 15.0,
    "casualties": 15.0,
    "ceasefire": 15.0,
    "border": 15.0,
    "protest": 15.0,
}
DEFAULT_ACTION_WEIGHT: float = 5.0

# Military / Security Equipment weights (0-25 scale contribution)
EQUIPMENT_WEIGHTS: Dict[str, float] = {
    "F-16": 25.0,
    "T-72": 20.0,
    "missile": 25.0,
    "missiles": 25.0,
    "artillery": 20.0,
    "tank": 15.0,
    "tanks": 15.0,
    "drone": 15.0,
    "drones": 15.0,
    "UAV": 15.0,
    "navy": 15.0,
    "naval": 15.0,
    "warship": 20.0,
    "troops": 15.0,
    "infantry": 15.0,
    "soldiers": 15.0,
    "soldier": 15.0,
}
DEFAULT_EQUIPMENT_WEIGHT: float = 5.0

# Configurable location sensitivity weights (0-20 scale contribution)
LOCATION_SENSITIVITY_WEIGHTS: Dict[str, float] = {
    "kyiv": 20.0,
    "taipei": 20.0,
    "border": 15.0,
    "capital": 20.0,
    "embassy": 15.0,
    "port": 10.0,
    "airport": 15.0,
}
DEFAULT_LOCATION_SENSITIVITY: float = 5.0  # Neutral/default value when unknown or unlisted location

# Source Reliability Configuration (0-100 base reliability)
SOURCE_RELIABILITY_MAP: Dict[str, float] = {
    "reuters": 90.0,
    "bbc": 90.0,
    "bbc world news": 90.0,
    "the guardian": 85.0,
    "the guardian world": 85.0,
    "al jazeera": 85.0,
    "al jazeera world": 85.0,
    "al jazeera english": 85.0,
    "al jazeera breaking news": 85.0,
    "un news": 85.0,
    "un news global perspective": 85.0,
    "crisiswatch international": 85.0,
    "defense one": 85.0,
    "france 24": 88.0,
    "france 24 world": 88.0,
    "defence blog": 85.0,
    "defense blog": 85.0,
    "telegram": 50.0,
    "defense news": 85.0,
    "reuters world": 90.0,
    "reliefweb crisis reports": 90.0,
    "us naval institute news": 85.0,
    "uk mod / security announcements": 90.0,
}
DEFAULT_SOURCE_RELIABILITY: float = 60.0

# Threat Level Thresholds
# Low: 0-39, Medium: 40-69, High: 70-100
THREAT_LEVEL_LOW_MAX: float = 39.0
THREAT_LEVEL_MEDIUM_MAX: float = 69.0

def get_threat_level(score: float) -> str:
    if score <= THREAT_LEVEL_LOW_MAX:
        return "Low"
    elif score <= THREAT_LEVEL_MEDIUM_MAX:
        return "Medium"
    else:
        return "High"

# Clustering Configuration Parameters
MAX_SPATIAL_DISTANCE_KM: float = 50.0
MAX_TEMPORAL_WINDOW_SECONDS: float = 86400.0  # 24 hours
MIN_CLUSTER_MATCH_SCORE: float = 0.55

# Memory Optimization: Semantic embedding model (sentence-transformers/PyTorch) takes >400MB RAM.
# Disabled by default for 512MB RAM tier (Render), falling back to high-speed Jaccard (<5MB RAM).
import os
ENABLE_SEMANTIC_EMBEDDINGS: bool = os.getenv("ENABLE_SEMANTIC_EMBEDDINGS", "false").lower() in ("true", "1", "yes")
