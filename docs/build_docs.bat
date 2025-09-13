@echo off
echo Building HFT Trading System Documentation
echo =========================================

REM Check if GitBook CLI is installed
gitbook --version >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo GitBook CLI not found. Installing...
    npm install -g gitbook-cli
)

echo Installing GitBook plugins...
gitbook install

echo Building documentation...
gitbook build

echo Serving documentation locally...
echo Documentation will be available at: http://localhost:4000
gitbook serve

pause