#!/bin/bash
# Frontend Code Formatting Script for Unix/Linux/macOS
# Usage: format-frontend.sh [options]

# Set default values
DO_CHECK=0
DO_VERBOSE=0

# Simple argument parsing
for arg in "$@"; do
    if [ "$arg" = "--check" ]; then
        DO_CHECK=1
    elif [ "$arg" = "--verbose" ]; then
        DO_VERBOSE=1
    elif [ "$arg" = "--help" ] || [ "$arg" = "-h" ]; then
        echo "Frontend Code Formatting Script"
        echo ""
        echo "Usage: $0 [options]"
        echo ""
        echo "Options:"
        echo "  --check     Check code format without modifying files"
        echo "  --verbose   Show detailed output"
        echo "  --help      Show this help message"
        echo ""
        echo "Examples:"
        echo "  $0                 Format all frontend files"
        echo "  $0 --check         Check format only"
        echo "  $0 --verbose       Show detailed output"
        echo ""
        exit 0
    else
        echo "ERROR: Unknown argument: $arg"
        echo "Use --help for usage information"
        exit 1
    fi
done

# Check prerequisites
if [ ! -d "frontend" ]; then
    echo "ERROR: frontend directory not found"
    exit 1
fi

if ! command -v node &> /dev/null; then
    echo "ERROR: Node.js not found"
    exit 1
fi

if ! command -v npm &> /dev/null; then
    echo "ERROR: npm not found"
    exit 1
fi

echo "Frontend Code Formatting"
if [ "$DO_CHECK" -eq 1 ]; then
    echo "Mode: Check only"
else
    echo "Mode: Format"
fi

# Change to frontend directory
cd frontend

# Run Prettier
echo ""
echo "Running Prettier..."
if [ "$DO_CHECK" -eq 1 ]; then
    if [ "$DO_VERBOSE" -eq 1 ]; then
        npm run format:check
    else
        npm run format:check > /dev/null 2>&1
    fi
else
    if [ "$DO_VERBOSE" -eq 1 ]; then
        npm run format
    else
        npm run format > /dev/null 2>&1
    fi
fi

if [ $? -ne 0 ]; then
    echo "ERROR: Prettier failed"
    cd ..
    exit 1
fi
echo "Prettier: OK"

# Run ESLint
echo ""
echo "Running ESLint..."
if [ "$DO_CHECK" -eq 1 ]; then
    if [ "$DO_VERBOSE" -eq 1 ]; then
        npm run lint:check
    else
        npm run lint:check > /dev/null 2>&1
    fi
else
    if [ "$DO_VERBOSE" -eq 1 ]; then
        npm run lint
    else
        npm run lint > /dev/null 2>&1
    fi
fi

if [ $? -ne 0 ]; then
    echo "WARNING: ESLint found issues"
    if [ "$DO_CHECK" -eq 1 ]; then
        cd ..
        exit 1
    fi
else
    echo "ESLint: OK"
fi

# Return to project root
cd ..

echo ""
echo "Frontend formatting completed successfully"
exit 0