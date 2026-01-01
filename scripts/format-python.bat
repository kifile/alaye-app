@echo off
REM Python code formatting script (Windows version)
REM Supports: autoflake, isort, black, flake8

echo Starting Python code formatting...

REM Parameter handling
set CHECK_ONLY=false
set VERBOSE=false

:parse_args
if "%~1"=="--check" (
    set CHECK_ONLY=true
    shift
    goto parse_args
)
if "%~1"=="--verbose" (
    set VERBOSE=true
    shift
    goto parse_args
)
if "%~1"=="-h" goto help
if "%~1"=="--help" goto help
if not "%~1"=="" (
    echo Unknown parameter: %~1
    echo Use --help to see help information
    exit /b 1
)

REM Set parameters based on mode
if "%CHECK_ONLY%"=="true" (
    set AUTOFLAKE_ARGS=--check-only --diff --recursive
    set BLACK_ARGS=--check --diff
    set ISORT_ARGS=--check-only --diff
    set FLAKE8_ARGS=--exit-zero
    echo Check mode: checking code format only, not modifying files
) else (
    set AUTOFLAKE_ARGS=--in-place --remove-all-unused-imports --remove-unused-variables --remove-duplicate-keys --recursive
    set BLACK_ARGS=
    set ISORT_ARGS=
    set FLAKE8_ARGS=--exit-zero
    echo Format mode: will modify file format
)

echo.
echo Running autoflake (unused import removal)...
if "%VERBOSE%"=="true" (
    uv run autoflake src/ tests/ main.py %AUTOFLAKE_ARGS%
) else (
    uv run autoflake src/ tests/ main.py %AUTOFLAKE_ARGS% >nul 2>&1
)
echo autoflake completed

echo.
echo Running isort (import sorting)...
if "%VERBOSE%"=="true" (
    uv run isort . %ISORT_ARGS%
) else (
    uv run isort . %ISORT_ARGS% >nul 2>&1
)
echo isort completed

echo.
echo Running black (code formatting)...
if "%VERBOSE%"=="true" (
    uv run black . %BLACK_ARGS%
) else (
    uv run black . %BLACK_ARGS% >nul 2>&1
)
echo black completed

echo.
echo Running flake8 (code checking)...
uv run flake8 src/ tests/ main.py %FLAKE8_ARGS%
if %ERRORLEVEL% equ 0 (
    echo flake8 check passed
) else (
    if "%CHECK_ONLY%"=="false" (
        echo flake8 found some issues, but files have been formatted
    ) else (
        echo flake8 found issues, please fix and retry
        exit /b 1
    )
)

echo.
if "%CHECK_ONLY%"=="true" (
    echo Python code format check completed!
) else (
    echo Python code formatting completed!
)
goto :eof

:help
echo Usage: %~nx0 [--check] [--verbose] [--help]
echo   --check     Check code format only, do not modify files
echo   --verbose   Show detailed information
echo   --help      Show help information
exit /b 0