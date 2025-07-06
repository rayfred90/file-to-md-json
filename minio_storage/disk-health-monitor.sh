#!/bin/bash

# MinIO Disk Health Monitor
# This script monitors disk health and performance for MinIO

MINIO_DATA_DIR="/home/adebo/con/minio_storage/data"
LOG_FILE="/home/adebo/con/minio_storage/logs/disk-health.log"
ALERT_THRESHOLD_IOWAIT=20  # Alert if I/O wait > 20%
ALERT_THRESHOLD_SPACE=90   # Alert if disk usage > 90%

# Create log directory if it doesn't exist
mkdir -p "$(dirname "$LOG_FILE")"

# Function to log with timestamp
log_message() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOG_FILE"
}

# Function to check disk space
check_disk_space() {
    local usage_percent=$(df "$MINIO_DATA_DIR" | awk 'NR==2 {print $5}' | sed 's/%//')
    if [ "$usage_percent" -gt "$ALERT_THRESHOLD_SPACE" ]; then
        log_message "⚠️  WARNING: Disk usage is ${usage_percent}% (threshold: ${ALERT_THRESHOLD_SPACE}%)"
        return 1
    else
        log_message "✅ Disk usage OK: ${usage_percent}%"
        return 0
    fi
}

# Function to check I/O wait
check_io_wait() {
    local iowait=$(iostat -c 1 2 2>/dev/null | tail -1 | awk '{print $4}' | cut -d'.' -f1 2>/dev/null || echo "0")
    # Handle case where iostat might not return numeric value
    if ! [[ "$iowait" =~ ^[0-9]+$ ]]; then
        iowait=0
    fi
    
    if [ "$iowait" -gt "$ALERT_THRESHOLD_IOWAIT" ]; then
        log_message "⚠️  WARNING: High I/O wait: ${iowait}% (threshold: ${ALERT_THRESHOLD_IOWAIT}%)"
        return 1
    else
        log_message "✅ I/O wait OK: ${iowait}%"
        return 0
    fi
}

# Function to check for MinIO process
check_minio_process() {
    if pgrep -f "minio server" > /dev/null; then
        log_message "✅ MinIO process is running"
        return 0
    else
        log_message "❌ MinIO process is not running"
        return 1
    fi
}

# Function to perform basic I/O test
test_io_performance() {
    local test_file="$MINIO_DATA_DIR/.health_check_$(date +%s)"
    local start_time=$(date +%s.%N)
    
    # Write test
    if echo "health_check_data" > "$test_file" 2>/dev/null; then
        # Read test
        if cat "$test_file" > /dev/null 2>&1; then
            # Delete test
            rm -f "$test_file" 2>/dev/null
            local end_time=$(date +%s.%N)
            local duration=$(echo "$end_time - $start_time" | bc -l 2>/dev/null || echo "0.1")
            # Format duration to 2 decimal places
            duration=$(printf "%.2f" "$duration" 2>/dev/null || echo "0.1")
            log_message "✅ I/O test passed (${duration}s)"
            return 0
        fi
    fi
    
    log_message "❌ I/O test failed"
    rm -f "$test_file" 2>/dev/null
    return 1
}

# Function to check for lock files
check_lock_files() {
    local lock_count=$(find "$MINIO_DATA_DIR" -name "*.lock" -type f | wc -l)
    if [ "$lock_count" -gt 0 ]; then
        log_message "⚠️  WARNING: Found $lock_count lock files"
        return 1
    else
        log_message "✅ No lock files found"
        return 0
    fi
}

# Main health check function
run_health_check() {
    log_message "🔍 Starting MinIO disk health check..."
    
    local issues=0
    
    check_disk_space || ((issues++))
    check_io_wait || ((issues++))
    check_minio_process || ((issues++))
    test_io_performance || ((issues++))
    check_lock_files || ((issues++))
    
    if [ "$issues" -eq 0 ]; then
        log_message "✅ All health checks passed"
    else
        log_message "⚠️  Health check completed with $issues issue(s)"
    fi
    
    log_message "📊 System stats:"
    log_message "   Disk usage: $(df -h "$MINIO_DATA_DIR" | awk 'NR==2 {print $5}')"
    log_message "   Available space: $(df -h "$MINIO_DATA_DIR" | awk 'NR==2 {print $4}')"
    log_message "   Load average: $(uptime | awk -F'load average:' '{print $2}')"
    log_message "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    
    return $issues
}

# Script execution
case "${1:-check}" in
    "check")
        run_health_check
        ;;
    "monitor")
        log_message "🚀 Starting continuous monitoring (interval: ${2:-300}s)..."
        while true; do
            run_health_check
            sleep "${2:-300}"  # Default 5 minutes
        done
        ;;
    "clean")
        log_message "🧹 Cleaning up temporary files..."
        find "$MINIO_DATA_DIR" -name "*.tmp" -type f -delete 2>/dev/null || true
        find "$MINIO_DATA_DIR" -name ".health_check_*" -type f -delete 2>/dev/null || true
        log_message "✅ Cleanup completed"
        ;;
    *)
        echo "Usage: $0 {check|monitor [interval]|clean}"
        echo "  check    - Run a single health check"
        echo "  monitor  - Run continuous monitoring (default 300s interval)"
        echo "  clean    - Clean up temporary files"
        exit 1
        ;;
esac
