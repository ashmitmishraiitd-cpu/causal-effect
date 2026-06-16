import os
import uuid
import pandas as pd
from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, FileResponse
from causal_engine import CausalInsightEngine

app = FastAPI(
    title="CausalInsight API",
    version="2.0.0",
    description="Interactive Enterprise Causal Inference Platform",
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

sessions = {}


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
    if not file.filename.lower().endswith(".csv"):
        raise HTTPException(400, "Only CSV files accepted")

    session_id = str(uuid.uuid4())[:8]
    filepath = os.path.join(UPLOAD_DIR, f"{session_id}.csv")

    content = await file.read()
    with open(filepath, "wb") as f:
        f.write(content)

    try:
        df, metadata = _parse_csv_metadata(filepath, file.filename)
    except Exception as e:
        os.remove(filepath)
        raise HTTPException(400, f"Failed to parse CSV: {str(e)}")

    sessions[session_id] = {"filepath": filepath, "df": df, "columns": metadata["all_columns"]}

    return JSONResponse({"session_id": session_id, **metadata})


def _run_analysis(session_id: str, treatment: str, outcome: str, confounders: str):
    if session_id not in sessions:
        raise HTTPException(400, "Session expired or invalid. Re-upload the CSV.")

    confounders_list = [c.strip() for c in confounders.split(",") if c.strip()]
    session = sessions[session_id]
    df = session["df"]

    for col in [treatment, outcome] + confounders_list:
        if col not in df.columns:
            raise HTTPException(400, f"Column '{col}' not found in dataset")

    try:
        engine = CausalInsightEngine(df)
        results = engine.full_analysis(treatment, outcome, confounders_list)
        sessions[session_id]["config"] = {
            "treatment": treatment,
            "outcome": outcome,
            "confounders": confounders_list,
        }
        return JSONResponse({"status": "success", "results": results})
    except Exception as e:
        raise HTTPException(500, f"Analysis failed: {str(e)}")


@app.get("/")
def root():
    return {
        "service": "CausalInsight API",
        "status": "ready",
        "version": "2.0.0",
        "endpoints": {
            "upload": ["/upload-csv", "/upload-metadata"],
            "analyze": ["/analyze", "/compute-causal-impact"],
            "cate": "/cate",
            "health": "/health",
        },
    }


@app.get("/health")
def health():
    return {"status": "healthy", "active_sessions": len(sessions)}


@app.get("/sample-data")
def download_sample():
    if not os.path.exists(SAMPLE_DATA):
        raise HTTPException(404, "Sample dataset not found")
    return FileResponse(
        SAMPLE_DATA,
        media_type="text/csv",
        filename="sample_causal_data.csv",
    )


@app.post("/upload-csv")
async def upload_csv(file: UploadFile = File(...)):
    return await _handle_upload(file)


@app.post("/upload-metadata")
async def upload_metadata(file: UploadFile = File(...)):
    return await _handle_upload(file)


@app.post("/analyze")
async def analyze(
    session_id: str = Form(...),
    treatment: str = Form(...),
    outcome: str = Form(...),
    confounders: str = Form(...),
):
    return _run_analysis(session_id, treatment, outcome, confounders)


@app.post("/compute-causal-impact")
async def compute_causal_impact(
    session_id: str = Form(...),
    treatment: str = Form(...),
    outcome: str = Form(...),
    confounders: str = Form(...),
):
    return _run_analysis(session_id, treatment, outcome, confounders)


@app.post("/cate")
async def cate_analysis(
    session_id: str = Form(...),
    treatment: str = Form(...),
    outcome: str = Form(...),
    confounders: str = Form(...),
    feature: str = Form(...),
):
    if session_id not in sessions:
        raise HTTPException(400, "Session expired or invalid.")

    confounders_list = [c.strip() for c in confounders.split(",") if c.strip()]
    session = sessions[session_id]
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
        raise HTTPException(500, f"CATE analysis failed: {str(e)}")


@app.get("/sessions/{session_id}")
def get_session(session_id: str):
    if session_id not in sessions:
        raise HTTPException(404, "Session not found")

    session = sessions[session_id]
    df = session["df"]
    return {
        "session_id": session_id,
        "rows": len(df),
        "columns": session["columns"],
        "config": session.get("config"),
        "preview": df.head(10).to_dict(orient="records"),
    }


@app.on_event("shutdown")
def cleanup():
    import shutil
    if os.path.exists(UPLOAD_DIR):
        shutil.rmtree(UPLOAD_DIR, ignore_errors=True)
        os.makedirs(UPLOAD_DIR, exist_ok=True)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
