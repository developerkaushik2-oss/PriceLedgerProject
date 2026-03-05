#!/bin/bash
# Docker Startup Script for PriceLedger Project

set -e

echo "================================"
echo "PriceLedger Docker Startup"
echo "================================"
echo ""

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check if Docker is installed
if ! command -v docker &> /dev/null; then
    echo -e "${RED}Docker is not installed. Please install Docker first.${NC}"
    exit 1
fi

# Check if Docker Compose is installed
if ! command -v docker-compose &> /dev/null; then
    echo -e "${RED}Docker Compose is not installed. Please install Docker Compose first.${NC}"
    exit 1
fi

echo -e "${YELLOW}Step 1: Building images...${NC}"
docker-compose build

echo ""
echo -e "${YELLOW}Step 2: Starting services...${NC}"
docker-compose up -d

echo ""
echo -e "${YELLOW}Step 3: Waiting for services to be healthy...${NC}"
sleep 10

echo ""
echo -e "${YELLOW}Step 4: Checking service status...${NC}"
docker-compose ps

echo ""
echo -e "${GREEN}================================${NC}"
echo -e "${GREEN}Services are running!${NC}"
echo -e "${GREEN}================================${NC}"
echo ""
echo "Available endpoints:"
echo "  API:        http://localhost:5000"
echo "  API Docs:   http://localhost:5000/api/docs"
echo "  Health:     http://localhost:5000/api/health"
echo "  Database:   localhost:5432"
echo "  Redis:      localhost:6379"
echo ""
echo "Useful commands:"
echo "  View logs:           docker-compose logs -f"
echo "  Backend logs:        docker-compose logs -f backend"
echo "  Worker logs:         docker-compose logs -f celery_worker"
echo "  Stop services:       docker-compose down"
echo "  Access database:     docker exec -it priceledger-db psql -U priceledger_user -d priceledger"
echo ""
