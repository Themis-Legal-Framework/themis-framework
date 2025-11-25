#!/bin/bash

# LLM-COUNSEL Startup Script
# Starts both the backend API server and frontend dev server

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}"
echo "  ⚖️  LLM-COUNSEL"
echo "  Multi-Model Legal Strategy Deliberation System"
echo -e "${NC}"

# Check for .env file
if [ ! -f .env ]; then
    echo -e "${YELLOW}Warning: No .env file found.${NC}"
    echo "Creating .env from .env.example..."
    if [ -f .env.example ]; then
        cp .env.example .env
        echo -e "${YELLOW}Please edit .env and add your OPENROUTER_API_KEY${NC}"
    else
        echo "OPENROUTER_API_KEY=" > .env
        echo -e "${RED}Please add your OpenRouter API key to .env${NC}"
    fi
fi

# Load environment variables
export $(grep -v '^#' .env | xargs)

# Check for API key
if [ -z "$OPENROUTER_API_KEY" ]; then
    echo -e "${RED}Error: OPENROUTER_API_KEY not set in .env${NC}"
    echo "Get your API key from https://openrouter.ai/keys"
    exit 1
fi

# Create data directory if it doesn't exist
mkdir -p data/conversations

# Check if uv is available for Python
if command -v uv &> /dev/null; then
    PYTHON_CMD="uv run python"
    echo -e "${GREEN}Using uv for Python environment${NC}"
else
    PYTHON_CMD="python"
    echo -e "${YELLOW}Using system Python (consider installing uv for better dependency management)${NC}"
fi

# Function to cleanup on exit
cleanup() {
    echo ""
    echo -e "${YELLOW}Shutting down...${NC}"
    kill $BACKEND_PID 2>/dev/null || true
    kill $FRONTEND_PID 2>/dev/null || true
    exit 0
}

trap cleanup SIGINT SIGTERM

# Start backend
echo -e "${BLUE}Starting backend server on http://localhost:8001...${NC}"
cd "$(dirname "$0")"
$PYTHON_CMD -m uvicorn backend.main:app --host 0.0.0.0 --port 8001 --reload &
BACKEND_PID=$!

# Wait for backend to start
sleep 2

# Check if backend started successfully
if ! kill -0 $BACKEND_PID 2>/dev/null; then
    echo -e "${RED}Failed to start backend server${NC}"
    exit 1
fi

echo -e "${GREEN}Backend started (PID: $BACKEND_PID)${NC}"

# Start frontend
echo -e "${BLUE}Starting frontend server on http://localhost:5173...${NC}"
cd frontend

# Check if node_modules exists
if [ ! -d "node_modules" ]; then
    echo "Installing frontend dependencies..."
    npm install
fi

npm run dev &
FRONTEND_PID=$!

cd ..

# Wait for frontend to start
sleep 3

# Check if frontend started successfully
if ! kill -0 $FRONTEND_PID 2>/dev/null; then
    echo -e "${RED}Failed to start frontend server${NC}"
    kill $BACKEND_PID 2>/dev/null
    exit 1
fi

echo -e "${GREEN}Frontend started (PID: $FRONTEND_PID)${NC}"

echo ""
echo -e "${GREEN}═══════════════════════════════════════════════════════════${NC}"
echo -e "${GREEN}  LLM-COUNSEL is running!${NC}"
echo -e "${GREEN}═══════════════════════════════════════════════════════════${NC}"
echo ""
echo -e "  Frontend:  ${BLUE}http://localhost:5173${NC}"
echo -e "  Backend:   ${BLUE}http://localhost:8001${NC}"
echo -e "  API Docs:  ${BLUE}http://localhost:8001/docs${NC}"
echo ""
echo -e "  Press ${YELLOW}Ctrl+C${NC} to stop all servers"
echo ""

# Wait for processes
wait
