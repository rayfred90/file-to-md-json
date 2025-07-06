#!/bin/bash

# Document Converter - Service Shutdown Script
# This script stops both MinIO and Flask services

echo "🛑 Stopping Document Converter Services..."
echo "========================================="

# Set colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Function to kill process by PID file
kill_by_pidfile() {
    local service_name=$1
    local pidfile=$2
    
    if [ -f "$pidfile" ]; then
        local pid=$(cat "$pidfile")
        if kill -0 "$pid" 2>/dev/null; then
            echo -e "${BLUE}🛑 Stopping $service_name (PID: $pid)...${NC}"
            kill "$pid"
            sleep 2
            if kill -0 "$pid" 2>/dev/null; then
                echo -e "${YELLOW}   Force killing $service_name...${NC}"
                kill -9 "$pid"
            fi
            echo -e "${GREEN}✅ $service_name stopped${NC}"
        else
            echo -e "${YELLOW}⚠️  $service_name PID not running${NC}"
        fi
        rm -f "$pidfile"
    else
        echo -e "${YELLOW}⚠️  No PID file found for $service_name${NC}"
    fi
}

# Stop services using PID files
kill_by_pidfile "Flask" "/tmp/flask.pid"
kill_by_pidfile "MinIO" "/tmp/minio.pid"

# Kill any remaining processes by name/port
echo -e "${BLUE}🧹 Cleaning up remaining processes...${NC}"

# Kill Flask processes
pkill -f "python3 app.py" 2>/dev/null && echo -e "${GREEN}✅ Killed remaining Flask processes${NC}" || echo -e "${YELLOW}⚠️  No Flask processes found${NC}"

# Kill MinIO processes
pkill -f "minio server" 2>/dev/null && echo -e "${GREEN}✅ Killed remaining MinIO processes${NC}" || echo -e "${YELLOW}⚠️  No MinIO processes found${NC}"

# Kill by ports as last resort
for port in 5000 9000 9001; do
    if lsof -ti:$port > /dev/null 2>&1; then
        echo -e "${BLUE}🔫 Killing process on port $port...${NC}"
        lsof -ti:$port | xargs kill -9 2>/dev/null || true
        echo -e "${GREEN}✅ Port $port cleared${NC}"
    fi
done

echo -e "${GREEN}"
echo "🎉 All services stopped successfully!"
echo "======================================"
echo -e "${NC}"
