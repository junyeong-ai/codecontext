#!/usr/bin/env bash

# ChromaDB Management CLI
# Comprehensive tool for managing ChromaDB server and data
# Best practices: error handling, signal handling, PID locking, exponential backoff

# Strict error handling
set -euo pipefail
IFS=$'\n\t'

# Configuration
CHROMA_HOST="${CHROMA_HOST:-localhost}"
CHROMA_PORT="${CHROMA_PORT:-8000}"
CHROMA_DATA_DIR="${CHROMA_DATA_DIR:-./chroma}"
CHROMA_LOG_DIR="${CHROMA_LOG_DIR:-./logs}"

# Runtime directory for PID files (project-specific)
CHROMA_RUNTIME_DIR="${CHROMA_RUNTIME_DIR:-${HOME}/.local/run/codecontext}"
mkdir -p "$CHROMA_RUNTIME_DIR" 2>/dev/null || CHROMA_RUNTIME_DIR="/tmp/codecontext"
mkdir -p "$CHROMA_RUNTIME_DIR"

CHROMA_PID_FILE="$CHROMA_RUNTIME_DIR/chroma-${CHROMA_PORT}.pid"
CHROMA_LOCK_FILE="$CHROMA_RUNTIME_DIR/chroma-${CHROMA_PORT}.lock"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Cleanup flag
CLEANUP_DONE=false

# Helper functions
log_info() {
    local timestamp
    timestamp=$(date '+%Y-%m-%d %H:%M:%S')
    echo -e "${BLUE}[INFO]${NC} [$timestamp] $*" >&2
}

log_success() {
    local timestamp
    timestamp=$(date '+%Y-%m-%d %H:%M:%S')
    echo -e "${GREEN}[SUCCESS]${NC} [$timestamp] $*" >&2
}

log_warn() {
    local timestamp
    timestamp=$(date '+%Y-%m-%d %H:%M:%S')
    echo -e "${YELLOW}[WARN]${NC} [$timestamp] $*" >&2
}

log_error() {
    local timestamp
    timestamp=$(date '+%Y-%m-%d %H:%M:%S')
    echo -e "${RED}[ERROR]${NC} [$timestamp] $*" >&2
}

# Cleanup function for signal handlers
cleanup() {
    if [ "$CLEANUP_DONE" = true ]; then
        return 0
    fi
    CLEANUP_DONE=true

    log_warn "Received termination signal, cleaning up..."

    # Release lock if we have it
    release_lock

    exit 0
}

# Acquire lock (portable atomic mkdir-based lock)
acquire_lock() {
    local lock_dir="$CHROMA_LOCK_FILE"
    local max_attempts=5
    local attempt=0

    while [ $attempt -lt $max_attempts ]; do
        if mkdir "$lock_dir" 2>/dev/null; then
            # Lock acquired, store PID for verification
            echo $$ > "$lock_dir/owner"
            return 0
        fi

        # Check if lock is stale
        if [ -f "$lock_dir/owner" ]; then
            local lock_pid
            lock_pid=$(cat "$lock_dir/owner" 2>/dev/null || echo "")
            if [ -n "$lock_pid" ] && ! kill -0 "$lock_pid" 2>/dev/null; then
                log_warn "Removing stale lock (PID $lock_pid not running)"
                rm -rf "$lock_dir"
                continue
            fi
        fi

        ((attempt++))
        if [ $attempt -lt $max_attempts ]; then
            sleep 1
        fi
    done

    return 1
}

# Release lock
release_lock() {
    local lock_dir="$CHROMA_LOCK_FILE"
    if [ -d "$lock_dir" ]; then
        # Verify we own the lock
        if [ -f "$lock_dir/owner" ]; then
            local lock_pid
            lock_pid=$(cat "$lock_dir/owner" 2>/dev/null || echo "")
            if [ "$lock_pid" = "$$" ]; then
                rm -rf "$lock_dir"
            fi
        fi
    fi
}

# Set up signal handlers
trap cleanup SIGTERM SIGINT SIGHUP

# Detect ChromaDB command
get_chroma_cmd() {
    # Try uv run first (preferred for project venv)
    if [ -f "pyproject.toml" ] && command -v uv &> /dev/null; then
        echo "uv run chroma"
    # Try .venv/bin/chroma
    elif [ -x ".venv/bin/chroma" ]; then
        echo ".venv/bin/chroma"
    # Fall back to system chroma
    elif command -v chroma &> /dev/null; then
        echo "chroma"
    else
        echo ""
    fi
}

# Check if ChromaDB is installed
check_chroma_installed() {
    local chroma_cmd
    chroma_cmd=$(get_chroma_cmd)
    if [ -z "$chroma_cmd" ]; then
        log_error "ChromaDB is not installed. Install with: uv sync"
        exit 1
    fi
}

# Validate and clean stale PID file
validate_pid_file() {
    if [ ! -f "$CHROMA_PID_FILE" ]; then
        return 1
    fi

    local pid
    pid=$(cat "$CHROMA_PID_FILE" 2>/dev/null || echo "")

    if [ -z "$pid" ]; then
        rm -f "$CHROMA_PID_FILE"
        return 1
    fi

    # Check if process exists
    if ! kill -0 "$pid" 2>/dev/null; then
        log_warn "Removing stale PID file (process $pid not found)"
        rm -f "$CHROMA_PID_FILE"
        return 1
    fi

    # Verify it's actually a chroma process
    local process_name
    process_name=$(ps -p "$pid" -o comm= 2>/dev/null || echo "")

    if ! echo "$process_name" | grep -q "chroma\|python\|uv"; then
        log_warn "Removing stale PID file (process $pid is '$process_name', not chroma)"
        rm -f "$CHROMA_PID_FILE"
        return 1
    fi

    return 0
}

# Get ChromaDB process ID
get_chroma_pid() {
    if validate_pid_file; then
        cat "$CHROMA_PID_FILE"
    else
        pgrep -f "chroma run.*--port $CHROMA_PORT" | head -1 || true
    fi
}

# Check if ChromaDB is running
is_chroma_running() {
    local pid
    pid=$(get_chroma_pid)
    if [ -n "$pid" ] && ps -p "$pid" > /dev/null 2>&1; then
        return 0
    fi
    return 1
}

# Validate directory permissions
validate_permissions() {
    # Check log directory
    if [ ! -d "$CHROMA_LOG_DIR" ]; then
        mkdir -p "$CHROMA_LOG_DIR" || {
            log_error "Cannot create log directory: $CHROMA_LOG_DIR"
            exit 1
        }
    fi

    if [ ! -w "$CHROMA_LOG_DIR" ]; then
        log_error "No write permission to log directory: $CHROMA_LOG_DIR"
        exit 1
    fi

    # Check data directory if it exists
    if [ -d "$CHROMA_DATA_DIR" ] && [ ! -w "$CHROMA_DATA_DIR" ]; then
        log_error "No write permission to data directory: $CHROMA_DATA_DIR"
        exit 1
    fi
}

# Start ChromaDB server with atomic lock protection
start_chroma() {
    log_info "Starting ChromaDB server..."

    # Validate permissions first
    validate_permissions

    # Acquire lock to prevent multiple start attempts
    if ! acquire_lock; then
        log_error "Another instance is already managing ChromaDB on port $CHROMA_PORT"
        exit 1
    fi

    if is_chroma_running; then
        local pid
        pid=$(get_chroma_pid)
        log_warn "ChromaDB is already running (PID: $pid)"
        release_lock
        return 0
    fi

    # Get chroma command
    local chroma_cmd
    chroma_cmd=$(get_chroma_cmd)

    # Start ChromaDB in background
    local log_file
    log_file="$CHROMA_LOG_DIR/chroma-$(date +%Y%m%d-%H%M%S).log"

    # Use eval to properly handle multi-word commands like "uv run chroma"
    eval "nohup $chroma_cmd run --host \"$CHROMA_HOST\" --port \"$CHROMA_PORT\" > \"$log_file\" 2>&1 &"

    local shell_pid=$!

    # Wait a moment for the actual process to spawn
    sleep 2

    # Find the actual chroma process (not the shell wrapper)
    local actual_pid
    actual_pid=$(pgrep -f "chroma run.*--port $CHROMA_PORT" | head -1 || echo "")

    local pid
    if [ -n "$actual_pid" ]; then
        echo "$actual_pid" > "$CHROMA_PID_FILE"
        pid=$actual_pid
    else
        # Fallback to shell PID if we can't find the process
        echo "$shell_pid" > "$CHROMA_PID_FILE"
        pid=$shell_pid
    fi

    # Wait for server to start with exponential backoff
    log_info "Waiting for ChromaDB to start..."
    local max_attempts=15
    local attempt=0
    local delay=1
    local max_delay=8

    while [ $attempt -lt $max_attempts ]; do
        if curl -s --connect-timeout 2 --max-time 5 \
            "http://${CHROMA_HOST}:${CHROMA_PORT}/api/v1/heartbeat" > /dev/null 2>&1; then
            log_success "ChromaDB started successfully (PID: $pid)"
            log_info "Server: http://${CHROMA_HOST}:${CHROMA_PORT}"
            log_info "Log file: $log_file"
            release_lock
            return 0
        fi

        sleep "$delay"
        ((attempt++))

        # Exponential backoff with max delay cap
        if [ $delay -lt $max_delay ]; then
            delay=$((delay * 2))
        fi
    done

    log_error "ChromaDB failed to start within timeout"
    log_info "Check log file: $log_file"

    # Clean up failed start
    if [ -n "$pid" ] && ps -p "$pid" > /dev/null 2>&1; then
        kill "$pid" 2>/dev/null || true
    fi
    rm -f "$CHROMA_PID_FILE"

    release_lock
    return 1
}

# Stop ChromaDB server
stop_chroma() {
    log_info "Stopping ChromaDB server..."

    local pid
    pid=$(get_chroma_pid)

    if [ -z "$pid" ]; then
        log_warn "ChromaDB is not running"
        return 0
    fi

    if ps -p "$pid" > /dev/null 2>&1; then
        # Try graceful shutdown first (SIGTERM)
        kill -TERM "$pid" 2>/dev/null || true

        # Wait for process to stop with exponential backoff
        local max_attempts=10
        local attempt=0
        local delay=1

        while [ $attempt -lt $max_attempts ]; do
            if ! ps -p "$pid" > /dev/null 2>&1; then
                break
            fi
            sleep "$delay"
            ((attempt++))

            # Increase delay (1, 2, 3, ...)
            delay=$((delay + 1))
        done

        # Force kill if still running (SIGKILL)
        if ps -p "$pid" > /dev/null 2>&1; then
            log_warn "Force killing ChromaDB process..."
            kill -9 "$pid" 2>/dev/null || true
            sleep 1
        fi
    fi

    rm -f "$CHROMA_PID_FILE"
    log_success "ChromaDB stopped successfully"
}

# Restart ChromaDB server
restart_chroma() {
    log_info "Restarting ChromaDB server..."
    stop_chroma
    sleep 2
    start_chroma
}

# Check ChromaDB status
status_chroma() {
    if is_chroma_running; then
        local pid
        pid=$(get_chroma_pid)
        log_success "ChromaDB is running (PID: $pid)"
        log_info "Server: http://${CHROMA_HOST}:${CHROMA_PORT}"

        # Check if server is responsive
        if curl -s --connect-timeout 2 --max-time 5 \
            "http://${CHROMA_HOST}:${CHROMA_PORT}/api/v1/heartbeat" > /dev/null 2>&1; then
            log_success "Server is responsive"
        else
            log_warn "Server process exists but not responding"
        fi

        # Show data directory info
        if [ -d "$CHROMA_DATA_DIR" ]; then
            local size
            size=$(du -sh "$CHROMA_DATA_DIR" 2>/dev/null | cut -f1)
            log_info "Data directory: $CHROMA_DATA_DIR ($size)"
        fi
    else
        log_warn "ChromaDB is not running"
        return 1
    fi
}

# Initialize/reset ChromaDB database
init_db() {
    local force=false

    if [ "${1:-}" = "--force" ] || [ "${1:-}" = "-f" ]; then
        force=true
    fi

    if [ -d "$CHROMA_DATA_DIR" ] && [ "$force" = false ]; then
        log_error "ChromaDB data directory already exists: $CHROMA_DATA_DIR"
        log_info "Use 'chroma-cli.sh init --force' to reset the database"
        return 1
    fi

    if is_chroma_running; then
        log_info "Stopping ChromaDB before initialization..."
        stop_chroma
    fi

    if [ -d "$CHROMA_DATA_DIR" ]; then
        log_warn "Removing existing ChromaDB data..."
        rm -rf "$CHROMA_DATA_DIR"
    fi

    log_success "ChromaDB data directory cleared"
    log_info "Start ChromaDB with: $0 start"
}

# Remove ChromaDB data
clean_data() {
    if is_chroma_running; then
        log_error "ChromaDB is running. Stop it first with: $0 stop"
        return 1
    fi

    if [ ! -d "$CHROMA_DATA_DIR" ]; then
        log_warn "ChromaDB data directory does not exist"
        return 0
    fi

    log_warn "This will permanently delete all ChromaDB data!"
    read -r -p "Are you sure? (yes/no): " confirm

    if [ "$confirm" = "yes" ]; then
        rm -rf "$CHROMA_DATA_DIR"
        log_success "ChromaDB data removed successfully"
    else
        log_info "Operation cancelled"
    fi
}

# Show ChromaDB logs
logs_chroma() {
    local follow=false
    local lines=50

    while [ $# -gt 0 ]; do
        case "$1" in
            -f|--follow)
                follow=true
                shift
                ;;
            -n|--lines)
                lines="${2:-50}"
                shift 2
                ;;
            *)
                shift
                ;;
        esac
    done

    if [ ! -d "$CHROMA_LOG_DIR" ]; then
        log_error "Log directory does not exist: $CHROMA_LOG_DIR"
        return 1
    fi

    local latest_log
    latest_log=$(ls -t "$CHROMA_LOG_DIR"/chroma-*.log 2>/dev/null | head -1 || echo "")

    if [ -z "$latest_log" ]; then
        log_error "No log files found in: $CHROMA_LOG_DIR"
        return 1
    fi

    log_info "Showing logs from: $latest_log"
    echo ""

    if [ "$follow" = true ]; then
        tail -f -n "$lines" "$latest_log"
    else
        tail -n "$lines" "$latest_log"
    fi
}

# Show database info
info_chroma() {
    log_info "ChromaDB Configuration:"
    echo "  Host: $CHROMA_HOST"
    echo "  Port: $CHROMA_PORT"
    echo "  Data Directory: $CHROMA_DATA_DIR"
    echo "  Log Directory: $CHROMA_LOG_DIR"
    echo "  Runtime Directory: $CHROMA_RUNTIME_DIR"
    echo "  PID File: $CHROMA_PID_FILE"
    echo ""

    if [ -d "$CHROMA_DATA_DIR" ]; then
        local size files
        size=$(du -sh "$CHROMA_DATA_DIR" 2>/dev/null | cut -f1)
        files=$(find "$CHROMA_DATA_DIR" -type f 2>/dev/null | wc -l | tr -d ' ')
        log_info "Database Statistics:"
        echo "  Size: $size"
        echo "  Files: $files"
    else
        log_warn "Data directory does not exist"
    fi

    echo ""
    status_chroma || true
}

# Show usage
usage() {
    cat << EOF
ChromaDB Management CLI

Usage: $0 <command> [options]

Commands:
  start           Start ChromaDB server
  stop            Stop ChromaDB server
  restart         Restart ChromaDB server
  status          Check ChromaDB status
  init [--force]  Initialize/reset database (use --force to overwrite)
  clean           Remove all ChromaDB data (interactive)
  logs [-f] [-n N] Show ChromaDB logs (-f: follow, -n: number of lines)
  info            Show ChromaDB configuration and statistics
  help            Show this help message

Environment Variables:
  CHROMA_HOST        ChromaDB host (default: localhost)
  CHROMA_PORT        ChromaDB port (default: 8000)
  CHROMA_DATA_DIR    ChromaDB data directory (default: ./chroma)
  CHROMA_LOG_DIR     ChromaDB log directory (default: ./logs)
  CHROMA_RUNTIME_DIR Runtime directory for PID files (default: ~/.local/run/codecontext)

Examples:
  $0 start                    # Start ChromaDB
  $0 stop                     # Stop ChromaDB
  $0 status                   # Check status
  $0 init --force             # Reset database
  $0 logs -f                  # Follow logs in real-time
  $0 logs -n 100              # Show last 100 lines

  # Use custom port
  CHROMA_PORT=8001 $0 start

Features:
  - Automatic stale PID detection and cleanup
  - Atomic process locking via mkdir (portable, no flock dependency)
  - Graceful shutdown with SIGTERM, force kill with SIGKILL
  - Exponential backoff for health checks
  - Signal handling (SIGTERM, SIGINT, SIGHUP)
  - Comprehensive permission validation
  - Cross-platform compatible (Linux, macOS, BSD)
EOF
}

# Main
main() {
    if [ $# -eq 0 ]; then
        usage
        exit 0
    fi

    check_chroma_installed

    case "$1" in
        start)
            start_chroma
            ;;
        stop)
            stop_chroma
            ;;
        restart)
            restart_chroma
            ;;
        status)
            status_chroma
            ;;
        init)
            shift
            init_db "$@"
            ;;
        clean)
            clean_data
            ;;
        logs)
            shift
            logs_chroma "$@"
            ;;
        info)
            info_chroma
            ;;
        help|--help|-h)
            usage
            ;;
        *)
            log_error "Unknown command: $1"
            echo ""
            usage
            exit 1
            ;;
    esac
}

main "$@"
