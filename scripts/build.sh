#!/bin/bash

# Build script for pywebview application using Nuitka
# This script compiles main.py into a standalone executable for Linux/macOS

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

echo -e "${GREEN}Building pywebview application with Nuitka...${NC}"
echo ""

# Check if nuitka is installed
if ! python -c "import nuitka" 2>/dev/null; then
    echo -e "${RED}Error: Nuitka is not installed. Please install it first:${NC}"
    echo -e "${YELLOW}  pip install nuitka${NC}"
    exit 1
fi

# Check if main.py exists
if [ ! -f "main.py" ]; then
    echo -e "${RED}Error: main.py not found. Please run this script from the project root directory.${NC}"
    exit 1
fi

# Create build directory if it doesn't exist
mkdir -p "build"

echo -e "${CYAN}Building frontend resources...${NC}"
echo -e "${CYAN}Output will be saved to: frontend/out${NC}"
echo ""

# Build frontend resources
cd frontend
if ! npm run build; then
    echo ""
    echo -e "${RED}Frontend build failed! Please check the error messages above.${NC}"
    cd ..
    exit 1
fi
cd ..

echo -e "${GREEN}Frontend build completed successfully!${NC}"
echo ""
echo -e "${CYAN}Starting Nuitka compilation...${NC}"
echo ""

# Detect platform and set appropriate options
NUITKA_MODE="--onefile"
OS=$(uname -s)
case "$OS" in
    Linux*)
        EXECUTABLE_NAME="alaye"
        # Enable both pywebview and PyQt6 plugins, and include Qt platform plugins
        # Based on Nuitka best practices for Qt applications
        EXTRA_ARGS="--output-filename=$EXECUTABLE_NAME --enable-plugin=pyqt6 --include-qt-plugins=platforms"
        ;;
    Darwin*)
        # macOS needs --mode=app for pywebview with Foundation framework
        NUITKA_MODE="--mode=app"
        EXTRA_ARGS=""
        EXECUTABLE_NAME="alaye.app"
        ;;
    CYGWIN*|MINGW*|MSYS*)
        EXTRA_ARGS="--windows-console-mode=disable --output-filename=$EXECUTABLE_NAME"
        EXECUTABLE_NAME="alaye.exe"
        ;;
    *)
        echo -e "${YELLOW}Warning: Unknown platform $OS, using default options${NC}"
        EXECUTABLE_NAME="alaye"
        EXTRA_ARGS="--output-filename=$EXECUTABLE_NAME"
        ;;
esac

echo -e "${CYAN}Output will be saved to: build/$EXECUTABLE_NAME${NC}"
echo ""

# Nuitka command
nuitka \
    $NUITKA_MODE \
    $EXTRA_ARGS \
    --output-dir=build \
    --remove-output \
    --assume-yes-for-downloads \
    --enable-plugin=pywebview \
    --include-data-dir=frontend/out=frontend/out \
    main.py

if [ $? -eq 0 ]; then
    echo ""
    echo -e "${GREEN}Build completed successfully!${NC}"
    echo -e "${GREEN}Executable location: build/$EXECUTABLE_NAME${NC}"
    echo ""
    echo -e "${CYAN}To run the application:${NC}"
    echo -e "${YELLOW}  build/$EXECUTABLE_NAME${NC}"
else
    echo ""
    echo -e "${RED}Build failed! Please check the error messages above.${NC}"
    exit 1
fi

echo ""