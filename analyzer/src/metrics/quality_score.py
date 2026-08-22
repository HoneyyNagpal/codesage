"""
Single source of truth for turning a list of issues into a 0-100 score.
Kept separate from routes.py so it's independently testable and isn't
duplicated or drifted between endpoints.
"""
from typing import Dict, List, Any

SEVERITY_WEIGHTS = {"high": 20, "medium": 10, "low": 4}

# Security issues carry extra weight beyond their severity label, since a
# medium-severity security finding is generally worse than a medium-severity
# style finding.
CATEGORY_MULTIPLIER = {"security": 1.5}

MIN_SCORE = 10
MAX_SCORE = 100


def compute_score(issues: List[Dict[str, Any]]) -> int:
    if not issues:
        return MAX_SCORE

    deduction = 0.0
    for issue in issues:
        base = SEVERITY_WEIGHTS.get(issue.get("severity", "low"), 4)
        multiplier = CATEGORY_MULTIPLIER.get(issue.get("category", ""), 1.0)
        deduction += base * multiplier

    return max(int(MAX_SCORE - deduction), MIN_SCORE)


def summarize_by_category(issues: List[Dict[str, Any]]) -> Dict[str, int]:
    counts: Dict[str, int] = {}
    for issue in issues:
        cat = issue.get("category", "other")
        counts[cat] = counts.get(cat, 0) + 1
    return counts