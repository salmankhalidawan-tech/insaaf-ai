# Insaaf AI

**Auditing AI for a fairer Pakistan.**

Insaaf AI is a bilingual, multi-agent AI accountability auditor. Upload any AI system's decision data — loan approvals, hiring, admissions — and it detects bias, explains why, and issues a Trust Score with a full report in English and Urdu.

Built for the **Alibaba Cloud AI Hackathon Pakistan 2026** (Open Innovation track), hosted by Alkhidmat Foundation Pakistan on the Bano Qabil platform.

---

## How it works

```
Upload (CSV)
     │
     ▼
Intake Agent            validates the data, detects the protected attribute and outcome column
     │
     ▼
Bias Detection Agent     Disparate Impact Ratio, Equal Opportunity Difference (80% rule)
     │
     ▼
Explainability Agent     SHAP feature importance — shows *why*, not just *that*
     │
     ▼
Translation Agent        bilingual English + Urdu summary
     │
     ▼
Reporting Agent          Trust Score (0–100) + certified seal + downloadable PDF
```

Orchestrated as a CrewAI multi-agent crew, with live streamed progress (SSE) shown in the UI as each agent runs.

## Try it

Two datasets ship with the project:

| Dataset | What it shows |
|---|---|
| `backend/data/pakistani_loan_admissions.csv` | Synthetic Pakistani lending data — urban bias (major vs. minor cities, DIR 0.68) and a secondary gender gap (DIR 0.82) |
| `backend/data/uci_adult_income.csv` | Public UCI Adult Income benchmark, used to externally validate the fairness metrics (DIR 0.31 on gender — see `backend/data/VALIDATION.md`) |

## Project structure

```
insaaf-ai/
├── backend/
│   ├── agents/
│   │   ├── intake_agent.py           # validation + protected-attribute detection
│   │   ├── bias_detection_agent.py   # Disparate Impact Ratio, Equal Opportunity Difference
│   │   ├── explainability_agent.py   # SHAP feature importance
│   │   ├── translation_agent.py      # English → Urdu (offline fallback + free HF API path)
│   │   └── reporting_agent.py        # Trust Score + bilingual, watermarked PDF
│   ├── crew.py                       # CrewAI orchestration
│   ├── streaming.py                  # live SSE progress events
│   ├── pipeline.py                   # sequential fallback pipeline
│   ├── main.py                       # FastAPI app
│   ├── data/                         # sample + Pakistani + UCI datasets, VALIDATION.md
│   ├── fonts/                        # Noto Naskh Arabic (free, OFL) — renders Urdu in PDFs
│   ├── assets/                       # logo watermark for PDF reports
│   └── requirements.txt
└── frontend/
    ├── src/App.jsx                   # upload flow + results dashboard
    ├── src/ActivityLog.jsx           # live per-agent progress log
    ├── src/Seal.jsx                  # "Insaaf Certified" seal
    ├── src/TrustDial.jsx             # circular Trust Score gauge
    └── public/logo/                  # brand mark, favicon
```

## Running it locally

**Backend**

```bash
cd backend
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
```

**Frontend**

```bash
cd frontend
npm install
npm run dev
```

Set `VITE_API_BASE_URL` in a `frontend/.env` file if the backend isn't on `http://localhost:8000`.

**Quick test via API**

```bash
curl -X POST http://localhost:8000/api/audit \
  -F "file=@data/pakistani_loan_admissions.csv" \
  -F "protected_attribute=gender" \
  -F "privileged_value=male" \
  -F "positive_outcome_value=approved"
```

## What's genuinely free in this stack

- FastAPI, pandas, scikit-learn, SHAP, CrewAI, fpdf2, arabic-reshaper, python-bidi — open source, no cost.
- Noto Naskh Arabic font — free, OFL-licensed.
- React, Vite, recharts — open source, no cost.
- Translation ships with a zero-cost offline dictionary fallback for the app's own report vocabulary, with a ready path to the free-tier Hugging Face Inference API (`USE_HF_API` + `HF_API_TOKEN` in `translation_agent.py`) for open-ended text.

## Known limitations

- Fairness metrics assume a binary or grouped protected attribute (e.g. one city group vs. another) against a binary outcome.
- Equal Opportunity Difference requires a separate ground-truth outcome column; without one, only Disparate Impact Ratio is computed.
- The offline Urdu fallback covers the app's own fixed report vocabulary, not open-ended translation.

## Roadmap

- PostgreSQL persistence for audit history (currently stateless).
- Basic API authentication before this goes beyond a demo.
- One-vs-rest extension for multi-category protected attributes beyond two groups.
- One-vs-rest extension for multi-category protected attributes beyond two groups.

