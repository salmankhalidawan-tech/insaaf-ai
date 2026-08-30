"""
Semantic auto-detection for positive outcome values and privileged values.

Replaces the naive mode()-based default that silently picks whichever value
is most frequent — a problem on biased datasets where "rejected" may
outnumber "approved" and the pipeline ends up treating rejection as the
positive outcome, inverting every metric.
"""

import pandas as pd
from typing import List, Optional


# Keywords that semantically signal the *positive* (desirable) outcome.
POSITIVE_KEYWORDS = [
    "approved", "accepted", "admitted", "hired", "granted",
    "success", "yes", "positive", "1", "true", "pass", "selected",
]

# Keywords that semantically signal the *negative* (undesirable) outcome.
NEGATIVE_KEYWORDS = [
    "rejected", "denied", "declined", "failed", "no", "negative",
    "0", "false", "fail", "not_selected",
]


def detect_positive_outcome(df: pd.DataFrame, outcome_column: str) -> Optional[str]:
    """Return the semantically positive value from outcome_column.

    Priority order:
    1. A value that matches a positive keyword (case-insensitive).
    2. If no positive match but a negative keyword matches, return the
       first value that ISN'T negative (i.e. the implicit positive).
    3. mode()[0] as a last resort.
    """
    unique_values = df[outcome_column].dropna().unique()
    str_values = [str(v).strip() for v in unique_values]
    lower_values = [s.lower() for s in str_values]

    # 1. Positive keyword match
    for kw in POSITIVE_KEYWORDS:
        if kw in lower_values:
            return str_values[lower_values.index(kw)]

    # 2. Negative keyword found — pick the first non-negative value
    neg_indices = [
        i for i, lv in enumerate(lower_values) if lv in NEGATIVE_KEYWORDS
    ]
    if neg_indices:
        non_neg = [
            str_values[i] for i in range(len(str_values)) if i not in neg_indices
        ]
        if non_neg:
            return non_neg[0]

    # 3. Fallback
    return str(df[outcome_column].mode()[0])


def detect_privileged_value(df: pd.DataFrame, protected_attribute: str) -> str:
    """Return the privileged (majority / reference) group value.

    No reliable keyword heuristic exists for arbitrary protected attributes,
    so this always falls back to the most frequent value.
    """
    return str(df[protected_attribute].mode()[0])


def build_auto_detect_meta(
    explicit_protected_attribute: Optional[str],
    explicit_privileged_value: Optional[str],
    explicit_positive_outcome_value: Optional[str],
    resolved_protected_attribute: str,
    resolved_privileged_value: str,
    resolved_positive_outcome_value: str,
) -> dict:
    """Build the auto_detect metadata dict for config_used."""
    return {
        "protected_attribute": explicit_protected_attribute is None,
        "privileged_value": explicit_privileged_value is None,
        "positive_outcome_value": explicit_positive_outcome_value is None,
    }
