#!/bin/bash

# Document Converter - Service Stop Script
# This script stops MinIO and Flask services

echo "🛑 Stopping Document Converter Services..."
echo "========================================="

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to kill process by PID
kill_process() {
    local pid=$1
    local service_name=$2
    
    if [ -n "$pid" ] && kill -0 "$pid" 2>/dev/null; then
        echo -e "${BLUE}🔄 Stopping $service_name (PID: $pid)...${NC}"
        kill "$pid" 2>/dev/null
        sleep 2
        
        # Force kill if still running
        if kill -0 "$pid" 2>/dev/null; then
            echo -e "${YELLOW}⚠️  Force killing $service_name...${NC}"
            kill -9 "$pid" 2>/dev/null
        fi
        
        if ! kill -0 "$pid" 2>/dev/null; then
            echo -e "${GREEN}✅ $service_name stopped${NC}"
        else
            echo -e "${RED}❌ Failed to stop $service_name${NC}"
        fi
    else
        echo -e "${YELLOW}⚠️  $service_name not running (PID: $pid)${NC}"
    fi
}

# Function to kill processes on port
kill_port() {
    local port=$1
    local service_name=$2
    
    if lsof -Pi :$port -sTCP:LISTEN -t >/dev/null 2>&1; then
        echo -e "${BLUE}🔄 Killing processes on port $port ($service_name)...${NC}"
        lsof -ti:$port | xargs kill -9 2>/dev/null || true
        sleep 1
        
        if ! lsof -Pi :$port -sTCP:LISTEN -t >/dev/null 2>&1; then
            echo -e "${GREEN}✅ Port $port freed${NC}"
        else
            echo -e "${RED}❌ Failed to free port $port${NC}"
        fi
    fi
}

# Stop Flask application
if [ -f ".flask_pid" ]; then
    FLASK_PID=$(cat .flask_pid)
    kill_process "$FLASK_PID" "Flask"
    rm -f .flask_pid
else
    echo -e "${YELLOW}⚠️  Flask PID file not found, trying port-based stop...${NC}"
fi

# Stop by port just in case
kill_port 5000 "Flask"

# Stop MinIO server
if [ -f ".minio_pid" ]; then
    MINIO_PID=$(cat .minio_pid)
    kill_process "$MINIO_PID" "MinIO"
    rm -f .minio_pid
else
    echo -e "${YELLOW}⚠️  MinIO PID file not found, trying port-based stop...${NC}"
fi

# Stop MinIO by port
kill_port 9000 "MinIO API"
kill_port 9001 "MinIO Console"

# Also try to kill any remaining minio processes
pkill -f "minio server" 2>/dev/null || true

echo ""
echo -e "${GREEN}🎉 All services stopped successfully!${NC}"
echo -e "${BLUE}💡 Services can be restarted with: ./start_services.sh${NC}"
