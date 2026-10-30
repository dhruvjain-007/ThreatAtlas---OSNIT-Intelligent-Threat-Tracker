"""
NLP Preprocessing Module.
Provides text normalization, cleaning, and conflict keyword patterns.
"""
import re
from typing import List
from bs4 import BeautifulSoup

# High-frequency conflict and broader security terminology patterns
CONFLICT_KEYWORDS: List[str] = [
    # Explicit target terminology
    "shelling",
    "missile",
    "intercept",
    "drone",
    "patrol",
    "navy",
    "clashes",
    "border",
    "casualty",
    "ceasefire",
    "strike",
    "troops",
    # Additional kinetic, aerial, naval, and ground security keywords
    "airstrike",
    "explosion",
    "bombing",
    "offensive",
    "attack",
    "protest",
    "riot",
    "artillery",
    "tank",
    "tanks",
    "uav",
    "military",
    "combat",
    "armed",
    "warfare",
    "soldier",
    "soldiers",
    "clash",
    "casualties",
    "strikes",
    "missiles",
    "naval",
    "warship",
    "hostilities",
    "incursion",
    "ambush",
    "gunfire",
    "shootout",
    "infantry",
    "militia",
    "skirmish",
    "assault",
    "intercepted",
    "intercepting",
    "interception",
    "bombardment",
    "battalion",
    "reconnaissance",
    "airspace",
    "air defense",
    "anti-air",
    "frontline",
]

# Compiled regex matching with word boundaries (\b), ordered longest first
CONFLICT_KEYWORD_PATTERN: re.Pattern = re.compile(
    r"\b(?:" + "|".join(re.escape(kw) for kw in sorted(CONFLICT_KEYWORDS, key=len, reverse=True)) + r")\b",
    re.IGNORECASE,
)


def clean_text(text: str) -> str:
    """Normalize text by stripping HTML, URLs, and excessive whitespace."""
    if not text:
        return ""

    # Remove HTML tags
    text = BeautifulSoup(text, "html.parser").get_text(separator=" ")

    # Remove URLs
    text = re.sub(r"http[s]?://\S+", "", text)

    # Normalize whitespace
    text = re.sub(r"\s+", " ", text).strip()

    return text


def contains_conflict_keywords(text: str) -> bool:
    """Return True if text contains any recognized conflict or defensive threat keyword."""
    if not text:
        return False
    return bool(CONFLICT_KEYWORD_PATTERN.search(text))


def extract_conflict_keywords(text: str) -> List[str]:
    """Extract all unique matched conflict keywords found in text (in lowercase)."""
    if not text:
        return []
    matches = CONFLICT_KEYWORD_PATTERN.findall(text)
    return list(dict.fromkeys(m.lower() for m in matches))


def is_conflict_relevant(text: str) -> bool:
    """Determine if raw text is conflict/threat relevant based on expanded security keywords."""
    return contains_conflict_keywords(text)


__all__ = [
    "clean_text",
    "CONFLICT_KEYWORDS",
    "CONFLICT_KEYWORD_PATTERN",
    "contains_conflict_keywords",
    "extract_conflict_keywords",
    "is_conflict_relevant",
]
