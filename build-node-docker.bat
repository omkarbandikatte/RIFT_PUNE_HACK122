@echo off
REM Build Node.js Docker image for RIFT Agent

echo ================================================
echo   Building Node.js Agent Docker Image
echo ================================================
echo.

REM Check if Docker is running
docker --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Docker is not installed or not in PATH
    echo Please install Docker Desktop and try again
    pause
    exit /b 1
)

REM Navigate to project root
cd /d %~dp0..

echo Building rift-agent-node:latest...
echo.

docker build -f backend\docker\Dockerfile.agent.node -t rift-agent-node:latest backend

if errorlevel 1 (
    echo.
    echo ERROR: Docker build failed!
    echo Check the error messages above
    pause
    exit /b 1
)

echo.
echo ================================================
echo   Node.js Image Built Successfully!
echo ================================================
echo.
echo Image: rift-agent-node:latest
echo.

REM Show image details
docker images rift-agent-node:latest

echo.
echo You can now run JavaScript/TypeScript projects!
echo.
pause
