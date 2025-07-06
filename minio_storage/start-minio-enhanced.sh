#!/bin/bash

# MinIO Server Start Script with Enhanced Error Handling
# This script starts MinIO with better I/O monitoring and recovery

MINIO_DIR="/home/adebo/con/minio_storage"
DATA_DIR="$MINIO_DIR/data"
CONFIG_FILE="$MINIO_DIR/config/minio.env"
LOG_FILE="$MINIO_DIR/logs/minio.log"
HEALTH_MONITOR="$MINIO_DIR/disk-health-monitor.sh"
PID_FILE="$MINIO_DIR/logs/minio.pid"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${2:-$GREEN}$1${NC}"
}

# Function to check if MinIO is already running
check_running() {
    if [ -f "$PID_FILE" ]; then
        local pid=$(cat "$PID_FILE")
        if kill -0 "$pid" 2>/dev/null; then
            return 0  # Running
        else
            rm -f "$PID_FILE"
        fi
    fi
    return 1  # Not running
}

# Function to stop MinIO if running
stop_minio() {
    if check_running; then
        local pid=$(cat "$PID_FILE")
        print_status "🛑 Stopping existing MinIO server (PID: $pid)..." "$YELLOW"
        kill "$pid" 2>/dev/null
        
        # Wait for graceful shutdown
        local count=0
        while kill -0 "$pid" 2>/dev/null && [ $count -lt 10 ]; do
            sleep 1
            ((count++))
        done
        
        # Force kill if needed
        if kill -0 "$pid" 2>/dev/null; then
            kill -9 "$pid" 2>/dev/null
        fi
        
        rm -f "$PID_FILE"
        print_status "✅ MinIO server stopped"
    fi
}

# Function to cleanup old resources
cleanup_resources() {
    print_status "🧹 Cleaning up resources..." "$BLUE"
    
    # Clean up old lock files
    find "$DATA_DIR" -name "*.lock" -type f -delete 2>/dev/null || true
    
    # Clean up temporary files
    find "$DATA_DIR" -name "*.tmp" -type f -delete 2>/dev/null || true
    
    # Clean up old log files (keep last 5)
    if [ -f "$LOG_FILE" ]; then
        cp "$LOG_FILE" "$LOG_FILE.$(date +%Y%m%d_%H%M%S)"
        find "$(dirname "$LOG_FILE")" -name "minio.log.*" -type f | sort | head -n -5 | xargs rm -f 2>/dev/null || true
        > "$LOG_FILE"  # Clear current log
    fi
    
    print_status "✅ Cleanup completed"
}

# Function to check system resources
check_system_resources() {
    print_status "📊 Checking system resources..." "$BLUE"
    
    # Check disk space
    local available_space=$(df "$DATA_DIR" | awk 'NR==2 {print $4}')
    local space_gb=$((available_space / 1024 / 1024))
    
    if [ "$space_gb" -lt 1 ]; then
        print_status "⚠️  WARNING: Low disk space: ${space_gb}GB available" "$YELLOW"
    else
        print_status "✅ Disk space OK: ${space_gb}GB available"
    fi
    
    # Check memory
    local available_memory=$(free -m | awk 'NR==2{print $7}')
    if [ "$available_memory" -lt 512 ]; then
        print_status "⚠️  WARNING: Low available memory: ${available_memory}MB" "$YELLOW"
    else
        print_status "✅ Memory OK: ${available_memory}MB available"
    fi
    
    # Check load average
    local load=$(uptime | awk -F'load average:' '{print $2}' | awk '{print $1}' | cut -d',' -f1)
    local load_int=$(echo "$load" | cut -d'.' -f1)
    if [ "$load_int" -gt 4 ]; then
        print_status "⚠️  WARNING: High system load: $load" "$YELLOW"
    else
        print_status "✅ System load OK: $load"
    fi
}

# Function to run pre-start health check
pre_start_health_check() {
    if [ -x "$HEALTH_MONITOR" ]; then
        print_status "🔍 Running pre-start health check..." "$BLUE"
        if "$HEALTH_MONITOR" check; then
            print_status "✅ Health check passed"
        else
            print_status "⚠️  Health check found issues, but continuing..." "$YELLOW"
        fi
    fi
}

# Function to start MinIO with monitoring
start_minio() {
    print_status "🚀 Starting MinIO Server..." "$GREEN"
    print_status "📁 Data Directory: $DATA_DIR"
    print_status "⚙️  Configuration: $CONFIG_FILE"
    print_status "📝 Log File: $LOG_FILE"
    print_status "🌐 Console URL: http://localhost:9001"
    print_status "🔗 API URL: http://localhost:9000"
    echo ""
    
    # Source configuration
    if [ -f "$CONFIG_FILE" ]; then
        source "$CONFIG_FILE"
        print_status "✅ Configuration loaded from $CONFIG_FILE"
    else
        print_status "⚠️  Configuration file not found, using defaults" "$YELLOW"
        export MINIO_ROOT_USER=minioadmin
        export MINIO_ROOT_PASSWORD=minioadmin
    fi
    
    # Create necessary directories
    mkdir -p "$DATA_DIR"
    mkdir -p "$(dirname "$LOG_FILE")"
    mkdir -p "$(dirname "$PID_FILE")"
    
    # Set proper permissions
    chmod 755 "$DATA_DIR"
    
    # Performance optimization: Set I/O scheduler if possible
    if [ -w /sys/block/sda/queue/scheduler ]; then
        echo deadline | sudo tee /sys/block/sda/queue/scheduler > /dev/null 2>&1 || true
        print_status "✅ I/O scheduler optimized"
    fi
    
    # Start MinIO server in background with monitoring
    print_status "🎯 Starting MinIO server process..." "$BLUE"
    
    # Use nohup and nice to improve stability
    nohup nice -n 10 minio server "$DATA_DIR" \
        --console-address ":9001" \
        --quiet \
        > "$LOG_FILE" 2>&1 &
    
    local minio_pid=$!
    echo "$minio_pid" > "$PID_FILE"
    
    # Wait a moment and check if it started successfully
    sleep 3
    if kill -0 "$minio_pid" 2>/dev/null; then
        print_status "✅ MinIO server started successfully (PID: $minio_pid)" "$GREEN"
        print_status "📊 Monitor logs with: tail -f $LOG_FILE"
        print_status "🔍 Run health check with: $HEALTH_MONITOR check"
        
        # Start background health monitoring if requested
        if [[ "${1:-}" == "--monitor" ]]; then
            print_status "🔄 Starting background health monitoring..." "$BLUE"
            nohup "$HEALTH_MONITOR" monitor 300 > "$MINIO_DIR/logs/health-monitor.log" 2>&1 &
            print_status "✅ Health monitoring started"
        fi
        
    else
        print_status "❌ Failed to start MinIO server" "$RED"
        rm -f "$PID_FILE"
        return 1
    fi
}

# Function to show status
show_status() {
    if check_running; then
        local pid=$(cat "$PID_FILE")
        print_status "✅ MinIO server is running (PID: $pid)" "$GREEN"
        
        # Show recent log entries
        if [ -f "$LOG_FILE" ]; then
            echo ""
            print_status "📝 Recent log entries:" "$BLUE"
            tail -5 "$LOG_FILE"
        fi
    else
        print_status "❌ MinIO server is not running" "$RED"
    fi
}

# Main script logic
case "${1:-start}" in
    "start")
        if check_running; then
            print_status "⚠️  MinIO is already running" "$YELLOW"
            show_status
        else
            check_system_resources
            cleanup_resources
            pre_start_health_check
            start_minio "${2:-}"
        fi
        ;;
    "stop")
        stop_minio
        ;;
    "restart")
        stop_minio
        sleep 2
        check_system_resources
        cleanup_resources
        pre_start_health_check
        start_minio "${2:-}"
        ;;
    "status")
        show_status
        ;;
    "health")
        if [ -x "$HEALTH_MONITOR" ]; then
            "$HEALTH_MONITOR" check
        else
            print_status "❌ Health monitor script not found" "$RED"
        fi
        ;;
    "logs")
        if [ -f "$LOG_FILE" ]; then
            tail -f "$LOG_FILE"
        else
            print_status "❌ Log file not found: $LOG_FILE" "$RED"
        fi
        ;;
    *)
        echo "Usage: $0 {start [--monitor]|stop|restart [--monitor]|status|health|logs}"
        echo ""
        echo "Commands:"
        echo "  start [--monitor]  - Start MinIO server (optionally with health monitoring)"
        echo "  stop               - Stop MinIO server"
        echo "  restart [--monitor]- Restart MinIO server (optionally with health monitoring)"
        echo "  status             - Show MinIO server status"
        echo "  health             - Run health check"
        echo "  logs               - Follow MinIO logs"
        echo ""
        echo "Examples:"
        echo "  $0 start --monitor   # Start with health monitoring"
        echo "  $0 restart           # Restart server"
        echo "  $0 health            # Check system health"
        exit 1
        ;;
esac
