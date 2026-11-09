#!/bin/bash
# MedTrack Project - Complete Run Script
# This script starts backend, frontend, and prepares BOM testing

echo "=========================================="
echo "  MedTrack ERP - Build & Run Script"
echo "=========================================="

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Set environment
PROJECT_DIR="."
BACKEND_DIR="backend"
FRONTEND_DIR="frontend"

# Function to run commands
run_step() {
    echo -e "${BLUE}➤ $1${NC}"
}

success() {
    echo -e "${GREEN}✅ $1${NC}"
}

# Step 1: Build Frontend
run_step "Building Frontend..."
cd "$FRONTEND_DIR"
npm run build
if [ $? -eq 0 ]; then
    success "Frontend build completed"
else
    echo "❌ Frontend build failed"
    exit 1
fi
cd ..

# Step 2: Start Backend
run_step "Starting Backend API (port 8000)..."
python -m venv .venv 2>/dev/null
source .venv/Scripts/activate 2>/dev/null || . .venv/Scripts/activate
python -m uvicorn backend.app.main:app --host 0.0.0.0 --port 8000 &
BACKEND_PID=$!
sleep 3
success "Backend started (PID: $BACKEND_PID)"

# Step 3: Start Frontend Dev Server
run_step "Starting Frontend Dev Server (port 3000)..."
cd "$FRONTEND_DIR"
npm run dev &
FRONTEND_PID=$!
sleep 5
success "Frontend dev server started (PID: $FRONTEND_PID)"
cd ..

# Step 4: Info about testing
echo ""
echo "=========================================="
echo "  ${GREEN}Services Running${NC}"
echo "=========================================="
echo "  Backend API  : http://localhost:8000"
echo "  Frontend     : http://localhost:3000"
echo "  Login URL    : http://localhost:3000"
echo ""
echo "  Credentials:"
echo "  Email        : admin@medtrack-demo.com"
echo "  Password     : Demo@1234"
echo ""
echo "=========================================="
echo "  ${YELLOW}To Test BOM${NC}"
echo "=========================================="
echo "  Run in another terminal:"
echo "  python test_bom_api.py"
echo ""
echo "=========================================="
echo "  Press Ctrl+C to stop services"
echo "=========================================="

# Keep script running
wait
