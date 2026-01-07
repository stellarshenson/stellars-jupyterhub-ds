@echo off

REM Change directory to where the script is
cd /d "%~dp0"

REM first pull the jupyterlab and jupyterhub image
docker.exe pull stellars/stellars-jupyterlab-ds:latest
docker.exe pull stellars/stellars-jupyterhub-ds:latest

REM start platform
docker.exe compose --env-file .env -f compose.yml -f compose-gpu.yml up --no-recreate --no-build -d

REM EOF


