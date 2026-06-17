"""Entrypoint: ``python -m gpuinfo_nvidia`` runs the uvicorn server.

Host/port/log-level come from the environment so the container needs no args:
  GPUINFO_HOST       (default 0.0.0.0)
  GPUINFO_PORT       (default 8000)
  GPUINFO_LOG_LEVEL  (default info - shows startup, serving and detected hardware)

Access logging is off: the hub polls /health and /gpus every ~30s, so per-request
lines would bury the useful startup/serving/hardware logs.
"""

import os


def main():
    import uvicorn

    uvicorn.run(
        "gpuinfo_nvidia.app:app",
        host=os.environ.get("GPUINFO_HOST", "0.0.0.0"),
        port=int(os.environ.get("GPUINFO_PORT", "8000")),
        log_level=os.environ.get("GPUINFO_LOG_LEVEL", "info"),
        access_log=False,
    )


if __name__ == "__main__":
    main()
