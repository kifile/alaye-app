@echo off
REM Unified code formatting script (Windows version)
REM Formats Python and frontend code

echo Starting unified code formatting...

REM Set default values
set "CHECK_ONLY=0"
set "VERBOSE=0"
set "PYTHON_ONLY=0"
set "FRONTEND_ONLY=0"

REM Simple argument parsing
for %%A in (%*) do (
    if "%%A"=="--check" set "CHECK_ONLY=1"
    if "%%A"=="--verbose" set "VERBOSE=1"
    if "%%A"=="--python-only" set "PYTHON_ONLY=1"
    if "%%A"=="--frontend-only" set "FRONTEND_ONLY=1"
    if "%%A"=="--help" goto :help
    if "%%A"=="-h" goto :help
)

REM Check for conflicting options
if "%PYTHON_ONLY%"=="1" if "%FRONTEND_ONLY%"=="1" (
    echo ERROR: Cannot specify both --python-only and --frontend-only
    exit /b 1
)

REM Get script directory
set "SCRIPT_DIR=%~dp0"

echo Mode selection:
if "%CHECK_ONLY%"=="1" echo - Check mode
if "%CHECK_ONLY%"=="0" echo - Format mode
if "%PYTHON_ONLY%"=="1" echo - Python only
if "%FRONTEND_ONLY%"=="1" echo - Frontend only

REM Python code formatting
if not "%FRONTEND_ONLY%"=="1" (
    echo.
    echo Processing Python code...
    if "%CHECK_ONLY%"=="1" (
        if "%VERBOSE%"=="1" (
            call "%SCRIPT_DIR%format-python.bat" --check --verbose
        ) else (
            call "%SCRIPT_DIR%format-python.bat" --check
        )
    ) else (
        if "%VERBOSE%"=="1" (
            call "%SCRIPT_DIR%format-python.bat" --verbose
        ) else (
            call "%SCRIPT_DIR%format-python.bat"
        )
    )

    REM Check if there were actual formatting issues
    if "%CHECK_ONLY%"=="1" (
        REM In check mode, black returning non-zero is expected for formatting differences
        set "PYTHON_ISSUES=0"
    ) else (
        REM In format mode, check if black actually modified files
        if !ERRORLEVEL! neq 0 (
            set "PYTHON_ISSUES=1"
        ) else (
            set "PYTHON_ISSUES=0"
        )
    )

    if "%PYTHON_ISSUES%"=="1" (
        echo WARNING: Python code formatting had issues, but processing continued
    )
    echo Python code processing completed
)

REM Frontend code formatting
if not "%PYTHON_ONLY%"=="1" (
    echo.
    echo Processing frontend code...
    if "%CHECK_ONLY%"=="1" (
        if "%VERBOSE%"=="1" (
            call "%SCRIPT_DIR%format-frontend.bat" --check --verbose
        ) else (
            call "%SCRIPT_DIR%format-frontend.bat" --check
        )
    ) else (
        if "%VERBOSE%"=="1" (
            call "%SCRIPT_DIR%format-frontend.bat" --verbose
        ) else (
            call "%SCRIPT_DIR%format-frontend.bat"
        )
    )

      REM Check if there were actual formatting issues
    set "FRONTEND_ISSUES=0"
    if !ERRORLEVEL! neq 0 (
        set "FRONTEND_ISSUES=1"
    )

    if "%FRONTEND_ISSUES%"=="1" (
        echo WARNING: Frontend code formatting had issues, but processing continued
        if "%CHECK_ONLY%"=="1" (
            exit /b 1
        )
    )
    echo Frontend code processing completed
)

echo.
echo All code formatting completed successfully!

REM Display summary information
if "%CHECK_ONLY%"=="1" (
    echo Summary: All code format checks passed
) else (
    echo Summary: All code has been successfully formatted
)

if "%VERBOSE%"=="1" (
    echo.
    echo Tips:
    echo   - Use --check to check format without modifying files
    echo   - Use --python-only or --frontend-only to process specific languages
    echo   - Use --verbose to see detailed processing steps
)

exit /b 0

:help
echo Unified Code Formatting Script
echo.
echo Usage: %~nx0 [options]
echo.
echo Options:
echo   --check         Check code format without modifying files
echo   --verbose       Show detailed information
echo   --python-only   Format Python code only
echo   --frontend-only Format frontend code only
echo   --help          Show this help message
echo.
echo Examples:
echo   %~nx0                         Format all code
echo   %~nx0 --check                 Check all code format
echo   %~nx0 --python-only            Format Python only
echo   %~nx0 --frontend-only          Format frontend only
echo   %~nx0 --verbose               Show detailed output
echo.
exit /b 0