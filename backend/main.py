import os
import json
import logging
import shutil
from contextlib import asynccontextmanager
from typing import Optional

from fastapi import FastAPI, UploadFile, File, Form, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, FileResponse
from fastapi.routing import APIRouter

from causal_engine import (
    CausalInsightEngine,
    init_db,
    session_count,
    cleanup_expired,
    handle_upload,
    get_session_data,
    run_analysis,
    run_cate,
    register_progress_callback,
)
from causal_engine.models import HealthResponse

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(name)-24s | %(levelname)-6s | %(message)s",
)
logger = logging.getLogger("causal_effect.api")

MAX_FILE_SIZE = 50 * 1024 * 1024
SAMPLE_DATA = os.path.join(os.path.dirname(__file__), "sample_causal_data.csv")
UPLOAD_DIR = os.path.join(os.path.dirname(__file__), "uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)

API_TOKEN = os.environ.get("CAUSAL_EFFECT_API_TOKEN")
_ws_clients: dict[str, list[WebSocket]] = {}


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting Causal Effect API")
    init_db()
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
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# === API v1 Router ===
v1 = APIRouter(prefix="/v1", tags=["v1"])

# === API v2 Router ===
v2 = APIRouter(prefix="/v2", tags=["v2"])


async def verify_token(authorization: Optional[str] = None):
    if API_TOKEN is None:
        return True
    if not authorization:
        raise HTTPException(401, "Missing Authorization header")
    scheme, _, token = authorization.partition(" ")
    if scheme.lower() != "bearer" or token != API_TOKEN:
        raise HTTPException(403, "Invalid API token")
    return True


# === WebSocket progress ===
@app.websocket("/ws/{session_id}")
async def websocket_progress(websocket: WebSocket, session_id: str):
    await websocket.accept()
    if session_id not in _ws_clients:
        _ws_clients[session_id] = []
    _ws_clients[session_id].append(websocket)

    def progress_cb(data: dict):
        asyncio_run(websocket.send_json(data))

    register_progress_callback(session_id, progress_cb)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        _ws_clients[session_id].remove(websocket)


def asyncio_run(coro):
    import asyncio
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            asyncio.ensure_future(coro)
        else:
            loop.run_until_complete(coro)
    except RuntimeError:
        asyncio.run(coro)


def _progress_websocket_cb(session_id: str, message: str, pct: float):
    if session_id in _ws_clients:
        payload = json.dumps({"message": message, "pct": pct})
        for ws in _ws_clients[session_id][:]:
            try:
                asyncio_run(ws.send_json({"message": message, "pct": pct}))
            except Exception:
                _ws_clients[session_id].remove(ws)


# === Meta endpoints (unversioned) ===

@app.get("/", tags=["Meta"])
def root():
    return {
        "service": "Causal Effect API",
        "status": "ready",
        "version": "2.0.0",
        "endpoints": {
            "upload": "/upload-csv",
            "analyze": "/v2/analyze",
            "cate": "/v2/cate",
            "health": "/health",
            "docs": "/docs",
        },
    }


@app.get("/health", response_model=HealthResponse, tags=["Meta"])
def health():
    return HealthResponse(status="healthy", active_sessions=session_count())


@app.get("/sample-data", tags=["Data"])
def download_sample():
    if not os.path.exists(SAMPLE_DATA):
        raise HTTPException(404, "Sample dataset not found")
    return FileResponse(SAMPLE_DATA, media_type="text/csv", filename="sample_causal_data.csv")


# === v1 endpoints (legacy compat) ===

@v1.post("/upload-csv")
async def v1_upload_csv(file: UploadFile = File(...)):
    content = await file.read()
    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(413, f"File too large. Maximum size is {MAX_FILE_SIZE // (1024*1024)}MB")
    return JSONResponse(handle_upload(content, file.filename or "upload.csv"))


@v1.post("/analyze")
async def v1_analyze(
    session_id: str = Form(...),
    treatment: str = Form(...),
    outcome: str = Form(...),
    confounders: str = Form(...),
    instruments: str = Form(""),
):
    result = run_analysis(session_id, treatment, outcome, confounders, instruments,
                          progress_cb=lambda m, p: _progress_websocket_cb(session_id, m, p))
    return JSONResponse(result)


@v1.post("/cate")
async def v1_cate(
    session_id: str = Form(...),
    treatment: str = Form(...),
    outcome: str = Form(...),
    confounders: str = Form(...),
    feature: str = Form(...),
):
    return JSONResponse(run_cate(session_id, treatment, outcome, confounders, feature))


# === v2 endpoints (current) ===

@v2.post("/upload-csv")
async def v2_upload_csv(file: UploadFile = File(...)):
    content = await file.read()
    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(413, f"File too large. Maximum size is {MAX_FILE_SIZE // (1024*1024)}MB")
    return JSONResponse(handle_upload(content, file.filename or "upload.csv"))


@v2.post("/analyze")
async def v2_analyze(
    session_id: str = Form(...),
    treatment: str = Form(...),
    outcome: str = Form(...),
    confounders: str = Form(...),
    instruments: str = Form(""),
):
    result = run_analysis(session_id, treatment, outcome, confounders, instruments,
                          progress_cb=lambda m, p: _progress_websocket_cb(session_id, m, p))
    return JSONResponse(result)


@v2.post("/cate")
async def v2_cate(
    session_id: str = Form(...),
    treatment: str = Form(...),
    outcome: str = Form(...),
    confounders: str = Form(...),
    feature: str = Form(...),
):
    return JSONResponse(run_cate(session_id, treatment, outcome, confounders, feature))


@v2.get("/sessions/{session_id}")
def v2_get_session(session_id: str):
    data = get_session_data(session_id)
    df = data["df"]
    return {
        "session_id": session_id,
        "rows": len(df),
        "columns": data["session"]["columns"],
        "config": data["session"].get("config"),
        "preview": df.head(10).to_dict(orient="records"),
    }


app.include_router(v1)
app.include_router(v2)


# === Legacy unversioned endpoints (redirect to v2) ===

@app.post("/upload-csv")
async def upload_csv(file: UploadFile = File(...)):
    return await v2_upload_csv(file)


@app.post("/upload-metadata")
async def upload_metadata(file: UploadFile = File(...)):
    return await v2_upload_csv(file)


@app.post("/analyze")
async def analyze(
    session_id: str = Form(...),
    treatment: str = Form(...),
    outcome: str = Form(...),
    confounders: str = Form(...),
    instruments: str = Form(""),
):
    return await v2_analyze(session_id, treatment, outcome, confounders, instruments)


@app.post("/compute-causal-impact")
async def compute_causal_impact(
    session_id: str = Form(...),
    treatment: str = Form(...),
    outcome: str = Form(...),
    confounders: str = Form(...),
    instruments: str = Form(""),
):
    return await v2_analyze(session_id, treatment, outcome, confounders, instruments)


@app.post("/cate")
async def cate_analysis(
    session_id: str = Form(...),
    treatment: str = Form(...),
    outcome: str = Form(...),
    confounders: str = Form(...),
    feature: str = Form(...),
):
    return await v2_cate(session_id, treatment, outcome, confounders, feature)


@app.get("/sessions/{session_id}")
def get_session(session_id: str):
    return v2_get_session(session_id)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
