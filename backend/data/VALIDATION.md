# Insaaf AI — Validation Against UCI Adult Income Dataset

## Dataset

| Field | Value |
|---|---|
| **Name** | UCI Adult Income (Census Income) |
| **Source** | [UCI Machine Learning Repository](https://archive.ics.uci.edu/dataset/2/adult) |
| **Original size** | 32,561 rows × 15 columns |
| **After cleaning** | 30,162 rows (dropped rows with missing values or `?`) |
| **Sampled** | 2,000 rows (seed = 42) |
| **Saved as** | `backend/data/uci_adult_income.csv` |
| **Prep script** | `backend/data/prepare_uci_adult.py` |

## Column Mapping

| Original column | Renamed to | Notes |
|---|---|---|
| `sex` | `gender` | Lowercased: `male`, `female` |
| `age` | `age` | Kept as-is |
| `education` | `education` | Categorical (e.g. `Bachelors`, `HS-grad`) |
| `hours_per_week` | `hours_per_week` | Numeric |
| `native_country` | `native_country` | Categorical |
| `income` | `loan_approved` | `>50K` → `approved`, `<=50K` → `rejected` |

## Dataset Demographics (2,000-row sample)

| Group | Count | % |
|---|---|---|
| Male | 1,347 | 67.4% |
| Female | 653 | 32.6% |
| Approved (>50K) | 515 | 25.8% |
| Rejected (<=50K) | 1,485 | 74.2% |

## Pipeline Configuration

```
protected_attribute  = gender
privileged_value     = male
positive_outcome     = approved
ground_truth_column  = loan_approved
```

## Results

### Bias Detection

| Metric | Value | Threshold | Pass/Fail |
|---|---|---|---|
| **Disparate Impact Ratio** | **0.3138** | ≥ 0.80 (80% rule) | **FAIL** |
| Privileged positive rate (male) | 0.3318 (33.2%) | — | — |
| Unprivileged positive rate (female) | 0.1041 (10.4%) | — | — |
| Approval rate gap | 22.8 percentage points | — | — |
| **Equal Opportunity Difference** | **0.0** | within ±0.1 | PASS |

### Explainability (SHAP — top 5 features)

| Rank | Feature | Mean |SHAP| |
|---|---|---|
| 1 | `age` | 0.0976 |
| 2 | `gender` | 0.0754 |
| 3 | `hours_per_week` | 0.0593 |
| 4 | `education` | 0.0422 |
| 5 | `native_country` | 0.0021 |

`gender` appears as the **2nd most important feature**, confirming the model relies on it directly or through correlated proxies.

### Trust Score

| | |
|---|---|
| **Score** | **60 / 100** |
| **Certified** | **No** |
| Penalties applied | DIR failure (−25), gender in top SHAP features (−15) |

### Bilingual Summary

**English:**
> Trust Score: 60/100. This system shows signs of bias against the unprivileged group. Disparate Impact Ratio fails the 80 percent rule (score: 0.3138). The top contributing feature to the model's decisions is: age.

**Urdu:**
> اعتماد اسکور: 60/100۔ یہ نظام کمزور گروہ کے خلاف تعصب کے آثار ظاہر کرتا ہے۔ غیر مساوی اثر کا تناسب 80 فیصد اصول پر پورا نہیں اترتا (score: 0.3138)۔ ماڈل کے فیصلوں میں سب سے زیادہ اثر انداز عنصر ہے: age۔

## Interpretation

The UCI Adult Income dataset is a well-known benchmark in fairness research. The income prediction task (`>50K` vs `<=50K`) is known to exhibit strong gender and age disparities in the underlying census data.

Insaaf AI correctly identified:

1. **Severe disparate impact** — males earn >50K at 3.2× the rate of females (DIR = 0.31, well below the 0.80 threshold). This is consistent with the known gender wage gap in 1994 US census data.
2. **Gender as a top SHAP feature** — ranked 2nd, confirming the model uses gender either directly or through correlated features (occupation, hours_per_week).
3. **Equal Opportunity Difference = 0.0** — both groups achieve perfect true-positive rates among those who actually earn >50K, so there is no TPR disparity. The bias manifests purely in base-rate differences (disparate impact), not in differential accuracy.

The Trust Score of **60/100** (not certified) reflects the two applicable penalties: DIR failure (−25) and protected attribute in top SHAP features (−15).

## Reproduction

```bash
# 1. Prepare dataset
cd backend
python data/prepare_uci_adult.py

# 2. Run audit via the API (server must be running on port 8899)
curl -X POST http://127.0.0.1:8899/api/audit \
  -F "file=@data/uci_adult_income.csv" \
  -F "protected_attribute=gender" \
  -F "privileged_value=male" \
  -F "positive_outcome_value=approved" \
  -F "ground_truth_column=loan_approved"
```
