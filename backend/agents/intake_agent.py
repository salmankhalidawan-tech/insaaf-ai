"""
Intake Agent
Responsible for: validating an uploaded dataset, detecting likely protected
attributes (gender, age, location, religion, etc.), and detecting which
column holds the model's decision/outcome (approved/rejected, hired/not, etc.)

This agent does NOT compute fairness metrics itself - it only prepares and
validates the data so the Bias Detection Agent can trust its input.
"""

import pandas as pd
from typing import Dict, List, Tuple

# Common column-name patterns for protected attributes. This is a heuristic
# starting point - extend this list as you test on real Pakistani datasets
# (e.g. "zaat", "firqa", "wilayat" if you localize further).
PROTECTED_ATTRIBUTE_HINTS = [
    "gender", "sex", "age", "age_group", "race", "ethnicity", "religion",
    "location", "city", "province", "region", "disability", "marital_status",
]

# Common column-name patterns for the outcome/decision column.
OUTCOME_HINTS = [
    "approved", "outcome", "decision", "label", "target", "result",
    "status", "hired", "admitted", "prediction", "predicted",
]


class IntakeAgent:
    def __init__(self, dataframe: pd.DataFrame):
        self.df = dataframe

    def validate(self) -> Tuple[bool, str]:
        """Basic sanity checks before anything else runs."""
        if self.df is None or self.df.empty:
            return False, "Uploaded dataset is empty."
        if self.df.shape[0] < 10:
            return False, "Dataset needs at least 10 rows for meaningful bias analysis."
        if self.df.shape[1] < 2:
            return False, "Dataset needs at least 2 columns (a protected attribute and an outcome)."
        return True, "Dataset passed validation."

    def detect_protected_attributes(self) -> List[str]:
        """Return column names that look like protected attributes."""
        found = []
        for col in self.df.columns:
            normalized = col.strip().lower().replace(" ", "_")
            if normalized in PROTECTED_ATTRIBUTE_HINTS:
                found.append(col)
        return found

    def detect_outcome_column(self) -> str | None:
        """Return the most likely outcome/decision column."""
        for col in self.df.columns:
            normalized = col.strip().lower().replace(" ", "_")
            if normalized in OUTCOME_HINTS:
                return col
        # Fallback: last column is often the label in benchmark datasets
        return self.df.columns[-1] if len(self.df.columns) > 0 else None

    def run(self) -> Dict:
        is_valid, message = self.validate()
        result = {
            "valid": is_valid,
            "message": message,
            "protected_attributes": [],
            "outcome_column": None,
            "row_count": 0,
        }
        if not is_valid:
            return result

        result["protected_attributes"] = self.detect_protected_attributes()
        result["outcome_column"] = self.detect_outcome_column()
        result["row_count"] = int(self.df.shape[0])
        return result
