import os
import uuid
import logging
import shutil
from contextlib import asynccontextmanager

import pandas as pd
from fastapi import FastAPI, UploadFile, File, Form, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, FileResponse

from causal_engine import CausalInsightEngine
from causal_engine.models import (
    AnalysisResponse,
    CateResponse,
    HealthResponse,
    SessionResponse,
    UploadResponse,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(name)-24s | %(levelname)-6s | %(message)s",
)
logger = logging.getLogger("causal_effect.api")

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting Causal Effect API")
    yield
    if os.path.exists(UPLOAD_DIR):
        shutil.rmtree(UPLOAD_DIR, ignore_errors=True)
        os.makedirs(UPLOAD_DIR, exist_ok=True)
    logger.info("Cleanup complete")


app = FastAPI(
    title="Causal Effect API",
    version="2.0.0",
    description="Causal inference analysis platform — DoWhy + EconML",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://localhost:3000",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

UPLOAD_DIR = os.path.join(os.path.dirname(__file__), "uploads")
SAMPLE_DATA = os.path.join(os.path.dirname(__file__), "sample_causal_data.csv")
os.makedirs(UPLOAD_DIR, exist_ok=True)

MAX_FILE_SIZE = 50 * 1024 * 1024

sessions: dict[str, dict] = {}


def _get_session(session_id: str) -> dict:
    session = sessions.get(session_id)
    if session is None:
        raise HTTPException(404, "Session not found or expired. Re-upload the CSV.")
    return session


def _parse_csv_metadata(filepath: str, filename: str):
    df = pd.read_csv(filepath)
    numeric_cols = df.select_dtypes(include=["number"]).columns.tolist()
    categorical_cols = df.select_dtypes(exclude=["number"]).columns.tolist()
    all_columns = df.columns.tolist()
    sample_data = df.head(10).to_dict(orient="records")

    col_info = {}
    for col in all_columns:
        is_binary = col in numeric_cols and set(df[col].dropna().unique()) <= {0, 1}
        col_info[col] = {
            "dtype": str(df[col].dtype),
            "unique": int(df[col].nunique()),
            "missing": int(df[col].isna().sum()),
            "is_numeric": col in numeric_cols,
            "is_binary": is_binary,
        }
        if col in numeric_cols:
            desc = df[col].describe().to_dict()
            col_info[col]["stats"] = {
                k: float(v) if isinstance(v, (int, float)) else v for k, v in desc.items()
            }

    return df, {
        "filename": filename,
        "rows": len(df),
        "columns": len(all_columns),
        "numeric_columns": numeric_cols,
        "categorical_columns": categorical_cols,
        "all_columns": all_columns,
        "column_info": col_info,
        "sample": sample_data,
    }


async def _handle_upload(file: UploadFile):
    if not file.filename or not file.filename.lower().endswith(".csv"):
        raise HTTPException(400, "Only CSV files accepted")

    content = await file.read()
    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(413, f"File too large. Maximum size is {MAX_FILE_SIZE // (1024*1024)}MB")

    session_id = str(uuid.uuid4())[:8]
    filepath = os.path.join(UPLOAD_DIR, f"{session_id}.csv")

    try:
        with open(filepath, "wb") as f:
            f.write(content)
    except OSError as e:
        logger.error(f"Failed to write upload: {e}")
        raise HTTPException(500, "Failed to save uploaded file")

    try:
        df, metadata = _parse_csv_metadata(filepath, file.filename)
    except Exception as e:
        os.remove(filepath)
        logger.warning(f"CSV parse failed: {e}")
        raise HTTPException(400, f"Failed to parse CSV: {str(e)}")

    sessions[session_id] = {"filepath": filepath, "df": df, "columns": metadata["all_columns"]}
    logger.info(f"Session {session_id}: {metadata['rows']} rows, {metadata['columns']} cols")

    return JSONResponse({"session_id": session_id, **metadata})


def _run_analysis(session_id: str, treatment: str, outcome: str, confounders: str):
    session = _get_session(session_id)
    confounders_list = [c.strip() for c in confounders.split(",") if c.strip()]
    df = session["df"]

    for col in [treatment, outcome] + confounders_list:
        if col not in df.columns:
            raise HTTPException(400, f"Column '{col}' not found in dataset")

    logger.info(f"Analysis start: treatment={treatment}, outcome={outcome}, confounders={confounders_list}")
    try:
        engine = CausalInsightEngine(df)
        results = engine.full_analysis(treatment, outcome, confounders_list)
        sessions[session_id]["config"] = {
            "treatment": treatment,
            "outcome": outcome,
            "confounders": confounders_list,
        }
        logger.info(f"Analysis complete for session {session_id}")
        return JSONResponse({"status": "success", "results": results})
    except ValueError as e:
        logger.error(f"Analysis validation error: {e}")
        raise HTTPException(422, str(e))
    except Exception as e:
        logger.exception(f"Analysis failed for session {session_id}")
        raise HTTPException(500, f"Analysis failed: {str(e)}")


# === Auth middleware (Tip 23) ===
API_TOKEN = os.environ.get("CAUSAL_EFFECT_API_TOKEN")


async def verify_token(authorization: str = None):
    if API_TOKEN is None:
        return True
    if not authorization:
        raise HTTPException(401, "Missing Authorization header")
    scheme, _, token = authorization.partition(" ")
    if scheme.lower() != "bearer" or token != API_TOKEN:
        raise HTTPException(403, "Invalid API token")
    return True


# === Endpoints ===

@app.get("/", tags=["Meta"])
def root():
    return {
        "service": "Causal Effect API",
        "status": "ready",
        "version": "2.0.0",
        "endpoints": {
            "upload": "/upload-csv",
            "analyze": "/analyze",
            "cate": "/cate",
            "health": "/health",
            "docs": "/docs",
        },
    }


@app.get("/health", response_model=HealthResponse, tags=["Meta"])
def health():
    return HealthResponse(status="healthy", active_sessions=len(sessions))


@app.get("/sample-data", tags=["Data"])
def download_sample():
    if not os.path.exists(SAMPLE_DATA):
        raise HTTPException(404, "Sample dataset not found")
    return FileResponse(
        SAMPLE_DATA,
        media_type="text/csv",
        filename="sample_causal_data.csv",
    )


@app.post("/upload-csv", tags=["Data"])
async def upload_csv(file: UploadFile = File(...)):
    return await _handle_upload(file)


@app.post("/upload-metadata", tags=["Data"])
async def upload_metadata(file: UploadFile = File(...)):
    return await _handle_upload(file)


@app.post("/analyze", tags=["Analysis"])
async def analyze(
    session_id: str = Form(...),
    treatment: str = Form(...),
    outcome: str = Form(...),
    confounders: str = Form(...),
):
    return _run_analysis(session_id, treatment, outcome, confounders)


@app.post("/compute-causal-impact", tags=["Analysis"])
async def compute_causal_impact(
    session_id: str = Form(...),
    treatment: str = Form(...),
    outcome: str = Form(...),
    confounders: str = Form(...),
):
    return _run_analysis(session_id, treatment, outcome, confounders)


@app.post("/cate", tags=["Analysis"])
async def cate_analysis(
    session_id: str = Form(...),
    treatment: str = Form(...),
    outcome: str = Form(...),
    confounders: str = Form(...),
    feature: str = Form(...),
):
    session = _get_session(session_id)
    confounders_list = [c.strip() for c in confounders.split(",") if c.strip()]
    df = session["df"]

    for col in [treatment, outcome, feature] + confounders_list:
        if col not in df.columns:
            raise HTTPException(400, f"Column '{col}' not found")

    try:
        engine = CausalInsightEngine(df)
        cate_result = engine.compute_cate_by_feature(
            treatment, outcome, confounders_list, feature
        )
        return JSONResponse({
            "status": "success",
            "feature": feature,
            "cate": cate_result,
        })
    except Exception as e:
        logger.exception("CATE analysis failed")
        raise HTTPException(500, f"CATE analysis failed: {str(e)}")


@app.get("/sessions/{session_id}", tags=["Session"])
def get_session(session_id: str):
    session = _get_session(session_id)
    df = session["df"]
    return {
        "session_id": session_id,
        "rows": len(df),
        "columns": session["columns"],
        "config": session.get("config"),
        "preview": df.head(10).to_dict(orient="records"),
    }


# Cleanup handled via lifespan context manager


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
