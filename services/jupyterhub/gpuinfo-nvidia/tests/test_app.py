"""Tests for the FastAPI endpoints (sampler mocked via the nvidia module)."""

from unittest.mock import patch

from fastapi.testclient import TestClient

from gpuinfo_nvidia import nvidia
from gpuinfo_nvidia.app import app

client = TestClient(app)


def test_health_ok():
    with patch.object(nvidia, "driver_available", return_value=True):
        r = client.get("/health")
    assert r.status_code == 200
    body = r.json()
    assert body == {"status": "ok", "vendor": "nvidia", "driver_available": True}


def test_health_no_driver():
    with patch.object(nvidia, "driver_available", return_value=False):
        r = client.get("/health")
    assert r.status_code == 200
    assert r.json()["driver_available"] is False


def test_gpus_report():
    data = (
        True,
        [
            {
                "index": "0",
                "name": "NVIDIA GeForce RTX 5090",
                "uuid": "GPU-a",
                "utilization": 5,
                "memory_used_mb": 100,
                "memory_total_mb": 1000,
                "processes": [{"pid": 1, "name": "python", "used_memory_mb": 100}],
            }
        ],
    )
    with patch.object(nvidia, "sample", return_value=data):
        r = client.get("/gpus")
    assert r.status_code == 200
    body = r.json()
    assert body["vendor"] == "nvidia"
    assert body["available"] is True
    assert body["count"] == 1
    assert body["gpus"][0]["utilization"] == 5
    assert body["gpus"][0]["processes"][0]["pid"] == 1
    assert "timestamp" in body


def test_gpus_unavailable():
    with patch.object(nvidia, "sample", return_value=(False, [])):
        r = client.get("/gpus")
    assert r.status_code == 200
    body = r.json()
    assert body["available"] is False
    assert body["count"] == 0
    assert body["gpus"] == []
