@echo off
echo ========================================
echo RIFT Agent - Docker Image Builder
echo ========================================
echo.

echo Step 1: Checking Docker...
docker --version
if errorlevel 1 (
    echo ERROR: Docker not found! Please install Docker Desktop.
    pause
    exit /b 1
)

echo.
echo Step 2: Building rift-agent image...
cd /d "%~dp0"
docker build -f docker\Dockerfile.agent -t rift-agent:latest .

if errorlevel 1 (
    echo ERROR: Docker build failed!
    pause
    exit /b 1
)

echo.
echo ========================================
echo SUCCESS! Docker image built.
echo ========================================
echo.
echo You can now run the agent with:
echo   python -m uvicorn app.main:app --reload --port 8000 --reload-dir app
echo.
echo To verify the image:
echo   docker images ^| findstr rift-agent
echo.
pause
