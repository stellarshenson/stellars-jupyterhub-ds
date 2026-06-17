# GPU-info sidecar (NVIDIA). Two stages: build+test the wheel on a slim Python
# image (no GPU needed - the parse tests mock nvidia-smi), then install it into a
# runtime on the NVIDIA CUDA base so nvidia-smi is available via the nvidia
# container runtime. Build context is the repo root (see compose.yml).
#
# The CUDA base is parameterised so this sidecar tracks the platform's GPU base
# image (JUPYTERHUB_GPUINFO_NVIDIA_BASE_IMAGE).
ARG NVIDIA_BASE_IMAGE=nvidia/cuda:13.0.2-base-ubuntu24.04

##############################################################################
# STAGE 1 - build + test the wheel (tests gate the image build)
##############################################################################
FROM python:3.12-slim-bookworm AS builder

RUN pip install --no-cache-dir build
COPY services/jupyterhub/gpuinfo-nvidia /src/gpuinfo-nvidia
RUN python -m build /src/gpuinfo-nvidia --outdir /dist
RUN pip install --no-cache-dir /dist/gpuinfo_nvidia-*.whl pytest httpx \
    && pytest /src/gpuinfo-nvidia/tests -v

##############################################################################
# STAGE 2 - runtime on the CUDA base (nvidia-smi via nvidia runtime)
##############################################################################
FROM ${NVIDIA_BASE_IMAGE} AS target

LABEL maintainer="Konrad Jelen <konrad.jelen@delaval.com>"
LABEL org.opencontainers.image.title="gpuinfo-nvidia"
LABEL org.opencontainers.image.description="Vendor-neutral GPU-info sidecar API (NVIDIA implementation)"

ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update \
    && apt-get install -y --no-install-recommends python3 python3-venv \
    && rm -rf /var/lib/apt/lists/*

# Isolated venv (the CUDA base is externally-managed under PEP 668).
ENV VIRTUAL_ENV=/opt/venv
RUN python3 -m venv $VIRTUAL_ENV
ENV PATH="$VIRTUAL_ENV/bin:$PATH"

COPY --from=builder /dist/*.whl /tmp/
RUN pip install --no-cache-dir /tmp/*.whl && rm -f /tmp/*.whl

# nvidia container runtime needs these to expose the driver + nvidia-smi.
ENV NVIDIA_VISIBLE_DEVICES=all
ENV NVIDIA_DRIVER_CAPABILITIES=utility
ENV GPUINFO_PORT=8000

EXPOSE 8000
CMD ["python", "-m", "gpuinfo_nvidia"]
