"""
Insaaf AI - CrewAI Multi-Agent Orchestration

Wraps the existing sequential pipeline (Intake -> Bias Detection ->
Explainability -> Reporting) as a CrewAI Crew. Each stage is a CrewAI
Agent + Task pair whose tool delegates to the original agent class, so
all fairness-metric and SHAP logic stays unchanged.

LLM: Groq free tier by default (set GROQ_API_KEY). Swap to Ollama by
commenting/uncommenting the relevant block below.
"""

import json
import os
from typing import Dict, Optional

from dotenv import load_dotenv
load_dotenv()

import pandas as pd
from crewai import Agent, Task, Crew, LLM, Process
from crewai.tools import tool
from auto_detect import detect_positive_outcome, detect_privileged_value, build_auto_detect_meta

# Workaround for a CrewAI 1.15.x bug: the agent executor adds
# ``cache_breakpoint`` keys to messages for Anthropic-style prompt caching,
# but the litellm-based LLM class never strips them before sending to
# non-Anthropic providers (Groq, Ollama, etc.). Those APIs reject messages
# with unknown keys. Safe to remove once CrewAI fixes this upstream.
try:
    from crewai.llm import LLM as _LiteLLM

    _orig_format = _LiteLLM._format_messages_for_provider

    def _format_no_cache(self, messages):
        formatted = _orig_format(self, messages)
        for msg in formatted:
            if isinstance(msg, dict):
                msg.pop("cache_breakpoint", None)
        return formatted

    _LiteLLM._format_messages_for_provider = _format_no_cache
except Exception:
    pass


# ---------------------------------------------------------------------------
# LLM configuration
# ---------------------------------------------------------------------------
# OPTION 1 – Groq (free tier). Sign up at https://console.groq.com and set
# the GROQ_API_KEY environment variable before starting the server.
#
#   set GROQ_API_KEY=gsk_xxxxxxxx        (Windows cmd)
#   export GROQ_API_KEY=gsk_xxxxxxxx     (Linux / macOS / Git Bash)
#
_GROQ_API_KEY = os.environ.get("GROQ_API_KEY", "")

# OPTION 2 – Ollama (fully local, zero cost, no API key).
# Install Ollama from https://ollama.com, then run:
#   ollama pull llama3
# Uncomment the Ollama block below and comment out the Groq block.

if _GROQ_API_KEY:
    llm = LLM(
        model="groq/qwen/qwen3.8-27b",
        api_key=_GROQ_API_KEY,
        temperature=0,
    )
else:
    # Fallback: Ollama running locally on default port.
    # No API key needed – just make sure `ollama serve` is running.
    llm = LLM(
        model=os.environ.get("OLLAMA_MODEL", "ollama/llama3"),
        base_url=os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434"),
        temperature=0,
    )


# ---------------------------------------------------------------------------
# Crew factory
# ---------------------------------------------------------------------------
def build_insaaf_crew(
    df: pd.DataFrame,
    protected_attribute: Optional[str] = None,
    privileged_value: Optional[str] = None,
    positive_outcome_value: Optional[str] = None,
    ground_truth_column: Optional[str] = None,
) -> tuple[Crew, dict]:
    """
    Build the Insaaf audit Crew.

    Returns:
        (crew, state)  – call ``await crew.kickoff_async()`` then read ``state["results"]``
        for the same dict shape the old InsaafPipeline.run() produced.
    """

    # Mutable state shared between tool closures. Each tool writes its output
    # here so the final JSON response is assembled deterministically rather
    # than relying on the LLM to format it.
    state: Dict = {
        "df": df,
        "protected_attribute": protected_attribute,
        "privileged_value": privileged_value,
        "positive_outcome_value": positive_outcome_value,
        "ground_truth_column": ground_truth_column,
        "results": {},
    }

    # ------------------------------------------------------------------
    # Tools – one per pipeline stage, each calling the original agent
    # ------------------------------------------------------------------
    @tool
    def intake_tool(query: str) -> str:
        """Validate the uploaded dataset and auto-detect protected attributes and the outcome column."""
        from agents.intake_agent import IntakeAgent

        agent = IntakeAgent(state["df"])
        result = agent.run()
        state["results"]["intake"] = result
        return json.dumps(result)

    @tool
    def bias_detection_tool(query: str) -> str:
        """Compute fairness metrics (Disparate Impact Ratio, Equal Opportunity Difference) on the dataset."""
        from agents.bias_detection_agent import BiasDetectionAgent

        intake = state["results"]["intake"]
        if not intake["valid"]:
            return json.dumps({"error": "Intake validation failed."})

        pa = state["protected_attribute"] or (
            intake["protected_attributes"][0] if intake["protected_attributes"] else None
        )
        oc = intake["outcome_column"]
        pv = state["privileged_value"] or detect_privileged_value(state["df"], pa)
        pov = state["positive_outcome_value"] or detect_positive_outcome(state["df"], oc)

        # Store resolved config for later stages
        state["resolved_config"] = {
            "protected_attribute": pa,
            "outcome_column": oc,
            "privileged_value": str(pv),
            "positive_outcome_value": str(pov),
            "auto_detect": build_auto_detect_meta(
                state["protected_attribute"], state["privileged_value"],
                state["positive_outcome_value"], pa, str(pv), str(pov),
            ),
        }

        agent = BiasDetectionAgent(
            df=state["df"],
            protected_attribute=pa,
            outcome_column=oc,
            privileged_value=pv,
            positive_outcome_value=pov,
            ground_truth_column=state["ground_truth_column"],
        )
        result = agent.run()
        state["results"]["bias_detection"] = result
        return json.dumps(result)

    @tool
    def explainability_tool(query: str) -> str:
        """Use SHAP to identify which features drive the model's decisions, focusing on the protected attribute."""
        from agents.explainability_agent import ExplainabilityAgent

        cfg = state["resolved_config"]
        agent = ExplainabilityAgent(
            df=state["df"],
            outcome_column=cfg["outcome_column"],
            protected_attribute=cfg["protected_attribute"],
        )
        result = agent.run()
        state["results"]["explainability"] = result
        return json.dumps(result)

    @tool
    def reporting_tool(query: str) -> str:
        """Combine all agent outputs into a Trust Score, bilingual summary, and certification verdict."""
        from agents.reporting_agent import ReportingAgent

        intake = state["results"]["intake"]
        bias = state["results"]["bias_detection"]

        # If a prior stage already failed, propagate the error without
        # attempting to build a report from incomplete data.
        if isinstance(bias, dict) and "stage_failed" in bias:
            state["results"]["report"] = {"stage_failed": bias["stage_failed"], "error": bias.get("error", "")}
            return json.dumps(state["results"]["report"])

        explain = state["results"]["explainability"]

        agent = ReportingAgent(intake, bias, explain)
        result = agent.run()
        state["results"]["report"] = result
        state["results"]["config_used"] = state.get("resolved_config", {})
        return json.dumps(result)

    @tool
    def mitigation_tool(query: str) -> str:
        """Suggest a fairness intervention and project the improvement in Disparate Impact Ratio and Trust Score."""
        from agents.mitigation_agent import MitigationAgent

        bias = state["results"].get("bias_detection", {})
        if isinstance(bias, dict) and "stage_failed" in bias:
            return json.dumps({"mitigation_applied": None, "explanation": "Bias detection failed; no mitigation projected."})

        agent = MitigationAgent(state["df"], bias)
        result = agent.run()
        state["results"]["mitigation"] = result
        return json.dumps(result)

    # ------------------------------------------------------------------
    # Agents
    # ------------------------------------------------------------------
    intake_agent = Agent(
        role="Intake Analyst",
        goal="Validate the dataset and identify protected attributes and the outcome column.",
        backstory=(
            "You are a data-quality specialist. Your job is to confirm the "
            "uploaded CSV is usable and to flag which columns represent "
            "protected attributes (gender, age, etc.) and the decision outcome."
        ),
        tools=[intake_tool],
        llm=llm,
        verbose=False,
    )

    bias_agent = Agent(
        role="Bias Detection Analyst",
        goal="Compute standard fairness metrics and flag any statistically significant bias.",
        backstory=(
            "You are a fairness-in-ML researcher. You compute Disparate "
            "Impact Ratio and Equal Opportunity Difference, then flag "
            "violations of the 80% rule or the +/-0.1 EOD threshold."
        ),
        tools=[bias_detection_tool],
        llm=llm,
        verbose=False,
    )

    explain_agent = Agent(
        role="Explainability Specialist",
        goal="Determine which features most influence the model's decisions using SHAP.",
        backstory=(
            "You are a model-interpretability engineer. You train a surrogate "
            "model and use SHAP values to rank feature importance, paying "
            "special attention to whether the protected attribute appears in "
            "the top predictors."
        ),
        tools=[explainability_tool],
        llm=llm,
        verbose=False,
    )

    reporting_agent = Agent(
        role="Report Author",
        goal="Produce a Trust Score, certification verdict, and bilingual summary from all findings.",
        backstory=(
            "You compile the results of every upstream agent into a single "
            "trust report. You compute the 0-100 Trust Score using the "
            "documented penalty formula and translate the English summary "
            "into Urdu."
        ),
        tools=[reporting_tool],
        llm=llm,
        verbose=False,
    )

    mitigation_agent = Agent(
        role="Fairness Engineer",
        goal="Recommend a concrete bias mitigation and show the projected improvement.",
        backstory=(
            "You are a fairness engineer. You analyze the detected bias and "
            "propose a reweighing intervention that balances representation "
            "across privileged and unprivileged groups, then estimate the "
            "new Disparate Impact Ratio and Trust Score."
        ),
        tools=[mitigation_tool],
        llm=llm,
        verbose=False,
    )

    # ------------------------------------------------------------------
    # Tasks – one per agent, in pipeline order
    # ------------------------------------------------------------------
    intake_task = Task(
        description=(
            "Use the intake_tool to validate the dataset and detect "
            "protected attributes and the outcome column. Return the "
            "tool's JSON output as-is."
        ),
        expected_output="JSON with valid/message, protected_attributes list, outcome_column, row_count.",
        agent=intake_agent,
    )

    bias_task = Task(
        description=(
            "Use the bias_detection_tool to compute fairness metrics. "
            "Return the tool's JSON output as-is."
        ),
        expected_output="JSON with disparate_impact, equal_opportunity, bias_flags, bias_detected.",
        agent=bias_agent,
    )

    explain_task = Task(
        description=(
            "Use the explainability_tool to run SHAP analysis. "
            "Return the tool's JSON output as-is."
        ),
        expected_output="JSON with top_features, protected_attribute_in_top_features, status.",
        agent=explain_agent,
    )

    report_task = Task(
        description=(
            "Use the reporting_tool to compute the Trust Score and produce "
            "the bilingual summary. Return the tool's JSON output as-is."
        ),
        expected_output="JSON with trust_score, certified, summary_english, summary_urdu, generated_at.",
        agent=reporting_agent,
    )

    mitigation_task = Task(
        description=(
            "Use the mitigation_tool to suggest a reweighing fix and return "
            "the projected Disparate Impact Ratio and Trust Score. "
            "Return the tool's JSON output as-is."
        ),
        expected_output="JSON with mitigation_applied, original_dir, projected_dir, original_trust_score, projected_trust_score, explanation, code_snippet.",
        agent=mitigation_agent,
        context=[report_task],
    )

    crew = Crew(
        agents=[intake_agent, bias_agent, explain_agent, reporting_agent, mitigation_agent],
        tasks=[intake_task, bias_task, explain_task, report_task, mitigation_task],
        process=Process.sequential,
        verbose=False,
    )

    return crew, state
