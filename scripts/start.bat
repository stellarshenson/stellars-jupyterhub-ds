@echo off

REM Change directory to where the script is
cd /d "%~dp0"

docker.exe compose --env-file ..\.env -f ..\compose.yml up --no-recreate --no-build -d

REM EOF


