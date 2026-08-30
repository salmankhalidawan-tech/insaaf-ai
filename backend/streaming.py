"""
Insaaf AI — SSE Streaming Audit

Emits real-time Server-Sent Events as each pipeline stage runs.
Uses the sequential InsaafPipeline (not CrewAI) so we can emit genuine
progress events around each agent's actual run() call.

All CPU-blocking agent calls go through asyncio.to_thread() so the
event loop stays responsive and SSE frames flush progressively.
"""

import io
import os
import uuid
import json
import asyncio
import logging
import pandas as pd

from pipeline import InsaafPipeline
from agents.reporting_agent import ReportingAgent

STAGE_ORDER = [
    "upload",
    "intake",
    "bias_detection",
    "explainability",
    "translation",
    "reporting",
    "pdf_generation",
]

STAGE_LABELS = {
    "upload":         {"running": "Parsing the uploaded CSV",
                       "done":    "CSV parsed"},
    "intake":         {"running": "Validating the dataset",
                       "done":    "Dataset validated"},
    "bias_detection": {"running": "Testing for bias",
                       "done":    "Fairness metrics computed"},
    "explainability": {"running": "Explaining the results",
                       "done":    "Feature attribution complete"},
    "translation":    {"running": "Preparing the Urdu report",
                       "done":    "Urdu report prepared"},
    "reporting":      {"running": "Calculating the trust score",
                       "done":    "Trust report compiled"},
    "pdf_generation": {"running": "Generating the PDF report",
                       "done":    "PDF report ready"},
}


def sse(payload: dict) -> str:
    return "data: " + json.dumps(payload, ensure_ascii=False, default=str) + "\n\n"


def comment(text: str) -> str:
    return f": {text}\n\n"


def _stage_event(stage: str, status: str, label: str = None, **extra) -> str:
    payload = {
        "stage": stage,
        "status": status,
        "label": label or STAGE_LABELS.get(stage, {}).get(status, stage),
        "index": STAGE_ORDER.index(stage) if stage in STAGE_ORDER else None,
        "total": len(STAGE_ORDER),
    }
    payload.update(extra)
    return sse(payload)


async def audit_event_stream(
    contents: bytes,
    protected_attribute,
    privileged_value,
    positive_outcome_value,
    ground_truth_column,
    reports_dir: str,
):
    yield comment("stream-open")

    try:
        # ── upload ────────────────────────────────────────────────────
        yield _stage_event("upload", "running")
        try:
            df = await asyncio.to_thread(pd.read_csv, io.BytesIO(contents))
        except Exception as exc:
            yield _stage_event("upload", "error", f"Could not parse CSV: {exc}")
            return
        yield _stage_event("upload", "done", f"Parsed {len(df):,} rows, {len(df.columns)} columns")

        pipeline = InsaafPipeline(
            df=df,
            protected_attribute=protected_attribute,
            privileged_value=privileged_value,
            positive_outcome_value=positive_outcome_value,
            ground_truth_column=ground_truth_column,
        )

        # ── intake ────────────────────────────────────────────────────
        yield _stage_event("intake", "running")
        intake = await asyncio.to_thread(pipeline.stage_intake)

        if not intake["valid"]:
            yield _stage_event("intake", "error", intake.get("message", "Intake failed."))
            return

        cfg = pipeline.resolve_config(intake)
        if "error" in cfg:
            yield _stage_event("intake", "error", cfg["error"])
            return

        yield _stage_event(
            "intake", "done",
            f"Auditing '{cfg['protected_attribute']}' against '{cfg['outcome_column']}'"
        )

        # ── bias_detection ────────────────────────────────────────────
        yield _stage_event("bias_detection", "running")
        bias = await asyncio.to_thread(pipeline.stage_bias_detection, cfg)

        if isinstance(bias, dict) and "stage_failed" in bias:
            yield _stage_event("bias_detection", "error", bias.get("error", "Bias detection failed."))
            return

        yield _stage_event(
            "bias_detection", "done",
            "Bias detected" if bias.get("bias_detected") else "No bias flagged"
        )

        # ── explainability (non-fatal) ────────────────────────────────
        yield _stage_event("explainability", "running")
        explain = await asyncio.to_thread(pipeline.stage_explainability, cfg)

        if explain.get("status") == "error":
            yield _stage_event(
                "explainability", "done",
                "SHAP analysis unavailable — continuing without it",
                detail=explain.get("message"),
            )
        else:
            yield _stage_event("explainability", "done")

        # ── translation ───────────────────────────────────────────────
        agent = ReportingAgent(intake, bias, explain)
        trust_score = agent.compute_trust_score()

        yield _stage_event("translation", "running")
        summaries = await asyncio.to_thread(agent.build_summaries, trust_score)
        yield _stage_event("translation", "done")

        # ── reporting ─────────────────────────────────────────────────
        yield _stage_event("reporting", "running")
        report = agent.assemble_report(trust_score, summaries)
        result = {
            "intake": intake,
            "bias_detection": bias,
            "explainability": explain,
            "report": report,
            "config_used": pipeline.build_config_used(cfg),
        }
        yield _stage_event("reporting", "done", f"Trust Score {report['trust_score']}/100")

        # ── pdf_generation ────────────────────────────────────────────
        yield _stage_event("pdf_generation", "running")
        report_id = str(uuid.uuid4())
        pdf_path = os.path.join(reports_dir, f"{report_id}.pdf")
        await asyncio.to_thread(agent.generate_pdf, report, pdf_path)
        result["report_id"] = report_id
        yield _stage_event("pdf_generation", "done")

        yield sse({"stage": "complete", "status": "done", "result": result})

    except asyncio.CancelledError:
        raise
    except Exception as exc:
        logging.exception("audit-stream failed")
        yield _stage_event("unknown", "error", f"Unexpected error: {exc}")
