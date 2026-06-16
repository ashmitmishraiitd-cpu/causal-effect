import asyncio
import logging
import os
import uuid
from concurrent.futures import ThreadPoolExecutor
from functools import partial
from typing import Callable, Optional

import pandas as pd
from fastapi import HTTPException

from .engine import CausalInsightEngine
from .repository import (
    save_session,
    get_session as repo_get_session,
    update_config,
    init_db,
)
from .estimators import (
    LinearRegressionEstimator,
    PropensityMatchingEstimator,
    DoublyRobustEstimator,
    DoubleMLEstimator,
    CausalForestEstimator,
    InstrumentalVariableEstimator,
    BootstrapEstimator,
)

logger = logging.getLogger(__name__)

_executor = ThreadPoolExecutor(max_workers=4)

UPLOAD_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)

_progress_callbacks: dict[str, list] = {}


def register_progress_callback(session_id: str, callback):
    if session_id not in _progress_callbacks:
        _progress_callbacks[session_id] = []
    _progress_callbacks[session_id].append(callback)


def _notify_progress(session_id: str, message: str, pct: float):
    for cb in _progress_callbacks.get(session_id, []):
        try:
            cb({"message": message, "pct": pct})
        except Exception:
            pass


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


def handle_upload(file_content: bytes, filename: str) -> dict:
    if not filename.lower().endswith(".csv"):
        raise HTTPException(400, "Only CSV files accepted")
    session_id = str(uuid.uuid4())[:8]
    filepath = os.path.join(UPLOAD_DIR, f"{session_id}.csv")
    try:
        with open(filepath, "wb") as f:
            f.write(file_content)
    except OSError as e:
        logger.error(f"Failed to write upload: {e}")
        raise HTTPException(500, "Failed to save uploaded file")
    try:
        df, metadata = _parse_csv_metadata(filepath, filename)
    except Exception as e:
        os.remove(filepath)
        logger.warning(f"CSV parse failed: {e}")
        raise HTTPException(400, f"Failed to parse CSV: {str(e)}")
    save_session(session_id, filepath, metadata["all_columns"])
    logger.info(f"Session {session_id}: {metadata['rows']} rows, {metadata['columns']} cols")
    return {"session_id": session_id, **metadata}


def get_session_data(session_id: str) -> dict:
    session = repo_get_session(session_id)
    if session is None:
        raise HTTPException(404, "Session not found or expired. Re-upload the CSV.")
    filepath = session["filepath"]
    if not os.path.exists(filepath):
        raise HTTPException(404, "Uploaded file no longer available. Re-upload.")
    df = pd.read_csv(filepath)
    return {"session": session, "df": df, "filepath": filepath}


def run_analysis(session_id: str, treatment: str, outcome: str, confounders: str,
                 instruments: str = "", frontdoor_mediator: str = "",
                 progress_cb: Optional[Callable] = None) -> dict:
    session_data = get_session_data(session_id)
    df = session_data["df"]
    confounders_list = [c.strip() for c in confounders.split(",") if c.strip()]
    instruments_list = [c.strip() for c in instruments.split(",") if c.strip() and c.strip() != ""]

    for col in [treatment, outcome] + confounders_list + instruments_list:
        if col not in df.columns:
            raise HTTPException(400, f"Column '{col}' not found in dataset")

    if progress_cb:
        progress_cb("Preprocessing data", 5)
    else:
        _notify_progress(session_id, "Preprocessing data", 5)
    engine = CausalInsightEngine(df)

    if instruments_list:
        engine._instruments = instruments_list

    logger.info(f"Analysis start: treatment={treatment}, outcome={outcome}, confounders={confounders_list}")

    try:
        cb = progress_cb if progress_cb else (lambda msg, pct: _notify_progress(session_id, msg, pct))
        results = engine.full_analysis(
            treatment, outcome, confounders_list,
            progress_cb=cb,
        )
        update_config(session_id, {
            "treatment": treatment,
            "outcome": outcome,
            "confounders": confounders_list,
        })
        logger.info(f"Analysis complete for session {session_id}")
        return {"status": "success", "results": results}
    except ValueError as e:
        logger.error(f"Analysis validation error: {e}")
        raise HTTPException(422, str(e))
    except Exception as e:
        logger.exception(f"Analysis failed for session {session_id}")
        raise HTTPException(500, f"Analysis failed: {str(e)}")


def run_analysis_async(session_id: str, treatment: str, outcome: str, confounders: str,
                       instruments: str = ""):
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return run_analysis(session_id, treatment, outcome, confounders, instruments)
    finally:
        loop.close()


def run_cate(session_id: str, treatment: str, outcome: str, confounders: str, feature: str) -> dict:
    session_data = get_session_data(session_id)
    df = session_data["df"]
    confounders_list = [c.strip() for c in confounders.split(",") if c.strip()]

    for col in [treatment, outcome, feature] + confounders_list:
        if col not in df.columns:
            raise HTTPException(400, f"Column '{col}' not found")

    try:
        engine = CausalInsightEngine(df)
        cate_result = engine.compute_cate_by_feature(treatment, outcome, confounders_list, feature)
        return {"status": "success", "feature": feature, "cate": cate_result}
    except Exception as e:
        logger.exception("CATE analysis failed")
        raise HTTPException(500, f"CATE analysis failed: {str(e)}")
