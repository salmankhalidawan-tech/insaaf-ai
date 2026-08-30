"""
Insaaf AI - Pipeline Orchestrator

This coordinates the 5 agents in sequence:
Intake -> Bias Detection -> Explainability -> Translation -> Reporting

NOTE FOR QODER BUILD PHASE:
This file currently orchestrates agents with plain sequential Python calls,
which is the fastest way to get a correct, demoable pipeline running.
To match the submitted technical approach exactly, wrap this same call
sequence in a CrewAI Crew (crewai.Crew) with each agent class exposed as a
CrewAI Agent + Task pair. The agent logic itself does not need to change -
only the orchestration layer. This is a good first task to hand to Qoder's
Agent Mode: "convert pipeline.py's sequential calls into a CrewAI Crew with
one Agent + Task per stage, preserving all existing method signatures."
"""

import pandas as pd
from typing import Dict, Optional

from agents.intake_agent import IntakeAgent
from agents.bias_detection_agent import BiasDetectionAgent
from agents.explainability_agent import ExplainabilityAgent
from agents.reporting_agent import ReportingAgent
from agents.mitigation_agent import MitigationAgent
from auto_detect import detect_positive_outcome, detect_privileged_value, build_auto_detect_meta


class InsaafPipeline:
    def __init__(
        self,
        df: pd.DataFrame,
        protected_attribute: Optional[str] = None,
        privileged_value: Optional[str] = None,
        positive_outcome_value: Optional[str] = None,
        ground_truth_column: Optional[str] = None,
    ):
        self.df = df
        self.protected_attribute = protected_attribute
        self.privileged_value = privileged_value
        self.positive_outcome_value = positive_outcome_value
        self.ground_truth_column = ground_truth_column

    def stage_intake(self) -> Dict:
        return IntakeAgent(self.df).run()

    def resolve_config(self, intake_result: Dict) -> Dict:
        protected_attribute = self.protected_attribute or (
            intake_result["protected_attributes"][0]
            if intake_result["protected_attributes"]
            else None
        )
        outcome_column = intake_result["outcome_column"]

        if not protected_attribute or not outcome_column:
            return {
                "error": "Could not auto-detect a protected attribute or outcome column. "
                         "Please specify them explicitly.",
            }

        privileged_value = (
            self.privileged_value
            or detect_privileged_value(self.df, protected_attribute)
        )
        positive_outcome_value = (
            self.positive_outcome_value
            or detect_positive_outcome(self.df, outcome_column)
        )

        return {
            "protected_attribute": protected_attribute,
            "outcome_column": outcome_column,
            "privileged_value": privileged_value,
            "positive_outcome_value": positive_outcome_value,
        }

    def stage_bias_detection(self, cfg: Dict) -> Dict:
        return BiasDetectionAgent(
            df=self.df,
            protected_attribute=cfg["protected_attribute"],
            outcome_column=cfg["outcome_column"],
            privileged_value=cfg["privileged_value"],
            positive_outcome_value=cfg["positive_outcome_value"],
            ground_truth_column=self.ground_truth_column,
        ).run()

    def stage_explainability(self, cfg: Dict) -> Dict:
        return ExplainabilityAgent(
            df=self.df,
            outcome_column=cfg["outcome_column"],
            protected_attribute=cfg["protected_attribute"],
        ).run()

    def stage_mitigation(self, bias_result: Dict) -> Dict:
        return MitigationAgent(df=self.df, bias_result=bias_result).run()

    def build_config_used(self, cfg: Dict) -> Dict:
        return {
            "protected_attribute": cfg["protected_attribute"],
            "outcome_column": cfg["outcome_column"],
            "privileged_value": str(cfg["privileged_value"]),
            "positive_outcome_value": str(cfg["positive_outcome_value"]),
            "auto_detect": build_auto_detect_meta(
                self.protected_attribute, self.privileged_value, self.positive_outcome_value,
                cfg["protected_attribute"], str(cfg["privileged_value"]), str(cfg["positive_outcome_value"]),
            ),
        }

    def run(self) -> Dict:
        # Stage 1: Intake
        intake_result = self.stage_intake()

        if not intake_result["valid"]:
            return {"stage_failed": "intake", "error": intake_result["message"]}

        cfg = self.resolve_config(intake_result)
        if "error" in cfg:
            return {
                "stage_failed": "intake",
                "error": cfg["error"],
                "intake_result": intake_result,
            }

        # Stage 2: Bias Detection
        bias_result = self.stage_bias_detection(cfg)

        # Stage 3: Explainability
        explainability_result = self.stage_explainability(cfg)

        # Stage 4 + 5: Reporting (internally calls Translation Agent)
        reporting_agent = ReportingAgent(intake_result, bias_result, explainability_result)
        report = reporting_agent.run()

        # Stage 6: Mitigation (suggests a fix and projects improvement)
        mitigation_result = self.stage_mitigation(bias_result)

        return {
            "intake": intake_result,
            "bias_detection": bias_result,
            "explainability": explainability_result,
            "report": report,
            "mitigation": mitigation_result,
            "config_used": self.build_config_used(cfg),
        }
