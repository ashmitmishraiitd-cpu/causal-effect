from pydantic import BaseModel, Field
from typing import Optional, Union
from datetime import datetime


class UploadResponse(BaseModel):
    session_id: str
    filename: str
    rows: int
    columns: int
    numeric_columns: list[str]
    categorical_columns: list[str]
    all_columns: list[str]
    column_info: dict
    sample: list[dict]


class AnalysisRequest(BaseModel):
    session_id: str = Field(..., min_length=4, max_length=64)
    treatment: str = Field(..., min_length=1)
    outcome: str = Field(..., min_length=1)
    confounders: list[str] = Field(..., min_length=1)


class MethodResult(BaseModel):
    ate: Optional[float] = None
    ate_interval: Optional[list[float]] = None
    method: str
    error: Optional[str] = None
    cate_distribution: Optional[dict] = None
    cate_samples: Optional[list[float]] = None


class RefutationResult(BaseModel):
    original_estimate: Optional[float] = None
    new_estimate: Optional[float] = None
    p_value: Optional[float] = None
    error: Optional[str] = None


class SummaryResult(BaseModel):
    dataset_shape: list[int]
    raw_rows: int
    treatment: str
    outcome: str
    confounders: list[str]
    treatment_type: str
    outcome_type: str
    missing_values: int
    rows_dropped: int
    num_rows: int
    is_binary_treatment: bool
    treatment_stats: Optional[dict] = None
    outcome_stats: Optional[dict] = None


class AnalysisResponse(BaseModel):
    status: str
    results: dict[str, Union[MethodResult, dict]]


class CateRequest(BaseModel):
    session_id: str
    treatment: str
    outcome: str
    confounders: list[str]
    feature: str


class CateResponse(BaseModel):
    status: str
    feature: str
    cate: dict


class SessionResponse(BaseModel):
    session_id: str
    rows: int
    columns: int
    config: Optional[dict] = None
    preview: list[dict]
    created_at: Optional[str] = None


class HealthResponse(BaseModel):
    status: str
    active_sessions: int
    timestamp: str = Field(default_factory=lambda: datetime.now().isoformat())
    version: str = "2.0.0"
