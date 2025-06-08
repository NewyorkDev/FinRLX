#!/usr/bin/env bash
# System X Management Script (improved edition)
# ---------------------------------------------
# Cross‑platform launcher for the Autonomous Trading & Back‑testing stack.
# Focus: safety, portability, graceful lifecycle with PM2, overridable settings.

set -euo pipefail
trap 'echo -e "\033[0;31m[$(date +%F\ %T)] FATAL: command \`$BASH_COMMAND\` failed at line $LINENO with exit $?\033[0m"; exit 1' ERR

# ────── Configurable parameters (env‑override) ─────────────────────────────────
PY=${PYTHON_BIN:-python3.12}        # export PYTHON_BIN=python
PORT=${SYSTEMX_PORT:-8080}         # export SYSTEMX_PORT=9090
VENV_PATH=${SYSTEMX_VENV:-venv}    # export SYSTEMX_VENV=.venv to auto‑activate
REDIS_HOST=${REDIS_HOST:-localhost}
REDIS_PORT=${REDIS_PORT:-6379}
ENV_FILE=${ENV_FILE_PATH:-the_end/.env}  # Allow custom env file location
# ──────────────────────────────────────────────────────────────────────────────

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &>/dev/null && pwd )"
cd "$SCRIPT_DIR"

# Colour helpers
RED='\033[0;31m'; GREEN='\033[0;32m'; YELLOW='\033[1;33m'; BLUE='\033[0;34m'; NC='\033[0m'
p()     { printf '%b\n' "$*"; }
status(){ p "${GREEN}[$(date '+%F %T')] $*${NC}"; }
warn()  { p "${YELLOW}[$(date '+%F %T')] WARNING: $*${NC}"; }
err()   { p "${RED}[$(date '+%F %T')] ERROR: $*${NC}"; }
info()  { p "${BLUE}[$(date '+%F %T')] $*${NC}"; }

require_command() { command -v "$1" &>/dev/null || { err "$1 is required but not installed"; exit 1; }; }

# Optional virtual‑env activation ------------------------------------------------
activate_venv() {
  if [[ -d "$VENV_PATH" && -f "$VENV_PATH/bin/activate" ]]; then
     info "Activating virtual‑env \"$VENV_PATH\""
     # shellcheck source=/dev/null
     source "$VENV_PATH/bin/activate"
     PY=python   # use interpreter from venv
  fi
}

# Enhanced smoke‑test for critical Python deps with specific version checks -----
smoke_python() {
"$PY" - <<'PY'
import importlib, sys
missing=[]
version_issues=[]

# Required packages with minimum versions
required_packages = {
    "supabase": None,
    "alpaca_trade_api": None, 
    "redis": None,
    "tenacity": None,
    "pandas": "2.0.0",
    "numpy": "1.20.0",
    "requests": None,
    "pydantic": "2.0.0"
}

for pkg, min_version in required_packages.items():
    try:
        mod = importlib.import_module(pkg)
        if min_version and hasattr(mod, '__version__'):
            from packaging import version
            if version.parse(mod.__version__) < version.parse(min_version):
                version_issues.append(f"{pkg} {mod.__version__} < {min_version}")
    except ImportError:
        missing.append(pkg)
    except Exception:
        pass  # Version check failed, but package exists

if missing:
    print(f"Missing packages: {', '.join(missing)}")
    sys.exit(1)
if version_issues:
    print(f"Version issues: {'; '.join(version_issues)}")
    sys.exit(2)
print("All Python dependencies satisfied")
PY
}

# Backend reachability with timeout and retry ------------------------------------
check_backend() { 
    info "Checking Redis connectivity..."
    if command -v nc &>/dev/null; then
        if nc -z -w3 "$REDIS_HOST" "$REDIS_PORT" 2>/dev/null; then
            status "Redis reachable at $REDIS_HOST:$REDIS_PORT"
        else
            warn "Redis unreachable at $REDIS_HOST:$REDIS_PORT (system will attempt to continue)"
        fi
    else
        warn "netcat (nc) not available - skipping Redis connectivity check"
    fi
}

# PM2 helpers with enhanced error handling -----------------------------------
pm2_graceful_stop() {
  info "Gracefully stopping PM2 processes..."
  
  # Try graceful stop first
  pm2 stop system-x --timeout 15000 2>/dev/null || true
  pm2 stop system-x-monitor --timeout 10000 2>/dev/null || true
  
  # Wait for processes to stop
  sleep 3
  
  # Delete processes
  pm2 delete system-x 2>/dev/null || true
  pm2 delete system-x-monitor 2>/dev/null || true
  
  status "PM2 processes stopped"
}

free_port() {
  local pids
  pids=$(lsof -ti :"$PORT" 2>/dev/null || true)
  if [[ -n "$pids" ]]; then
    info "Freeing port $PORT (PIDs: $(echo $pids | tr '\n' ' '))"
    echo "$pids" | xargs kill -TERM 2>/dev/null || true
    sleep 2
    # Force kill if still running
    pids=$(lsof -ti :"$PORT" 2>/dev/null || true)
    [[ -n "$pids" ]] && echo "$pids" | xargs kill -9 2>/dev/null || true
  fi
}

# Enhanced dependency validation with fallbacks ------------------------------
check_dependencies() {
  info "Checking dependencies…"
  require_command pm2
  require_command lsof
  
  # Check for nc with fallback
  if ! command -v nc &>/dev/null; then
    warn "netcat (nc) not found - Redis connectivity checks will be skipped"
  fi

  activate_venv
  require_command "$PY"

  [[ -f "$ENV_FILE" ]] || { err "Environment file missing: $ENV_FILE"; exit 1; }
  
  # Enhanced Python dependency check
  if ! smoke_python; then
    err "Python dependency check failed - see output above"
    exit 1
  fi
  
  check_backend
  status "All dependencies satisfied"
}

# System health check --------------------------------------------------------
health_check() {
    info "Performing system health check..."
    
    # Check if System X is responsive
    if "$PY" system_x.py --test &>/dev/null; then
        status "System X health check passed"
        return 0
    else
        err "System X health check failed"
        return 1
    fi
}

# Workflow verbs with enhanced error handling --------------------------------
start_system() { 
    info "Starting System X…"
    mkdir -p logs
    
    # Pre-flight health check
    if ! health_check; then
        err "Pre-flight health check failed - aborting start"
        exit 1
    fi
    
    pm2 start ecosystem.config.js --env production
    
    # Verify startup
    sleep 5
    if pm2 list | grep -q "system-x.*online"; then
        status "System X started successfully ⇒ pm2 logs system-x"
        info "Monitor with: pm2 monit"
    else
        err "System X failed to start properly"
        pm2 logs system-x --lines 20 --nostream
        exit 1
    fi
}

stop_system() { 
    info "Stopping System X…"
    pm2_graceful_stop
    free_port
    
    # Clean up any remaining Python processes
    pkill -f "system_x.py" 2>/dev/null || true
    
    status "System X stopped"
}

restart_system() { 
    info "Restarting System X…"
    stop_system
    sleep 2
    start_system
}

test_system() { 
    info "Running comprehensive self‑test…"
    activate_venv
    "$PY" system_x.py --test
    status "Self‑test passed"
}

generate_report() { 
    info "Generating performance report…"
    activate_venv
    "$PY" system_x.py --report
}

upgrade_system() { 
    info "Upgrading System X…"
    
    # Backup current state
    backup_dir="backup_$(date +%Y%m%d_%H%M%S)"
    mkdir -p "$backup_dir"
    cp -r logs "$backup_dir/" 2>/dev/null || true
    
    # Stop system
    stop_system
    
    # Update code
    git fetch origin
    git pull origin main --quiet || git pull origin master --quiet
    
    # Update dependencies if requirements exist
    activate_venv
    [[ -f requirements.txt ]] && "$PY" -m pip install -q -r requirements.txt
    [[ -f pyproject.toml ]] && "$PY" -m pip install -q -e .
    
    # Test before restarting
    if health_check; then
        start_system
        status "Upgrade completed successfully"
    else
        err "Upgrade failed - system health check failed"
        exit 1
    fi
}

# Status and monitoring with enhanced details --------------------------------
show_status() {
    info "System X Status Overview"
    echo ""
    
    # PM2 status
    if pm2 list 2>/dev/null | grep -E "(system-x|Process)" | head -5; then
        echo ""
    else
        warn "System X processes not running"
    fi
    
    # Port status
    if lsof -ti :"$PORT" &>/dev/null; then
        info "Port $PORT is in use"
    else
        info "Port $PORT is free"
    fi
    
    # Recent logs with size check
    if [[ -f logs/system-x-out.log ]]; then
        local log_size=$(wc -l < logs/system-x-out.log)
        info "Recent activity (last 20 of $log_size lines):"
        tail -20 logs/system-x-out.log
    else
        warn "No logs found yet"
    fi
    
    # System metrics if available
    if command -v free &>/dev/null; then
        echo ""
        info "System resources:"
        free -h | head -2
    fi
}

show_logs() { 
    local follow_flag="${2:-}"
    if [[ "$follow_flag" == "--follow" || "$follow_flag" == "-f" ]]; then
        info "Following System X logs (Ctrl+C to stop)…"
        pm2 logs system-x --lines 50
    else
        info "Recent System X logs:"
        pm2 logs system-x --lines 100 --nostream
    fi
}

# Dry run mode for testing ---------------------------------------------------
dry_run() {
    info "Running System X in dry-run mode (no real trades)..."
    activate_venv
    "$PY" system_x.py --dry-run
}

help() {
  cat <<EOF
System X Management Script
==========================

Usage: $0 {start|stop|restart|status|logs|test|report|upgrade|dry-run|help}

Commands:
  start     Start System X autonomous operation
  stop      Stop System X gracefully  
  restart   Restart System X (stop + start)
  status    Show detailed system status
  logs      Show logs (--follow for live stream)
  test      Run comprehensive system tests
  report    Generate daily performance report
  upgrade   Update code and restart system
  dry-run   Run system in simulation mode
  help      Show this message

Environment overrides:
  PYTHON_BIN     Custom python interpreter (default: python3.12)
  SYSTEMX_PORT   Port to monitor/free on stop (default: 8080)  
  SYSTEMX_VENV   Path to venv for auto-activation (default: venv)
  REDIS_HOST     Redis server host (default: localhost)
  REDIS_PORT     Redis server port (default: 6379)
  ENV_FILE_PATH  Custom .env file location (default: the_end/.env)

Examples:
  $0 start                    # Start with defaults
  PYTHON_BIN=python3 $0 start # Use different Python
  $0 logs --follow            # Stream live logs
  $0 upgrade                  # Update and restart
EOF
}

# Entrypoint with command validation -----------------------------------------
cmd="${1:-help}"
case "$cmd" in
  start)   check_dependencies; start_system;;
  stop)    require_command pm2; stop_system;;
  restart) check_dependencies; restart_system;;
  status)  require_command pm2; show_status;;
  logs)    require_command pm2; show_logs "$@";;
  test)    check_dependencies; test_system;;
  report)  check_dependencies; generate_report;;
  upgrade) require_command git; require_command pm2; upgrade_system;;
  dry-run) check_dependencies; dry_run;;
  help|--help|-h) help;;
  *) err "Invalid command: $cmd"; echo ""; help; exit 1;;
esac