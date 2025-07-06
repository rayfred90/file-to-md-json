#!/bin/bash

# Document Converter - Complete Startup Script
# This script starts both MinIO and Flask services

echo "🚀 Starting Document Converter Services..."
echo "=========================================="

# Set colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Function to check if a service is running
check_service() {
    local service_name=$1
    local port=$2
    if lsof -i:$port > /dev/null 2>&1; then
        echo -e "${GREEN}✅ $service_name is already running on port $port${NC}"
        return 0
    else
        echo -e "${YELLOW}⚠️  $service_name is not running on port $port${NC}"
        return 1
    fi
}

# Function to wait for service to start
wait_for_service() {
    local service_name=$1
    local port=$2
    local max_attempts=30
    local attempt=1
    
    echo -e "${BLUE}⏳ Waiting for $service_name to start on port $port...${NC}"
    
    while [ $attempt -le $max_attempts ]; do
        if lsof -i:$port > /dev/null 2>&1; then
            echo -e "${GREEN}✅ $service_name is ready!${NC}"
            return 0
        fi
        echo -e "${YELLOW}   Attempt $attempt/$max_attempts...${NC}"
        sleep 2
        ((attempt++))
    done
    
    echo -e "${RED}❌ $service_name failed to start after $max_attempts attempts${NC}"
    return 1
}

# Kill any existing processes on our ports
echo -e "${BLUE}🧹 Cleaning up existing processes...${NC}"
pkill -f "minio server" 2>/dev/null || true
lsof -ti:9000 | xargs kill -9 2>/dev/null || true
lsof -ti:9001 | xargs kill -9 2>/dev/null || true
lsof -ti:5000 | xargs kill -9 2>/dev/null || true
sleep 2

# Start MinIO server
echo -e "${BLUE}🗄️  Starting MinIO server...${NC}"
cd /home/adebo/con/minio_storage
if [ ! -f "start-minio.sh" ]; then
    echo -e "${RED}❌ MinIO start script not found!${NC}"
    exit 1
fi

chmod +x start-minio.sh
./start-minio.sh &
MINIO_PID=$!

# Wait for MinIO to be ready
if wait_for_service "MinIO" 9000; then
    echo -e "${GREEN}✅ MinIO server started successfully${NC}"
    echo -e "${BLUE}   MinIO Console: http://localhost:9001${NC}"
    echo -e "${BLUE}   MinIO API: http://localhost:9000${NC}"
else
    echo -e "${RED}❌ Failed to start MinIO server${NC}"
    exit 1
fi

# Go back to main directory
cd /home/adebo/con

# Check and activate virtual environment
echo -e "${BLUE}🐍 Setting up Python environment...${NC}"
VENV_PATH=""

# Check for common virtual environment names
if [ -d "venv" ]; then
    VENV_PATH="venv"
elif [ -d "my_env" ]; then
    VENV_PATH="my_env"
elif [ -d ".venv" ]; then
    VENV_PATH=".venv"
fi

if [ -n "$VENV_PATH" ] && [ -f "$VENV_PATH/bin/activate" ]; then
    echo -e "${GREEN}✅ Found virtual environment: $VENV_PATH${NC}"
    source "$VENV_PATH/bin/activate"
    echo -e "${GREEN}✅ Virtual environment activated${NC}"
else
    echo -e "${YELLOW}⚠️  No virtual environment found. Creating one...${NC}"
    python3 -m venv venv
    source venv/bin/activate
    echo -e "${GREEN}✅ Created and activated new virtual environment${NC}"
    
    # Install requirements if available
    if [ -f "requirements.txt" ]; then
        echo -e "${BLUE}📦 Installing Python dependencies...${NC}"
        pip install -r requirements.txt
        echo -e "${GREEN}✅ Dependencies installed${NC}"
    fi
fi

# Start Flask application
echo -e "${BLUE}🌐 Starting Flask application...${NC}"
export FLASK_APP=app.py
export FLASK_ENV=development
export FLASK_DEBUG=1

# Start Flask in background with virtual environment activated
nohup python app.py > flask.log 2>&1 &
FLASK_PID=$!

# Wait for Flask to be ready
if wait_for_service "Flask" 5000; then
    echo -e "${GREEN}✅ Flask application started successfully${NC}"
    echo -e "${BLUE}   Web Interface: http://localhost:5000${NC}"
else
    echo -e "${RED}❌ Failed to start Flask application${NC}"
    # Kill MinIO if Flask fails
    kill $MINIO_PID 2>/dev/null || true
    exit 1
fi

# Save PIDs for later cleanup
echo $MINIO_PID > /tmp/minio.pid
echo $FLASK_PID > /tmp/flask.pid

echo -e "${GREEN}"
echo "🎉 All services started successfully!"
echo "=========================================="
echo -e "${BLUE}📊 Service Status:${NC}"
echo -e "${GREEN}   ✅ MinIO Server: http://localhost:9001 (console)${NC}"
echo -e "${GREEN}   ✅ MinIO API: http://localhost:9000${NC}"
echo -e "${GREEN}   ✅ Flask App: http://localhost:5000${NC}"
echo -e "${BLUE}"
echo "📝 Logs:"
echo "   MinIO: /home/adebo/con/minio_storage/logs/"
echo "   Flask: /home/adebo/con/flask.log"
echo ""
echo "🛑 To stop services: ./stop_all.sh"
echo -e "${NC}"

# Keep the script running so we can see the services
echo -e "${YELLOW}Press Ctrl+C to stop all services...${NC}"
trap 'echo -e "\n${BLUE}🛑 Stopping services...${NC}"; kill $MINIO_PID $FLASK_PID 2>/dev/null || true; rm -f /tmp/minio.pid /tmp/flask.pid; exit 0' INT

# Wait for user to stop
while true; do
    sleep 1
done
