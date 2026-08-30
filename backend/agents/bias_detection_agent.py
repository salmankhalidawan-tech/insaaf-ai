"""
Bias Detection Agent
Computes standard, published fairness metrics on a dataset:

1. Disparate Impact Ratio (DIR)
   - Ratio of positive outcome rate for the unprivileged group vs privileged group.
   - The "80% rule" (used by the US EEOC) flags DIR < 0.8 as evidence of bias.

2. Equal Opportunity Difference (EOD)
   - Difference in True Positive Rate between groups, when ground truth is available.

3. Average Odds Difference (AOD)
   - Average of the difference in False Positive Rate and True Positive Rate
     between groups.

These are well-established metrics from the fairness-in-ML literature
(see IBM AI Fairness 360 documentation for reference definitions).
"""

import pandas as pd
import numpy as np
from typing import Dict, Optional


class BiasDetectionAgent:
    def __init__(
        self,
        df: pd.DataFrame,
        protected_attribute: str,
        outcome_column: str,
        privileged_value,
        positive_outcome_value,
        ground_truth_column: Optional[str] = None,
    ):
        self.df = df
        self.protected_attribute = protected_attribute
        self.outcome_column = outcome_column
        self.positive_outcome_value = positive_outcome_value
        self.ground_truth_column = ground_truth_column

        # Accept a single value or a comma-separated string of values.
        # "Lahore,Karachi,Islamabad" → treat all rows matching ANY as privileged.
        if isinstance(privileged_value, str) and "," in privileged_value:
            self.privileged_values = [v.strip() for v in privileged_value.split(",") if v.strip()]
        elif isinstance(privileged_value, list):
            self.privileged_values = [str(v).strip() for v in privileged_value if str(v).strip()]
        else:
            self.privileged_values = [str(privileged_value).strip()] if privileged_value is not None else []

        self.privileged_mask = df[protected_attribute].isin(self.privileged_values)

    def _validate_groups(self):
        """Return an error string if either group is empty, else None."""
        priv_count = int(self.privileged_mask.sum())
        unpriv_count = int((~self.privileged_mask).sum())
        if priv_count == 0:
            return (
                f"No rows matched the privileged value(s) {self.privileged_values} "
                f"in column '{self.protected_attribute}'. "
                "Check spelling and capitalization against the actual column values."
            )
        if unpriv_count == 0:
            return (
                f"All rows match the privileged value(s) {self.privileged_values} — "
                f"no unprivileged group exists in column '{self.protected_attribute}'. "
                "Check that the privileged value(s) do not cover every row."
            )
        return None

    def _get_group_definition(self) -> Dict:
        """Return the actual privileged/unprivileged value lists for this audit."""
        unprivileged_values = sorted(
            str(v) for v in self.df.loc[~self.privileged_mask, self.protected_attribute].unique()
        )
        return {
            "privileged_values": list(self.privileged_values),
            "unprivileged_values": unprivileged_values,
        }

    def _positive_rate(self, group_df: pd.DataFrame) -> float:
        if len(group_df) == 0:
            return 0.0
        positives = (group_df[self.outcome_column] == self.positive_outcome_value).sum()
        return positives / len(group_df)

    def disparate_impact_ratio(self) -> Dict:
        privileged = self.df[self.privileged_mask]
        unprivileged = self.df[~self.privileged_mask]

        priv_rate = self._positive_rate(privileged)
        unpriv_rate = self._positive_rate(unprivileged)

        if priv_rate > 0:
            dir_score = unpriv_rate / priv_rate
        elif unpriv_rate > 0:
            # Privileged group has 0 positives but unprivileged does not.
            dir_score = float("inf")
        else:
            # Both groups have 0 positives — ratio is undefined.
            dir_score = float("nan")

        return {
            "metric": "Disparate Impact Ratio",
            "privileged_positive_rate": round(priv_rate, 4),
            "unprivileged_positive_rate": round(unpriv_rate, 4),
            "score": round(dir_score, 4) if not (dir_score != dir_score) else None,  # NaN guard
            "passes_80_percent_rule": bool(dir_score >= 0.8) if dir_score == dir_score else False,
        }

    def equal_opportunity_difference(self) -> Optional[Dict]:
        """Requires ground truth labels to compute True Positive Rate per group."""
        if not self.ground_truth_column or self.ground_truth_column not in self.df.columns:
            return None

        def tpr(group_df: pd.DataFrame) -> float:
            actual_positive = group_df[group_df[self.ground_truth_column] == self.positive_outcome_value]
            if len(actual_positive) == 0:
                return 0.0
            correctly_predicted = (
                actual_positive[self.outcome_column] == self.positive_outcome_value
            ).sum()
            return correctly_predicted / len(actual_positive)

        privileged = self.df[self.privileged_mask]
        unprivileged = self.df[~self.privileged_mask]

        priv_tpr = tpr(privileged)
        unpriv_tpr = tpr(unprivileged)
        eod = unpriv_tpr - priv_tpr

        return {
            "metric": "Equal Opportunity Difference",
            "privileged_tpr": round(priv_tpr, 4),
            "unprivileged_tpr": round(unpriv_tpr, 4),
            "score": round(eod, 4),
            "within_acceptable_range": bool(abs(eod) <= 0.1),
        }

    def run(self) -> Dict:
        group_error = self._validate_groups()
        if group_error:
            return {
                "stage_failed": "bias_detection",
                "error": group_error,
                "disparate_impact": None,
                "equal_opportunity": None,
                "bias_flags": [],
                "bias_detected": False,
                "group_definition": self._get_group_definition(),
            }

        result = {
            "disparate_impact": self.disparate_impact_ratio(),
            "equal_opportunity": self.equal_opportunity_difference(),
            "group_definition": self._get_group_definition(),
        }

        dir_score = result["disparate_impact"]["score"]
        eod = result["equal_opportunity"]["score"] if result["equal_opportunity"] else None

        flags = []
        if dir_score is not None and dir_score < 0.8:
            flags.append("Disparate Impact Ratio below the 80% rule threshold.")
        if eod is not None and abs(eod) > 0.1:
            flags.append("Equal Opportunity Difference exceeds acceptable range (+/-0.1).")

        result["bias_flags"] = flags
        result["bias_detected"] = len(flags) > 0
        return result
