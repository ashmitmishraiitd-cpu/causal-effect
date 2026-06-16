import os
import sys
import tempfile
import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from main import app

client = TestClient(app)


@pytest.fixture
def sample_csv():
    content = "age,income,education,treatment,outcome_score\n"
    import numpy as np
    rng = np.random.RandomState(42)
    for i in range(100):
        age = rng.uniform(20, 70)
        income = rng.normal(50000, 15000)
        edu = rng.choice([0, 1, 2])
        treat = rng.binomial(1, 0.5)
        outcome = 10 + 4.5 * treat + 0.5 * age + rng.normal(0, 5)
        content += f"{age:.1f},{income:.1f},{edu},{treat},{outcome:.2f}\n"
    tmp = tempfile.NamedTemporaryFile(mode="w", suffix=".csv", delete=False)
    tmp.write(content)
    tmp.close()
    yield tmp.name
    os.unlink(tmp.name)


@pytest.fixture
def session_id(sample_csv):
    with open(sample_csv, "rb") as f:
        resp = client.post("/upload-csv", files={"file": ("test.csv", f, "text/csv")})
    assert resp.status_code == 200
    data = resp.json()
    assert data["rows"] == 100
    return data["session_id"]


def test_health():
    resp = client.get("/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "healthy"


def test_root():
    resp = client.get("/")
    assert resp.status_code == 200
    data = resp.json()
    assert "service" in data


def test_upload_csv(sample_csv):
    with open(sample_csv, "rb") as f:
        resp = client.post("/upload-csv", files={"file": ("test.csv", f, "text/csv")})
    assert resp.status_code == 200
    data = resp.json()
    assert "session_id" in data
    assert data["rows"] == 100


def test_upload_invalid_file():
    resp = client.post("/upload-csv", files={"file": ("test.txt", b"hello", "text/plain")})
    assert resp.status_code == 400


def test_analyze_flow(session_id):
    resp = client.post("/analyze", data={
        "session_id": session_id,
        "treatment": "treatment",
        "outcome": "outcome_score",
        "confounders": "age,income,education",
    })
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "success"
    assert "linear_regression" in data["results"]
    assert "summary" in data["results"]


def test_analyze_missing_column(session_id):
    resp = client.post("/analyze", data={
        "session_id": session_id,
        "treatment": "nonexistent",
        "outcome": "outcome_score",
        "confounders": "age",
    })
    assert resp.status_code == 400


def test_analyze_expired_session():
    resp = client.post("/analyze", data={
        "session_id": "invalid",
        "treatment": "x",
        "outcome": "y",
        "confounders": "z",
    })
    assert resp.status_code == 404


def test_sample_data():
    resp = client.get("/sample-data")
    assert resp.status_code == 200
    assert resp.headers["content-type"] == "text/csv; charset=utf-8" or "text/csv" in resp.headers["content-type"]


def test_get_session(session_id):
    resp = client.get(f"/sessions/{session_id}")
    assert resp.status_code == 200
    assert resp.json()["rows"] == 100
