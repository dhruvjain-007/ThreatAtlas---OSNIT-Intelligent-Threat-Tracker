from typing import Any, Dict, List, Tuple
from app.nlp.schemas import NLPResult
from app.intelligence.config import (
    ACTION_WEIGHTS,
    DEFAULT_ACTION_WEIGHT,
    EQUIPMENT_WEIGHTS,
    DEFAULT_EQUIPMENT_WEIGHT,
    LOCATION_SENSITIVITY_WEIGHTS,
    DEFAULT_LOCATION_SENSITIVITY,
    get_threat_level,
)
from app.intelligence.preprocessing import contains_conflict_keywords, extract_conflict_keywords

def calculate_threat_score(
    nlp_result: NLPResult,
    corroboration_count: int = 1,
) -> Tuple[float, str, Dict[str, Any]]:
    """
    Calculates a deterministic 0-100 threat score and breakdown.
    
    Factors:
    - Action / Event types (max 35)
    - Equipment impact (max 25)
    - Location sensitivity (max 20)
    - Frequency / Corroboration bonus (max 20)
    """
    action_score, equipment_score = _get_action_and_equipment_scores(nlp_result)

    # 3. Location Sensitivity Score
    location_score = DEFAULT_LOCATION_SENSITIVITY
    if nlp_result.locations:
        loc_scores = []
        for loc in nlp_result.locations:
            loc_name = loc.name.lower()
            # check direct match or substring in sensitivity map
            score = DEFAULT_LOCATION_SENSITIVITY
            for sens_key, sens_val in LOCATION_SENSITIVITY_WEIGHTS.items():
                if sens_key in loc_name or loc_name in sens_key:
                    score = max(score, sens_val)
            loc_scores.append(score)
        if loc_scores:
            location_score = max(loc_scores)
    location_score = min(20.0, location_score)

    # 4. Frequency / Corroboration Score
    # 1 report = 0 bonus, 2 reports = 10, 3+ reports = 20
    frequency_score = min(20.0, max(0.0, (corroboration_count - 1) * 10.0))

    # Total Score Calculation (clamped to 0.0 - 100.0)
    raw_total = action_score + equipment_score + location_score + frequency_score
    total_score = round(min(100.0, max(0.0, raw_total)), 1)
    threat_level = get_threat_level(total_score)

    breakdown = {
        "action_score": round(action_score, 1),
        "equipment_score": round(equipment_score, 1),
        "location_score": round(location_score, 1),
        "frequency_score": round(frequency_score, 1),
        "total": total_score,
    }

    return total_score, threat_level, breakdown


def _get_action_and_equipment_scores(nlp_result: NLPResult) -> Tuple[float, float]:
    """Extract action and equipment keywords and calculate their partial scores."""
    # 1. Action / Event Score
    action_score = 0.0
    found_actions = set(nlp_result.event_types)
    found_eq = set(nlp_result.equipment)
    
    # Also check text for action keywords in case NER missed explicit label
    lower_text = (nlp_result.cleaned_text or nlp_result.original_text or "").lower()
    for kw, weight in ACTION_WEIGHTS.items():
        if kw in lower_text:
            found_actions.add(kw)

    # Check equipment keywords in text
    for kw, weight in EQUIPMENT_WEIGHTS.items():
        if kw.lower() in lower_text:
            found_eq.add(kw)

    # Check extracted conflict keywords for broader coverage
    for ck in extract_conflict_keywords(lower_text):
        if ck in ACTION_WEIGHTS:
            found_actions.add(ck)
        elif ck in EQUIPMENT_WEIGHTS:
            found_eq.add(ck)
        else:
            # General security term
            found_actions.add(ck)
            
    if found_actions:
        action_score = max(ACTION_WEIGHTS.get(act.lower(), DEFAULT_ACTION_WEIGHT) for act in found_actions)
    action_score = min(35.0, action_score)

    # 2. Equipment Impact Score
    equipment_score = 0.0
    if found_eq:
        equipment_score = sum(EQUIPMENT_WEIGHTS.get(eq, DEFAULT_EQUIPMENT_WEIGHT) for eq in found_eq)
    equipment_score = min(25.0, equipment_score)

    return action_score, equipment_score


def is_post_relevant(nlp_result: NLPResult) -> bool:
    """
    Determines if a post is threat-relevant.
    A post is relevant if there is a non-zero action or equipment score,
    or if any conflict keyword patterns match the post text.
    """
    action_score, equipment_score = _get_action_and_equipment_scores(nlp_result)
    if action_score > 0 or equipment_score > 0:
        return True

    text = nlp_result.cleaned_text or nlp_result.original_text
    return contains_conflict_keywords(text)
