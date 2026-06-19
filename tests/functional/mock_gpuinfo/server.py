"""Mock gpuinfo-nvidia sidecar for the functional tests.

Serves the same contract the hub's gpu_client expects - ``GET /gpus`` ->
``{vendor, available, count, gpus[], timestamp}`` with per-GPU
``index/name/uuid/memory_total_mb/utilization/memory_used_mb/temperature_c/power_w``
- with DETERMINISTIC canned values, so the GPU display tests assert stable numbers and
run on any host (no real GPU/driver). Stop this container to exercise the
sidecar-disconnected path (DEF-4). Stdlib only; no dependencies.
"""

import json
import os
from http.server import BaseHTTPRequestHandler, HTTPServer

GPUS = [
    {"index": "0", "name": "NVIDIA RTX A500 Embedded GPU", "uuid": "GPU-mock-0000",
     "memory_total_mb": 4096, "memory_used_mb": 512, "utilization": 12,
     "temperature_c": 41, "power_w": 15.0, "processes": []},
    {"index": "1", "name": "NVIDIA GeForce RTX 5090", "uuid": "GPU-mock-0001",
     "memory_total_mb": 32607, "memory_used_mb": 8000, "utilization": 63,
     "temperature_c": 67, "power_w": 410.0, "processes": []},
    {"index": "2", "name": "NVIDIA RTX 5000 Ada Generation", "uuid": "GPU-mock-0002",
     "memory_total_mb": 32760, "memory_used_mb": 4000, "utilization": 22,
     "temperature_c": 55, "power_w": 120.0, "processes": []},
]

PAYLOAD = {"vendor": "nvidia", "available": True, "count": len(GPUS), "gpus": GPUS, "timestamp": "mock"}


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path.rstrip("/") in ("/gpus", ""):
            body = json.dumps(PAYLOAD).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
        else:
            self.send_response(404)
            self.end_headers()

    def log_message(self, *args):  # quiet - no per-request noise in the container log
        pass


if __name__ == "__main__":
    HTTPServer(("0.0.0.0", int(os.environ.get("PORT", "8000"))), Handler).serve_forever()
