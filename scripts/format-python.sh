#!/bin/bash
# Python Code Formatting Script for Unix/Linux/macOS
# Usage: format-python.sh [options]

# Set default values
CHECK_ONLY=0
VERBOSE=0

# Simple argument parsing
for arg in "$@"; do
    if [ "$arg" = "--check" ]; then
        CHECK_ONLY=1
    elif [ "$arg" = "--verbose" ]; then
        VERBOSE=1
    elif [ "$arg" = "--help" ] || [ "$arg" = "-h" ]; then
        echo "Python Code Formatting Script"
        echo ""
        echo "Usage: $0 [options]"
        echo ""
        echo "Options:"
        echo "  --check     Check code format without modifying files"
        echo "  --verbose   Show detailed output"
        echo "  --help      Show this help message"
        echo ""
        echo "Examples:"
        echo "  $0                  Format all Python files"
        echo "  $0 --check          Check format only"
        echo "  $0 --verbose        Show detailed output"
        echo ""
        exit 0
    else
        echo "ERROR: Unknown argument: $arg"
        echo "Use --help for usage information"
        exit 1
    fi
done

# Check prerequisites
if ! command -v uv &> /dev/null; then
    echo "ERROR: uv not found"
    exit 1
fi

echo "Python Code Formatting"
if [ "$CHECK_ONLY" -eq 1 ]; then
    echo "Mode: Check only"
else
    echo "Mode: Format"
fi

# Set tool arguments based on mode
if [ "$CHECK_ONLY" -eq 1 ]; then
    AUTOFLAKE_ARGS="--check-only --diff --recursive"
    BLACK_ARGS="--check --diff"
    ISORT_ARGS="--check-only --diff"
    FLAKE8_ARGS="--exit-zero"
else
    AUTOFLAKE_ARGS="--in-place --remove-all-unused-imports --remove-unused-variables --remove-duplicate-keys --recursive"
    BLACK_ARGS=""
    ISORT_ARGS=""
    FLAKE8_ARGS="--exit-zero"
fi

# Run autoflake
echo ""
echo "Running autoflake..."
if [ "$VERBOSE" -eq 1 ]; then
    uv run autoflake src/ tests/ main.py $AUTOFLAKE_ARGS
else
    uv run autoflake src/ tests/ main.py $AUTOFLAKE_ARGS > /dev/null 2>&1
fi

if [ $? -ne 0 ]; then
    echo "ERROR: autoflake failed"
    exit 1
fi
echo "autoflake: OK"

# Run isort
echo ""
echo "Running isort..."
if [ "$VERBOSE" -eq 1 ]; then
    uv run isort . $ISORT_ARGS
else
    uv run isort . $ISORT_ARGS > /dev/null 2>&1
fi

if [ $? -ne 0 ]; then
    echo "ERROR: isort failed"
    exit 1
fi
echo "isort: OK"

# Run black
echo ""
echo "Running black..."
if [ "$VERBOSE" -eq 1 ]; then
    uv run black . $BLACK_ARGS
else
    uv run black . $BLACK_ARGS > /dev/null 2>&1
fi

if [ $? -ne 0 ]; then
    echo "ERROR: black failed"
    exit 1
fi
echo "black: OK"

# Run flake8
echo ""
echo "Running flake8..."
if [ "$VERBOSE" -eq 1 ]; then
    uv run flake8 src/ tests/ main.py $FLAKE8_ARGS
else
    uv run flake8 src/ tests/ main.py $FLAKE8_ARGS > /dev/null 2>&1
fi

if [ $? -ne 0 ]; then
    echo "WARNING: flake8 found issues"
    if [ "$CHECK_ONLY" -eq 1 ]; then
        exit 1
    fi
else
    echo "flake8: OK"
fi

echo ""
echo "Python formatting completed successfully"
exit 0