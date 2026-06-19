# Mock gpuinfo-nvidia sidecar for the functional tests - serves canned /gpus so the
# GPU display tests run deterministically on any host. Built by `make test-functional-gpu`
# and self-started by the hub as its sidecar image (JUPYTERHUB_GPUINFO_NVIDIA_IMAGE).
FROM python:3.12-slim
COPY server.py /server.py
EXPOSE 8000
CMD ["python", "/server.py"]
