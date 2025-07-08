#!/bin/bash

# Document Converter - Service Startup Script
# This script starts MinIO and Flask services for the document converter application

echo "🚀 Starting Document Converter Services..."
echo "========================================"

# Set script directory as working directory
cd "$(dirname "$0")"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to check if a port is in use
check_port() {
    local port=$1
    if lsof -Pi :$port -sTCP:LISTEN -t >/dev/null 2>&1; then
        return 0  # Port is in use
    else
        return 1  # Port is free
    fi
}

# Function to kill process on port
kill_port() {
    local port=$1
    local service_name=$2
    
    if check_port $port; then
        echo -e "${YELLOW}⚠️  Port $port is already in use. Killing existing $service_name process...${NC}"
        lsof -ti:$port | xargs kill -9 2>/dev/null || true
        sleep 2
        
        if check_port $port; then
            echo -e "${RED}❌ Failed to free port $port${NC}"
            return 1
        else
            echo -e "${GREEN}✅ Port $port freed${NC}"
        fi
    fi
    return 0
}

# Step 1: Start MinIO Server
echo -e "${BLUE}📦 Starting MinIO Server...${NC}"

# Kill any existing MinIO process
kill_port 9000 "MinIO"
kill_port 9001 "MinIO Console"

# Start MinIO in background
cd minio_storage
if [ -f "start-minio.sh" ]; then
    chmod +x start-minio.sh
    ./start-minio.sh &
    MINIO_PID=$!
    echo -e "${GREEN}✅ MinIO started with PID: $MINIO_PID${NC}"
else
    echo -e "${YELLOW}⚠️  start-minio.sh not found, starting MinIO manually...${NC}"
    
    # Create data directory if it doesn't exist
    mkdir -p data
    
    # Start MinIO server
    MINIO_ROOT_USER=minioadmin MINIO_ROOT_PASSWORD=minioadmin \
    minio server data --address 0.0.0.0:9000 --console-address 0.0.0.0:9001 > logs/minio.log 2>&1 &
    MINIO_PID=$!
    echo -e "${GREEN}✅ MinIO started manually with PID: $MINIO_PID${NC}"
fi

# Return to main directory
cd ..

# Wait for MinIO to be ready
echo -e "${BLUE}⏳ Waiting for MinIO to be ready...${NC}"
for i in {1..30}; do
    if curl -s http://localhost:9000/minio/health/live >/dev/null 2>&1; then
        echo -e "${GREEN}✅ MinIO is ready!${NC}"
        break
    fi
    if [ $i -eq 30 ]; then
        echo -e "${RED}❌ MinIO failed to start within 30 seconds${NC}"
        exit 1
    fi
    sleep 1
done

# Step 2: Setup MinIO buckets (if needed)
echo -e "${BLUE}🪣 Setting up MinIO buckets...${NC}"
if [ -f "minio_storage/setup-buckets.sh" ]; then
    cd minio_storage
    chmod +x setup-buckets.sh
    ./setup-buckets.sh
    cd ..
else
    echo -e "${YELLOW}⚠️  setup-buckets.sh not found, buckets will be created automatically${NC}"
fi

# Step 3: Start Flask Application
echo -e "${BLUE}🌶️  Starting Flask Application...${NC}"

# Kill any existing Flask process
kill_port 5000 "Flask"

# Activate virtual environment if it exists
if [ -d "venv" ]; then
    echo -e "${BLUE}🐍 Activating virtual environment...${NC}"
    source venv/bin/activate
elif [ -d ".venv" ]; then
    echo -e "${BLUE}🐍 Activating virtual environment...${NC}"
    source .venv/bin/activate
fi

# Install requirements if needed
if [ -f "requirements.txt" ]; then
    echo -e "${BLUE}📦 Checking Python dependencies...${NC}"
    pip install -q -r requirements.txt
fi

# Set environment variables
export FLASK_APP=app.py
export FLASK_ENV=development
export FLASK_DEBUG=1

# Start Flask application
echo -e "${BLUE}🚀 Launching Flask application...${NC}"
python app.py &
FLASK_PID=$!

# Wait for Flask to be ready
echo -e "${BLUE}⏳ Waiting for Flask to be ready...${NC}"
for i in {1..15}; do
    if curl -s http://localhost:5000 >/dev/null 2>&1; then
        echo -e "${GREEN}✅ Flask is ready!${NC}"
        break
    fi
    if [ $i -eq 15 ]; then
        echo -e "${RED}❌ Flask failed to start within 15 seconds${NC}"
        echo -e "${YELLOW}💡 Check app.log for errors${NC}"
        exit 1
    fi
    sleep 1
done

# Success message
echo ""
echo -e "${GREEN}🎉 All services started successfully!${NC}"
echo "========================================"
echo -e "${BLUE}📊 Service URLs:${NC}"
echo -e "   📱 Web Application:    http://localhost:5000"
echo -e "   🗄️  MinIO Console:      http://localhost:9001"
echo -e "   🔧 MinIO API:          http://localhost:9000"
echo ""
echo -e "${BLUE}🔑 MinIO Credentials:${NC}"
echo -e "   Username: minioadmin"
echo -e "   Password: minioadmin"
echo ""
echo -e "${BLUE}💻 Process IDs:${NC}"
echo -e "   MinIO PID:  $MINIO_PID"
echo -e "   Flask PID:  $FLASK_PID"
echo ""
echo -e "${YELLOW}💡 To stop services, run: ./stop_services.sh${NC}"
echo -e "${YELLOW}💡 Or manually kill processes: kill $MINIO_PID $FLASK_PID${NC}"
echo ""
echo -e "${GREEN}✨ Ready to convert documents! ✨${NC}"

# Save PIDs for later cleanup
echo "$MINIO_PID" > .minio_pid
echo "$FLASK_PID" > .flask_pid
