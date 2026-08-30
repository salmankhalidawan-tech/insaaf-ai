"""
Mitigation Agent

Suggests a concrete fairness intervention for the audited dataset and
shows the projected improvement. The current implementation uses
reweighing: each training sample is assigned a weight so that the
privileged and unprivileged groups have equal representation among
positive outcomes. Recomputing the Disparate Impact Ratio on the
reweighted data gives a simulated / projected score.

This uses only pandas and numpy (already in requirements.txt).
"""

import numpy as np
import pandas as pd
from typing import Dict, Optional


class MitigationAgent:
    def __init__(self, df: pd.DataFrame, bias_result: Dict):
        self.df = df
        self.bias_result = bias_result

    @staticmethod
    def _compute_trust_score(bias_result: Dict) -> int:
        """Mirror the scoring logic in ReportingAgent.compute_trust_score."""
        score = 100

        dir_data = bias_result.get("disparate_impact", {})
        if not dir_data.get("passes_80_percent_rule", True):
            score -= 25

        eod_data = bias_result.get("equal_opportunity")
        if eod_data:
            penalty = min(25, abs(eod_data.get("score", 0)) * 100)
            score -= penalty

        if bias_result.get("explainability", {}).get("protected_attribute_in_top_features"):
            score -= 15

        return max(0, round(score))

    def run(self) -> Dict:
        bias = self.bias_result
        dir_data = bias.get("disparate_impact") if isinstance(bias, dict) else None

        # If bias detection failed or produced no DIR, we cannot meaningfully
        # project an improvement.
        if not dir_data or dir_data.get("score") is None:
            return {
                "mitigation_applied": None,
                "original_dir": None,
                "projected_dir": None,
                "original_trust_score": None,
                "projected_trust_score": None,
                "explanation": "Fairness metrics are unavailable, so no mitigation could be projected.",
                "code_snippet": None,
            }

        original_dir = dir_data["score"]

        group_def = bias.get("group_definition", {})
        protected_attribute = self.df.columns[0]  # placeholder; will be overridden below

        # Try to recover the protected attribute and outcome column from the
        # bias result metadata. Fall back to sniffing the dataframe if absent.
        # In practice the pipeline always passes the full bias_result dict.
        protected_values = group_def.get("privileged_values", [])
        unprotected_values = group_def.get("unprivileged_values", [])

        # The bias result doesn't store the column name, so we infer it from the
        # dataframe: pick the first column whose unique values contain all the
        # privileged values.
        outcome_column = None
        for col in self.df.columns:
            unique_vals = set(str(v) for v in self.df[col].unique())
            if all(str(pv) in unique_vals for pv in protected_values):
                protected_attribute = col
                break

        # Likewise infer the outcome column: the first column with exactly two
        # unique values including the positive outcome if we can guess it.
        positive_outcome_value = dir_data.get("positive_outcome_value")
        for col in self.df.columns:
            if col == protected_attribute:
                continue
            unique_vals = set(str(v) for v in self.df[col].unique())
            if len(unique_vals) == 2:
                outcome_column = col
                if positive_outcome_value is None and "approved" in unique_vals:
                    positive_outcome_value = "approved"
                elif positive_outcome_value is None:
                    positive_outcome_value = sorted(unique_vals)[0]
                break

        if outcome_column is None:
            return {
                "mitigation_applied": None,
                "original_dir": original_dir,
                "projected_dir": None,
                "original_trust_score": self._compute_trust_score(bias),
                "projected_trust_score": None,
                "explanation": "Could not infer the outcome column, so reweighing could not be simulated.",
                "code_snippet": None,
            }

        if positive_outcome_value is None:
            positive_outcome_value = sorted(str(v) for v in self.df[outcome_column].unique())[0]

        # Build a privileged mask matching the same logic as BiasDetectionAgent.
        privileged_mask = self.df[protected_attribute].isin(protected_values)
        df = self.df.copy()
        df["_privileged"] = privileged_mask
        df["_positive"] = df[outcome_column].astype(str) == str(positive_outcome_value)

        # Reweighing: compute sample weights so P(group, outcome) becomes
        # uniform / proportional across the four group-outcome combinations.
        # Weight formula:  P_expected(group, outcome) / P_observed(group, outcome)
        # Expected under fairness: each of the 4 combos has probability 1/4.
        n = len(df)
        weights = np.ones(n, dtype=float)

        for privileged in (True, False):
            for positive in (True, False):
                mask = (df["_privileged"] == privileged) & (df["_positive"] == positive)
                count = mask.sum()
                expected = n / 4.0
                if count > 0:
                    weights[mask] = expected / count

        # Projected DIR using weights: weighted positive rate per group.
        priv_mask = df["_privileged"].values
        pos_mask = df["_positive"].values

        priv_weighted_rate = (weights[priv_mask & pos_mask].sum()) / (weights[priv_mask].sum())
        unpriv_weighted_rate = (weights[(~priv_mask) & pos_mask].sum()) / (weights[(~priv_mask)].sum())

        if priv_weighted_rate > 0:
            projected_dir = unpriv_weighted_rate / priv_weighted_rate
        elif unpriv_weighted_rate > 0:
            projected_dir = float("inf")
        else:
            projected_dir = float("nan")

        projected_dir = round(projected_dir, 4) if projected_dir == projected_dir else None

        # Build a synthetic bias_result with the projected DIR to compute the
        # projected trust score the same way ReportingAgent would.
        projected_bias = {
            "disparate_impact": {
                "score": projected_dir,
                "passes_80_percent_rule": bool(projected_dir >= 0.8) if projected_dir is not None else False,
            },
            "equal_opportunity": bias.get("equal_opportunity"),
            "explainability": {"protected_attribute_in_top_features": False},
        }
        original_trust_score = self._compute_trust_score(bias)
        projected_trust_score = self._compute_trust_score(projected_bias)

        explanation = (
            "Reweighing adjusts the importance of each training sample so that "
            "privileged and unprivileged groups are equally represented among "
            "positive outcomes. This does not change the raw data; instead, it "
            "trains the model as if the dataset were more balanced, which typically "
            "raises the Disparate Impact Ratio closer to 1.0 and improves the "
            "projected Trust Score."
        )

        code_snippet = self._build_code_snippet()

        return {
            "mitigation_applied": "reweighing",
            "original_dir": original_dir,
            "projected_dir": projected_dir,
            "original_trust_score": original_trust_score,
            "projected_trust_score": projected_trust_score,
            "explanation": explanation,
            "code_snippet": code_snippet,
        }

    def _build_code_snippet(self) -> str:
        return '''import numpy as np
import pandas as pd

# 1. Load your decision data
df = pd.read_csv("your_data.csv")

protected_attribute = "gender"          # e.g. gender, city, age_group
privileged_values = ["male"]            # values treated as privileged
outcome_column = "loan_approved"        # decision/outcome column
positive_outcome_value = "approved"     # value considered "positive"

# 2. Build helper masks
df["_privileged"] = df[protected_attribute].isin(privileged_values)
df["_positive"] = df[outcome_column].astype(str) == positive_outcome_value

# 3. Compute reweighing sample weights so each group-outcome combination
#    has equal representation. Expected count for each of the 4 combos:
#    privileged+positive, privileged+negative, unprivileged+positive,
#    unprivileged+negative is n / 4.
n = len(df)
weights = np.ones(n, dtype=float)

for privileged in (True, False):
    for positive in (True, False):
        mask = (df["_privileged"] == privileged) & (df["_positive"] == positive)
        count = mask.sum()
        if count > 0:
            weights[mask] = (n / 4.0) / count

# 4. Use the weights when fitting any scikit-learn classifier
from sklearn.ensemble import RandomForestClassifier

X = df.drop(columns=[outcome_column, "_privileged", "_positive"])
y = df[outcome_column]

model = RandomForestClassifier(random_state=42)
model.fit(X, y, sample_weight=weights)

# 5. (Optional) Recompute Disparate Impact Ratio on the reweighted data
priv_mask = df["_privileged"].values
pos_mask = df["_positive"].values

priv_rate = weights[priv_mask & pos_mask].sum() / weights[priv_mask].sum()
unpriv_rate = weights[(~priv_mask) & pos_mask].sum() / weights[(~priv_mask)].sum()
projected_dir = unpriv_rate / priv_rate
print(f"Projected Disparate Impact Ratio: {projected_dir:.4f}")
'''
