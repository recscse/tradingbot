@echo off
echo Building HFT Trading System Documentation (MkDocs Material)
echo ==========================================================

REM Check if MkDocs is installed
mkdocs --version >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo MkDocs not found. Installing mkdocs-material...
    pip install mkdocs-material
)

echo Building documentation...
mkdocs build

echo Serving documentation locally...
echo Documentation will be available at: http://localhost:8000
mkdocs serve

pause