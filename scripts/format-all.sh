#!/bin/bash
# Unified Code Formatting Script for Unix/Linux/macOS
# Formats Python and frontend code

# Set default values
CHECK_ONLY=0
VERBOSE=0
PYTHON_ONLY=0
FRONTEND_ONLY=0

# Simple argument parsing
for arg in "$@"; do
    if [ "$arg" = "--check" ]; then
        CHECK_ONLY=1
    elif [ "$arg" = "--verbose" ]; then
        VERBOSE=1
    elif [ "$arg" = "--python-only" ]; then
        PYTHON_ONLY=1
    elif [ "$arg" = "--frontend-only" ]; then
        FRONTEND_ONLY=1
    elif [ "$arg" = "--help" ] || [ "$arg" = "-h" ]; then
        echo "Unified Code Formatting Script"
        echo ""
        echo "Usage: $0 [options]"
        echo ""
        echo "Options:"
        echo "  --check         Check code format without modifying files"
        echo "  --verbose       Show detailed information"
        echo "  --python-only   Format Python code only"
        echo "  --frontend-only Format frontend code only"
        echo "  --help          Show this help message"
        echo ""
        echo "Examples:"
        echo "  $0                         Format all code"
        echo "  $0 --check                 Check all code format"
        echo "  $0 --python-only           Format Python only"
        echo "  $0 --frontend-only         Format frontend only"
        echo "  $0 --verbose               Show detailed output"
        echo ""
        exit 0
    else
        echo "ERROR: Unknown argument: $arg"
        echo "Use --help for usage information"
        exit 1
    fi
done

# Check for conflicting options
if [ "$PYTHON_ONLY" -eq 1 ] && [ "$FRONTEND_ONLY" -eq 1 ]; then
    echo "ERROR: Cannot specify both --python-only and --frontend-only"
    exit 1
fi

# Get script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "Starting unified code formatting..."

echo "Mode selection:"
if [ "$CHECK_ONLY" -eq 1 ]; then
    echo " - Check mode"
else
    echo " - Format mode"
fi
if [ "$PYTHON_ONLY" -eq 1 ]; then
    echo " - Python only"
fi
if [ "$FRONTEND_ONLY" -eq 1 ]; then
    echo " - Frontend only"
fi

# Python code formatting
if [ "$FRONTEND_ONLY" -ne 1 ]; then
    echo ""
    echo "Processing Python code..."
    if [ "$CHECK_ONLY" -eq 1 ]; then
        if [ "$VERBOSE" -eq 1 ]; then
            "$SCRIPT_DIR/format-python.sh" --check --verbose
        else
            "$SCRIPT_DIR/format-python.sh" --check
        fi
    else
        if [ "$VERBOSE" -eq 1 ]; then
            "$SCRIPT_DIR/format-python.sh" --verbose
        else
            "$SCRIPT_DIR/format-python.sh"
        fi
    fi

    # In check mode, script exit code indicates format issues
    if [ $? -ne 0 ]; then
        if [ "$CHECK_ONLY" -eq 1 ]; then
            exit 1
        else
            # In format mode, we expect success if we reach here
            echo "WARNING: Python code formatting had issues, but processing continued"
        fi
    fi
    echo "Python code processing completed"
fi

# Frontend code formatting
if [ "$PYTHON_ONLY" -ne 1 ]; then
    echo ""
    echo "Processing frontend code..."
    if [ "$CHECK_ONLY" -eq 1 ]; then
        if [ "$VERBOSE" -eq 1 ]; then
            "$SCRIPT_DIR/format-frontend.sh" --check --verbose
        else
            "$SCRIPT_DIR/format-frontend.sh" --check
        fi
    else
        if [ "$VERBOSE" -eq 1 ]; then
            "$SCRIPT_DIR/format-frontend.sh" --verbose
        else
            "$SCRIPT_DIR/format-frontend.sh"
        fi
    fi

    # Check if there were actual formatting issues
    if [ $? -ne 0 ]; then
        echo "WARNING: Frontend code formatting had issues, but processing continued"
        if [ "$CHECK_ONLY" -eq 1 ]; then
            exit 1
        fi
    fi
    echo "Frontend code processing completed"
fi

echo ""
echo "All code formatting completed successfully!"

# Display summary information
if [ "$CHECK_ONLY" -eq 1 ]; then
    echo "Summary: All code format checks passed"
else
    echo "Summary: All code has been successfully formatted"
fi

if [ "$VERBOSE" -eq 1 ]; then
    echo ""
    echo "Tips:"
    echo "  - Use --check to check format without modifying files"
    echo "  - Use --python-only or --frontend-only to process specific languages"
    echo "  - Use --verbose to see detailed processing steps"
fi

exit 0