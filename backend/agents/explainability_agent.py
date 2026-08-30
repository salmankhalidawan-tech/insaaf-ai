"""
Explainability Agent
Trains a quick surrogate model on the dataset (if the user did not already
provide model scores) and uses SHAP to identify which features contribute
most to the outcome - specifically for the group flagged by the Bias
Detection Agent. This turns "bias was detected" into "here is WHY".
"""

import pandas as pd
import numpy as np
import shap
from sklearn.ensemble import RandomForestClassifier
from sklearn.preprocessing import LabelEncoder
from typing import Dict, List


class ExplainabilityAgent:
    def __init__(self, df: pd.DataFrame, outcome_column: str, protected_attribute: str):
        self.df = df.copy()
        self.outcome_column = outcome_column
        self.protected_attribute = protected_attribute

    def _prepare_features(self):
        feature_df = self.df.drop(columns=[self.outcome_column])
        encoders = {}
        for col in feature_df.columns:
            if not pd.api.types.is_numeric_dtype(feature_df[col]):
                le = LabelEncoder()
                feature_df[col] = le.fit_transform(feature_df[col].astype(str))
                encoders[col] = le

        target = self.df[self.outcome_column]
        if not pd.api.types.is_numeric_dtype(target):
            target = LabelEncoder().fit_transform(target.astype(str))

        return feature_df, target

    def run(self, top_n: int = 5) -> Dict:
        try:
            X, y = self._prepare_features()

            model = RandomForestClassifier(n_estimators=150, random_state=42, max_depth=6)
            model.fit(X, y)

            explainer = shap.TreeExplainer(model)
            shap_values = explainer.shap_values(X)

            # SHAP's return shape varies by version:
            # - list of arrays, one per class (older shap versions)
            # - 3D array (samples, features, classes) (newer shap versions)
            # - 2D array (samples, features) (regression / binary-only output)
            if isinstance(shap_values, list):
                values = np.abs(shap_values[1]).mean(axis=0)
            elif isinstance(shap_values, np.ndarray) and shap_values.ndim == 3:
                # take the positive class (last index) across all samples
                values = np.abs(shap_values[:, :, -1]).mean(axis=0)
            else:
                values = np.abs(shap_values).mean(axis=0)

            importance = sorted(
                zip(X.columns, values), key=lambda pair: pair[1], reverse=True
            )[:top_n]

            top_features: List[Dict] = [
                {"feature": name, "importance": round(float(score), 4)}
                for name, score in importance
            ]

            flagged = any(f["feature"] == self.protected_attribute for f in top_features)

            return {
                "status": "success",
                "top_features": top_features,
                "protected_attribute_in_top_features": flagged,
                "note": (
                    f"'{self.protected_attribute}' is among the top predictive features - "
                    "this is a strong signal the model may be relying on it directly or "
                    "through a correlated proxy feature."
                ) if flagged else (
                    f"'{self.protected_attribute}' was not directly among the top features, "
                    "but bias can still enter through correlated proxy variables (e.g. postal "
                    "code correlating with ethnicity). Cross-check proxy correlations manually."
                ),
            }
        except Exception as exc:
            return {"status": "error", "message": str(exc)}
