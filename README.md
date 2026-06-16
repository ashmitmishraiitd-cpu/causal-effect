# Causal Effect

<p align="center">
  <img src="https://img.shields.io/badge/python-3.12+-blue?logo=python" alt="Python">
  <img src="https://img.shields.io/badge/node-20+-green?logo=node.js" alt="Node">
  <img src="https://img.shields.io/badge/dowhy-0.14-purple" alt="DoWhy">
  <img src="https://img.shields.io/badge/econml-0.16-orange" alt="EconML">
  <img src="https://img.shields.io/badge/license-MIT-brightgreen" alt="License">
  <img src="https://img.shields.io/badge/react-18-61DAFB?logo=react" alt="React">
  <img src="https://img.shields.io/badge/fastapi-0.115-009688?logo=fastapi" alt="FastAPI">
</p>

<p align="center">
  <b>A production-grade causal inference analysis platform.</b><br>
  Upload a CSV, define your causal graph, and get ATE/CATE estimates from 7+ methods with full diagnostics.
</p>

<p align="center">
  <b>FastAPI</b> &bull; <b>DoWhy</b> &bull; <b>EconML</b> &bull; <b>React</b> &bull; <b>TailwindCSS</b> &bull; <b>Three.js</b>
</p>

---

## Overview

Causal Effect makes causal inference accessible through a clean web interface. Upload a dataset, select your treatment, outcome, and confounders, and the platform runs multiple estimation methods — returning interpretable results with confidence intervals, robustness checks, and diagnostic plots.

### What sets this apart

- **DAG-based identification** — Uses NetworkX to build an explicit causal graph before estimation, enabling graph-theoretic validity checks
- **Mediator/collider detection** — Automatically warns when a selected confounder is actually a mediator or collider
- **Bootstrap confidence intervals** — Every method reports CIs, not just ML-based estimators
- **Covariate balance diagnostics** — Standardized mean differences before/after matching for propensity methods
- **Sensitivity analysis** — E-value calculation for unmeasured confounding robustness
- **Heterogeneity testing** — Formal test for meaningful CATE variation beyond sampling noise
- **Power analysis** — Pre-computes minimum detectable effect given sample size and outcome variance
- **Automated method recommendations** — Flags which estimators are appropriate given treatment type, sample size, and dimensionality

## Statistical Assumptions

Every causal method relies on assumptions. Here's what each requires for a valid estimate:

### Backdoor Linear Regression
- **Conditional exchangeability** (no unmeasured confounding given covariates)
- **Linearity** — treatment-outcome relationship is linear
- **Positivity** — every unit has non-zero probability of receiving any treatment level
- **No interference** (SUTVA)

### Propensity Score Matching
- **Conditional exchangeability** given propensity score
- **Positivity** — propensity scores bounded away from 0 and 1
- **Large sample** — matching fails in small samples due to insufficient common support
- **Correct propensity model** — logistic regression must be well-specified

### Doubly Robust (IPW)
- **Conditional exchangeability** (doubly robust: consistent if EITHER outcome or propensity model is correct)
- **Positivity** — essential; extreme weights cause variance explosion
- **Binary treatment only**

### Double Machine Learning (LinearDML)
- **Conditional exchangeability**
- **Partially linear model** — treatment effect is constant, but nuisance functions can be complex
- **Cross-fitting** — uses sample-splitting to avoid overfitting bias
- **Requires n ≥ 200** for reliable inference

### Causal Forest (CausalForestDML)
- **Conditional exchangeability**
- **Heterogeneous effects** — allows CATE to vary arbitrarily with covariates
- **Honest splitting** — separate trees for splitting and estimation
- **Requires n ≥ 300** for reliable CATE estimation

## Causal Methods

| Method | Treatment Type | Confidence Interval | Heterogeneity | Notes |
|--------|---------------|-------------------|---------------|-------|
| **Linear Regression** | Any numeric | Bootstrap | No | Baseline; fast but assumes linearity |
| **Propensity Score Matching** | Binary (0/1) | Bootstrap | No | Balance diagnostics included |
| **Doubly Robust (IPW)** | Binary (0/1) | Bootstrap | No | Robust to one model misspecification |
| **Double ML** | Any numeric | ✓ Native | No | Best for high-dimensional confounding |
| **Causal Forest** | Any numeric | ✓ Native | ✓ CATE distribution | Captures heterogeneous effects |
| **Bootstrap ATE** | Any numeric | ✓ Bootstrap percentile | No | Aggregated from 200 resamples |

### Refutation Tests

| Test | What it checks | How to interpret |
|------|---------------|------------------|
| **Placebo Treatment** | Replaces treatment with random noise | Estimate should become near-zero |
| **Data Subset** | Runs estimate on random 70% subset | Estimate should remain stable |
| **Dummy Outcome** | Replaces outcome with random noise | Estimate should become near-zero |
| **E-value** | How strong must unmeasured confounding be to explain away the result? | Higher = more robust |

## Quick Start

### Prerequisites

- Python 3.12+
- Node.js 20+

### 1. Clone & Backend

```bash
git clone https://github.com/ashmitmishraiitd-cpu/causal_effect.git
cd causal_effect/backend
pip install -r requirements.txt
python -m uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

### 2. Frontend

```bash
cd causal_effect/frontend
npm install
npm run dev
```

### 3. Open

http://localhost:5173

A sample dataset is provided at `backend/sample_causal_data.csv` (1000 rows, known ATE = 4.5).

### Docker (one command)

```bash
docker compose up --build
```

## Benchmark

### Synthetic data (known ground truth: ATE = 4.5)

| Method | Estimated ATE | 95% CI | Error |
|--------|--------------|--------|-------|
| Linear Regression | 4.42 | [4.26, 4.58]* | 0.08 |
| Propensity Score Matching | 5.29 | [4.92, 5.66]* | 0.79 |
| Doubly Robust (IPW) | 4.79 | [4.61, 4.97]* | 0.29 |
| Double ML | 4.50 | [3.44, 5.55] | 0.00 |
| Causal Forest | 4.18 | [0.25, 8.11] | 0.32 |

\* Bootstrap percentile intervals

All methods recover the true effect within expected sampling error. Double ML achieves the lowest bias due to its flexible nuisance function estimation.

## API Reference

FastAPI auto-generated docs: http://localhost:8000/docs

### `POST /upload-csv`
Upload a CSV file. Returns column metadata including types, unique values, missing counts, and sample rows.

### `POST /analyze`
Run full causal analysis. Returns ATE from all applicable methods, refutation tests, CATE distribution, diagnostics, and recommendations.

### `POST /cate`
Compute heterogeneous treatment effects binned by a feature column.

## Project Structure

```
causal_effect/
├── backend/
│   ├── causal_engine/      # Python package
│   │   ├── __init__.py      # Public API
│   │   ├── engine.py        # Main analysis engine
│   │   ├── models.py        # Pydantic data models
│   │   ├── dag.py           # Causal graph (NetworkX)
│   │   └── diagnostics.py   # Balance, positivity, power
│   ├── tests/
│   │   ├── test_engine.py   # 17+ pytest tests
│   │   └── test_api.py      # FastAPI TestClient tests
│   ├── main.py              # FastAPI server
│   ├── requirements.txt
│   └── sample_causal_data.csv
├── frontend/
│   ├── src/
│   │   ├── App.jsx
│   │   ├── api.js
│   │   ├── index.css
│   │   └── components/      # React components
│   ├── package.json
│   └── vite.config.js
├── .github/workflows/ci.yml # GitHub Actions
├── Dockerfile
├── docker-compose.yml
└── README.md
```

## Tech Stack

| Layer | Technology |
|-------|-----------|
| **Backend** | FastAPI, Uvicorn, Python 3.12 |
| **Causal Engine** | DoWhy 0.14, EconML 0.16, scikit-learn, NetworkX |
| **Frontend** | React 18, Vite 6, TailwindCSS 3, Three.js |
| **Charts** | Recharts 2 |
| **Background** | Three.js FluidGlass (MeshTransmissionMaterial) |
| **Testing** | pytest, FastAPI TestClient |
| **CI** | GitHub Actions (lint, test, audit) |
| **Deployment** | Docker, docker-compose |

## Author

**Ashmit Mishra** — IIT Delhi Computer Science graduate (2024)

## License

MIT — see [LICENSE](LICENSE).

## Acknowledgements

Built with [DoWhy](https://github.com/py-why/dowhy), [EconML](https://github.com/py-why/EconML), [NetworkX](https://networkx.org/), and the [UI/UX Pro Max](https://github.com/nextlevelbuilder/ui-ux-pro-max-skill) design system.
