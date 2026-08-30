"""
Insaaf AI - FastAPI Backend

Endpoints:
  POST /api/audit          - upload a CSV, run the full pipeline, get JSON results
  GET  /api/report/{id}     - download the generated PDF report
  GET  /api/health          - health check

Run locally:
  pip install -r requirements.txt
  uvicorn main:app --reload --port 8000

TODO (Qoder build phase):
  - Add PostgreSQL persistence (SQLAlchemy) for audit history per user/org.
  - Add auth (even a simple API key) before this goes past demo stage.
  - Add the /api/audit-from-json endpoint for API-based (non-CSV) audits.
"""

import io
import os
import uuid
import pandas as pd
from fastapi import FastAPI, UploadFile, File, HTTPException, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, StreamingResponse
from typing import Optional

from crew import build_insaaf_crew
from pipeline import InsaafPipeline
from agents.reporting_agent import ReportingAgent
from streaming import audit_event_stream

app = FastAPI(title="Insaaf AI API", version="0.1.0")

# Allow the React dev server to call this API during development.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # tighten this to your deployed frontend URL in production
    allow_methods=["*"],
    allow_headers=["*"],
)

REPORTS_DIR = "generated_reports"
os.makedirs(REPORTS_DIR, exist_ok=True)


@app.get("/api/health")
def health():
    return {"status": "ok", "service": "Insaaf AI"}


@app.post("/api/audit")
async def audit(
    file: UploadFile = File(...),
    protected_attribute: Optional[str] = Form(None),
    privileged_value: Optional[str] = Form(None),
    positive_outcome_value: Optional[str] = Form(None),
    ground_truth_column: Optional[str] = Form(None),
):
    if not file.filename.endswith(".csv"):
        raise HTTPException(status_code=400, detail="Please upload a CSV file.")

    contents = await file.read()
    try:
        df = pd.read_csv(io.BytesIO(contents))
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Could not parse CSV: {exc}")

    crew, state = build_insaaf_crew(
        df=df,
        protected_attribute=protected_attribute,
        privileged_value=privileged_value,
        positive_outcome_value=positive_outcome_value,
        ground_truth_column=ground_truth_column,
    )
    try:
        await crew.kickoff_async()
        result = state["results"]
    except Exception as crew_err:
        # Fallback: no LLM available or crew failed — run the original
        # sequential pipeline so the API always returns a valid response.
        import logging
        logging.warning("CrewAI crew failed (%s), falling back to sequential pipeline.", crew_err)
        pipeline = InsaafPipeline(
            df=df,
            protected_attribute=protected_attribute,
            privileged_value=privileged_value,
            positive_outcome_value=positive_outcome_value,
            ground_truth_column=ground_truth_column,
        )
        result = pipeline.run()

    if "stage_failed" in result:
        raise HTTPException(status_code=422, detail=result)

    # Propagate nested stage failures from individual pipeline stages
    # (e.g. bias_detection returning stage_failed for empty groups).
    for stage_key, stage_val in result.items():
        if isinstance(stage_val, dict) and "stage_failed" in stage_val:
            raise HTTPException(status_code=422, detail=stage_val)

    if result.get("intake", {}).get("valid") is False:
        raise HTTPException(
            status_code=422,
            detail={"stage_failed": "intake", "error": result["intake"].get("message", "Intake failed.")},
        )

    # Generate the PDF and store it for download
    report_id = str(uuid.uuid4())
    reporting_agent = ReportingAgent(
        result["intake"], result["bias_detection"], result["explainability"]
    )
    pdf_path = os.path.join(REPORTS_DIR, f"{report_id}.pdf")
    reporting_agent.generate_pdf(result["report"], pdf_path)

    result["report_id"] = report_id
    return result


@app.post("/api/audit-stream")
async def audit_stream(
    file: UploadFile = File(...),
    protected_attribute: Optional[str] = Form(None),
    privileged_value: Optional[str] = Form(None),
    positive_outcome_value: Optional[str] = Form(None),
    ground_truth_column: Optional[str] = Form(None),
):
    if not file.filename.endswith(".csv"):
        raise HTTPException(status_code=400, detail="Please upload a CSV file.")

    contents = await file.read()

    return StreamingResponse(
        audit_event_stream(
            contents,
            protected_attribute,
            privileged_value,
            positive_outcome_value,
            ground_truth_column,
            REPORTS_DIR,
        ),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache, no-transform",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@app.get("/api/report/{report_id}")
def get_report(report_id: str):
    path = os.path.join(REPORTS_DIR, f"{report_id}.pdf")
    if not os.path.exists(path):
        raise HTTPException(status_code=404, detail="Report not found.")
    return FileResponse(path, media_type="application/pdf", filename="Insaaf_AI_Trust_Report.pdf")
