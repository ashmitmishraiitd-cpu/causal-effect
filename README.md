# CausalInsight

<p align="center">
  <img src="https://img.shields.io/badge/python-3.12+-blue?logo=python" alt="Python">
  <img src="https://img.shields.io/badge/node-18+-green?logo=node.js" alt="Node">
  <img src="https://img.shields.io/badge/dowhy-0.14-purple" alt="DoWhy">
  <img src="https://img.shields.io/badge/econml-0.16-orange" alt="EconML">
  <img src="https://img.shields.io/badge/license-MIT-brightgreen" alt="License">
  <img src="https://img.shields.io/badge/react-18-61DAFB?logo=react" alt="React">
  <img src="https://img.shields.io/badge/fastapi-latest-009688?logo=fastapi" alt="FastAPI">
</p>

<p align="center">
  <b>A full-stack causal inference analysis platform.</b><br>
  Upload a CSV, map your variables, and get ATE estimates from 5 methods with refutation tests.
</p>

<p align="center">
  <b>FastAPI</b> &bull; <b>DoWhy</b> &bull; <b>EconML</b> &bull; <b>React</b> &bull; <b>TailwindCSS</b> &bull; <b>Recharts</b>
</p>

---

## Overview

CausalInsight makes causal inference accessible through a clean web interface. Upload a dataset, select your treatment, outcome, and confounders, and the platform runs multiple estimation methods in parallel — returning interpretable results with confidence intervals and robustness checks.

### Workflow

```
Upload CSV  →  Map Variables  →  Run Analysis  →  View Results
   │               │                 │                │
   │  Columns,     │  Treatment,     │  5 methods     │  ATE chart,
   │  types,       │  Outcome,       │  + refutations │  CATE dist.,
   │  stats        │  Confounders    │                │  interpretation
```

## Causal Methods

| Method | Description | Treatment Type |
|--------|-------------|----------------|
| **Linear Regression** | Backdoor adjustment via OLS | Any numeric |
| **Propensity Score Matching** | Matching-based ATE estimation | Binary (0/1) |
| **Doubly Robust (IPW)** | Inverse probability weighting | Binary (0/1) |
| **Double ML** | Double machine learning (LinearDML) | Any numeric |
| **Causal Forest** | Heterogeneous treatment effects (CausalForestDML) | Any numeric |

### Refutation Tests

- **Placebo Treatment** — replaces treatment with random noise
- **Data Subset** — runs estimate on a random subset of data
- **Dummy Outcome** — replaces outcome with random noise

## Quick Start

### Prerequisites

- Python 3.12+
- Node.js 18+

### 1. Backend

```bash
cd backend
pip install -r requirements.txt
python -m uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

### 2. Frontend

```bash
cd frontend
npm install
npm run dev
```

### 3. Open

http://localhost:5173

A sample dataset is provided at `backend/sample_causal_data.csv` (1000 rows, known treatment effect = 4.5).

## API Reference

### `POST /upload-csv`

Upload a CSV file. Returns column metadata.

**Response:**
```json
{
  "session_id": "a1b2c3d4",
  "rows": 1000,
  "columns": 9,
  "all_columns": ["age", "treatment", "outcome_score", ...],
  "numeric_columns": ["age", "income", ...],
  "column_info": {
    "treatment": { "dtype": "int64", "unique": 2, "is_binary": true, ... }
  }
}
```

### `POST /analyze`

Run causal analysis with selected variables.

**Form params:** `session_id`, `treatment`, `outcome`, `confounders` (comma-separated)

**Response:**
```json
{
  "status": "success",
  "results": {
    "linear_regression": { "ate": 4.42, "method": "..." },
    "propensity_matching": { "ate": 5.29 },
    "doubly_robust": { "ate": 4.79 },
    "double_ml": { "ate": 4.50, "ate_interval": [3.44, 5.55] },
    "causal_forest": { "ate": 4.18, "ate_interval": [0.25, 8.11], "cate_distribution": {...} },
    "refutations": { "placebo_treatment": {...}, "data_subset": {...}, "dummy_outcome": {...} },
    "summary": { "num_rows": 1000, "treatment": "treatment", "outcome": "outcome_score", "confounders": [...] }
  }
}
```

## Project Structure

```
causal-insight/
├── backend/
│   ├── main.py              # FastAPI server (4 endpoints)
│   ├── causal_engine.py     # DoWhy + EconML analysis pipeline
│   ├── requirements.txt     # Python dependencies
│   ├── sample_causal_data.csv  # Test dataset (1000 rows)
│   └── uploads/             # Temporary CSV storage
├── frontend/
│   ├── src/
│   │   ├── App.jsx          # 3-step wizard routing
│   │   ├── api.js           # API client
│   │   ├── index.css        # Tailwind + custom styles
│   │   └── components/
│   │       ├── FileUpload.jsx       # Drag-and-drop CSV upload
│   │       ├── ColumnMapper.jsx     # Variable mapping form
│   │       ├── ResultsDashboard.jsx # ATE results + refutations
│   │       └── CausalChart.jsx      # Recharts visualizations
│   ├── index.html
│   ├── package.json
│   ├── vite.config.js
│   └── tailwind.config.js
├── .gitignore
├── CONTRIBUTING.md
├── LICENSE
└── README.md
```

## Tech Stack

| Layer | Technology |
|-------|-----------|
| **Backend** | FastAPI, Uvicorn, Python 3.12 |
| **Causal Engine** | DoWhy 0.14, EconML 0.16, scikit-learn |
| **Frontend** | React 18, Vite 6, TailwindCSS 3 |
| **Charts** | Recharts 2 |
| **Icons** | Lucide React |
| **Upload** | react-dropzone |

## Author

**Ashmit Mishra**

## License

MIT — see [LICENSE](LICENSE).

## Acknowledgements

Built with [DoWhy](https://github.com/py-why/dowhy), [EconML](https://github.com/py-why/EconML), and the [UI/UX Pro Max](https://github.com/nextlevelbuilder/ui-ux-pro-max-skill) design system.
