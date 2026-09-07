# Medical Risk XAI

Risk predictions use an auditable, deterministic clinical point engine. The
API returns the rule-engine score and band immediately; XGBoost/SHAP runs in
the background for observability and never changes or delays the clinical
classification. Responses include `total_points`, `point_breakdown`,
`risk_band`, and legacy fields for compatibility.

**medical-risk-xai** is an end-to-end machine learning pipeline for predicting patient medical risk scores using structured clinical datasets. The project leverages XGBoost for high-performance gradient-boosted classification and SHAP (SHapley Additive exPlanations) to provide transparent, interpretable explanations for every prediction. A FastAPI backend exposes model inference and SHAP explanations via a REST API backed by a SQLAlchemy-managed database, while a React/Vite frontend lets clinicians interactively explore risk scores and feature attributions in real time.

## Project Structure

```
medical-risk-xai/
├── data/
│   ├── raw/          # Original, unmodified dataset CSVs
│   └── processed/    # Cleaned, merged, and feature-engineered data
├── notebooks/        # Exploratory Data Analysis (EDA) notebooks
├── src/
│   ├── data_inventory.py       # Scan and catalogue all raw data files
│   ├── schema_mapping.py       # Harmonise column names across datasets
│   ├── build_training_data.py  # Merge + split into train/val/test sets
│   ├── preprocessing.py        # Feature engineering & imputation pipelines
│   ├── train.py                # XGBoost model training & evaluation
│   ├── explain.py              # SHAP explainability generation
│   └── dataset_shift_check.py  # Covariate / label shift detection
├── api/
│   ├── main.py      # FastAPI application entry point
│   ├── schemas.py   # Pydantic request/response models
│   └── database.py  # SQLAlchemy engine, session, and base models
├── frontend/        # Vite + React UI for risk dashboard
└── requirements.txt
```

## One-Command Quick Start (Recommended)

Running `python run_all.py` is the only command needed to get the whole system running end to end.

```bash
# 1. Activate your virtual environment
.venv\Scripts\activate      # Windows
# source .venv/bin/activate # macOS / Linux

# 2. Run the full platform
python run_all.py
```

`run_all.py` automatically:
1. Verifies/trains the ML pipeline (`src/build_training_data.py` &rarr; `src/preprocessing.py` &rarr; `src/train.py`) if `models/best_model.joblib` is missing.
2. Checks and seeds the database with demo admin, doctors, and patients with baseline clinical assessments.
3. Launches the FastAPI backend (`http://127.0.0.1:8000`).
4. Launches the React/Vite frontend (`http://localhost:5173`) only after the
   FastAPI health check succeeds. The frontend calls `/api`, which Vite proxies
   to the authenticated FastAPI backend and its database.
5. Streams all logs live to the terminal and terminates all processes cleanly on `Ctrl+C`.

---

## Manual Service Execution

```bash
# 1. Install dependencies
pip install -r requirements.txt
cd frontend && npm install && cd ..

# 2. Train model pipeline
python src/build_training_data.py
python src/preprocessing.py
python src/train.py

# 3. Seed demo accounts
python scripts/seed_demo_data.py

# 4. Run the API
uvicorn api.main:app --reload --port 8000

# 5. Run the frontend (in a separate terminal)
cd frontend && npm run dev
```
