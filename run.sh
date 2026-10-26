#!/usr/bin/env bash
#
# Unified Runner for Fusion ERP System
# Runs:
#   1. Fusion System Administrator (IAM Backend) on port 8001
#   2. Fusion Integrated Backend on port 8002
#   3. Fusion Integrated Frontend Client on port 5173
#

set -m # Enable job control so background processes get their own process group

# Ensure unbuffered output for Python so piped logs appear in real time
export PYTHONUNBUFFERED=1

# Default service token if not already set in environment
export TOKEN="${TOKEN:-fsvc_IokeDbMHN--rewd_g7gZPkLpD3MiwIZrPJsRKLR6jdY}"

# Colors
CYAN='\033[0;36m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
RED='\033[0;31m'
BOLD='\033[1m'
NC='\033[0m' # No Color

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ADMIN_DIR="/home/mohitj/Desktop/Software Engineering/Fusion_System_Administrator/Backend/backend"
ADMIN_PY="/home/mohitj/Desktop/Software Engineering/Fusion_System_Administrator/Backend/venv/bin/python"
INTEGRATED_DIR="$ROOT_DIR"
INTEGRATED_PY="$ROOT_DIR/.venv/bin/python"
CLIENT_DIR="$ROOT_DIR/client"

echo -e "${BOLD}======================================================${NC}"
echo -e "${BOLD}       Starting Fusion ERP Unified Environment        ${NC}"
echo -e "${BOLD}======================================================${NC}"
echo -e "Token:              ${GREEN}${TOKEN:0:15}...${NC}"
echo -e "IAM Backend:        ${CYAN}http://127.0.0.1:8001${NC}"
echo -e "Integrated Backend: ${GREEN}http://127.0.0.1:8002${NC}"
echo -e "Frontend Client:    ${YELLOW}http://127.0.0.1:5173${NC}"
echo -e "Press ${BOLD}Ctrl+C${NC} to stop all services simultaneously."
echo -e "${BOLD}======================================================${NC}\n"

# Verify required directories and binaries exist
if [ ! -d "$ADMIN_DIR" ]; then
    echo -e "${RED}Error: Admin directory not found at $ADMIN_DIR${NC}"
    exit 1
fi

if [ ! -f "$ADMIN_PY" ]; then
    echo -e "${RED}Error: Admin Python virtualenv not found at $ADMIN_PY${NC}"
    exit 1
fi

if [ ! -f "$INTEGRATED_PY" ]; then
    echo -e "${RED}Error: Integrated Python virtualenv not found at $INTEGRATED_PY${NC}"
    exit 1
fi

# Clean up any leftover processes on the required ports
for port in 8001 8002 5173; do
    if lsof -Pi :"$port" -sTCP:LISTEN -t >/dev/null 2>&1; then
        echo -e "${YELLOW}Port $port is currently in use. Clearing lingering process...${NC}"
        fuser -k "$port"/tcp 2>/dev/null || true
        sleep 0.5
    fi
done

# Cleanup handler on exit or Ctrl+C
cleanup() {
    trap - SIGINT SIGTERM EXIT
    echo -e "\n${BOLD}${RED}Received interrupt. Shutting down all services...${NC}"
    
    if [ -n "$PID_IAM" ] && kill -0 "$PID_IAM" 2>/dev/null; then
        pkill -P "$PID_IAM" 2>/dev/null || true
        kill "$PID_IAM" 2>/dev/null || true
    fi

    if [ -n "$PID_BACKEND" ] && kill -0 "$PID_BACKEND" 2>/dev/null; then
        pkill -P "$PID_BACKEND" 2>/dev/null || true
        kill "$PID_BACKEND" 2>/dev/null || true
    fi

    if [ -n "$PID_CLIENT" ] && kill -0 "$PID_CLIENT" 2>/dev/null; then
        pkill -P "$PID_CLIENT" 2>/dev/null || true
        kill "$PID_CLIENT" 2>/dev/null || true
    fi

    fuser -k 8001/tcp 2>/dev/null || true
    fuser -k 8002/tcp 2>/dev/null || true
    fuser -k 5173/tcp 2>/dev/null || true

    echo -e "${GREEN}All services successfully terminated.${NC}"
    exit 0
}

trap cleanup SIGINT SIGTERM EXIT

# Sync IAM permissions from Fusion-Integrated manifest before starting
echo -e "${CYAN}Syncing IAM permissions from permissions manifest...${NC}"
(
    cd "$ADMIN_DIR"
    export DJANGO_SETTINGS_MODULE="backend.settings"
    export DEBUG="True"
    export SECURE_SSL_REDIRECT="False"
    "$ADMIN_PY" manage.py seed_iam_permissions --manifest "$ROOT_DIR/registry/permissions.json" >/dev/null 2>&1 || true
)

# 1. Start IAM Backend (explicitly with backend.settings, DEBUG=True, and SECURE_SSL_REDIRECT=False)
echo -e "${CYAN}Starting IAM Backend on 127.0.0.1:8001...${NC}"
(
    cd "$ADMIN_DIR"
    export DJANGO_SETTINGS_MODULE="backend.settings"
    export DEBUG="True"
    export SECURE_SSL_REDIRECT="False"
    exec "$ADMIN_PY" manage.py runserver 127.0.0.1:8001 2>&1 | sed -u "s/^/$(printf "${CYAN}[IAM-8001]${NC} ")/"
) &
PID_IAM=$!

# Wait for IAM backend to start listening on port 8001
IAM_READY=0
for i in {1..50}; do
    if ! kill -0 "$PID_IAM" 2>/dev/null; then
        echo -e "${RED}Error: IAM Backend process died prematurely! Check logs above.${NC}"
        exit 1
    fi
    if lsof -Pi :8001 -sTCP:LISTEN -t >/dev/null 2>&1; then
        IAM_READY=1
        echo -e "${CYAN}IAM Backend is ready and listening on port 8001.${NC}"
        break
    fi
    sleep 0.2
done

if [ "$IAM_READY" -ne 1 ]; then
    echo -e "${RED}Error: IAM Backend timed out before opening port 8001.${NC}"
    exit 1
fi

# 2. Start Fusion Integrated Backend
echo -e "${GREEN}Starting Integrated Backend on 0.0.0.0:8002...${NC}"
(
    cd "$INTEGRATED_DIR"
    export DJANGO_SETTINGS_MODULE="config.settings.dev"
    exec "$INTEGRATED_PY" manage.py runserver 0.0.0.0:8002 2>&1 | sed -u "s/^/$(printf "${GREEN}[BACKEND-8002]${NC} ")/"
) &
PID_BACKEND=$!

# 3. Start Frontend Client
echo -e "${YELLOW}Starting Frontend Vite Client on port 5173...${NC}"
(
    cd "$CLIENT_DIR"
    exec npm run dev 2>&1 | sed -u "s/^/$(printf "${YELLOW}[CLIENT-VITE]${NC} ")/"
) &
PID_CLIENT=$!

# Wait for background processes
wait
