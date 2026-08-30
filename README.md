# Insaaf AI
**Auditing AI for a Fairer Pakistan.**

Insaaf AI is a bilingual, multi-agent AI accountability auditor. Upload any
AI system's decision data (loan approvals, hiring, admissions, etc.) and it
detects bias, explains why, and issues a Trust Score with a full report in
English and Urdu.

Built for the Alibaba Cloud AI Hackathon Pakistan 2026 (Open Innovation track).

## Architecture

```
Upload (CSV) -> Intake Agent -> Bias Detection Agent -> Explainability Agent (SHAP)
                                                              |
                                                              v
                                          Reporting Agent <- Translation Agent
                                                              |
                                                              v
                                            Trust Score + bilingual PDF report
```

## Project structure

```
insaaf-ai/
  backend/
    agents/
      intake_agent.py          # dataset validation, protected-attribute detection
      bias_detection_agent.py  # Disparate Impact Ratio, Equal Opportunity Difference
      explainability_agent.py  # SHAP feature importance
      translation_agent.py     # English -> Urdu (offline fallback + free HF API path)
      reporting_agent.py       # Trust Score formula + bilingual PDF generation
    fonts/                     # Noto Naskh Arabic (free, OFL) - renders Urdu in PDFs
    data/sample_loan_data.csv  # synthetic demo dataset with a real gender gap
    pipeline.py                # orchestrates all 5 agents in sequence
    main.py                    # FastAPI app
    requirements.txt
  frontend/
    src/App.jsx                # upload flow + results dashboard
    src/Seal.jsx                # "Insaaf Certified" seal component
    src/TrustDial.jsx           # circular Trust Score gauge
    src/App.css, src/index.css  # design system (case-dossier aesthetic)
```

## Running the backend

```bash
cd backend
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
```

Test it immediately with the bundled sample dataset:

```bash
curl -X POST http://localhost:8000/api/audit \
  -F "file=@data/sample_loan_data.csv" \
  -F "protected_attribute=gender" \
  -F "privileged_value=male" \
  -F "positive_outcome_value=approved"
```

This sample dataset was built with a deliberate ~13% vs ~87% approval gap
between genders, so a fresh install immediately shows a real, non-trivial
audit result (Disparate Impact Ratio ~0.16, fails the 80% rule).

## Running the frontend

```bash
cd frontend
npm install
npm run dev
```

Set `VITE_API_BASE_URL` in a `.env` file if your backend isn't on
`http://localhost:8000`.

## What is genuinely free in this stack

- FastAPI, pandas, scikit-learn, SHAP, fpdf2, arabic-reshaper, python-bidi: open source, no cost.
- Noto Naskh Arabic font: free, OFL-licensed (Google Fonts).
- React, Vite, recharts: open source, no cost.
- Translation: ships with a zero-cost offline dictionary fallback for the
  app's own report vocabulary. `agents/translation_agent.py` has a ready
  path to the free-tier Hugging Face Inference API for open-ended text -
  set `USE_HF_API = True` and an `HF_API_TOKEN` environment variable to
  enable it.

## What's left to build (see the hackathon delivery plan)

- Wrap `pipeline.py`'s sequential calls in an actual CrewAI `Crew` object
  (one `Agent` + `Task` per stage) - the agent logic itself does not need
  to change, only the orchestration layer. Good first task for Qoder's
  Agent Mode.
- PostgreSQL persistence for audit history (currently stateless).
- A second demo dataset reflecting Pakistani loan/admissions data at
  larger scale, for the live demo.
- Basic auth on the API before this goes beyond a demo.

## Known limitations to flag honestly to judges

- Fairness metrics currently assume a binary protected attribute
  (privileged vs. everyone else) and a binary outcome. Multi-category
  attributes (e.g. multiple provinces) would need a one-vs-rest extension.
- Equal Opportunity Difference requires a ground-truth outcome column
  separate from the model's prediction column; without one, only
  Disparate Impact Ratio is computed.
- The offline translation fallback covers the app's own fixed report
  vocabulary, not open-ended text - it is not a general translator.
