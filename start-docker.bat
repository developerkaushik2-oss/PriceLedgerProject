@echo off
REM Docker Startup Script for PriceLedger Project (Windows)

setlocal enabledelayedexpansion

echo.
echo ================================
echo PriceLedger Docker Startup
echo ================================
echo.

REM Check if Docker is installed
docker --version >nul 2>&1
if errorlevel 1 (
    echo Docker is not installed. Please install Docker Desktop for Windows.
    exit /b 1
)

REM Check if Docker Compose is installed
docker-compose --version >nul 2>&1
if errorlevel 1 (
    echo Docker Compose is not installed. Please install Docker Desktop for Windows.
    exit /b 1
)

echo Step 1: Building images...
docker-compose build
if errorlevel 1 goto error

echo.
echo Step 2: Starting services...
docker-compose up -d
if errorlevel 1 goto error

echo.
echo Step 3: Waiting for services to be healthy...
timeout /t 10 /nobreak

echo.
echo Step 4: Checking service status...
docker-compose ps

echo.
echo ================================
echo Services are running!
echo ================================
echo.
echo Available endpoints:
echo   API:        http://localhost:5000
echo   API Docs:   http://localhost:5000/api/docs
echo   Health:     http://localhost:5000/api/health
echo   Database:   localhost:5432
echo   Redis:      localhost:6379
echo.
echo Useful commands:
echo   View logs:           docker-compose logs -f
echo   Backend logs:        docker-compose logs -f backend
echo   Worker logs:         docker-compose logs -f celery_worker
echo   Stop services:       docker-compose down
echo   Access database:     docker exec -it priceledger-db psql -U priceledger_user -d priceledger
echo.

goto end

:error
echo.
echo Error occurred during startup. Check the output above for details.
exit /b 1

:end
