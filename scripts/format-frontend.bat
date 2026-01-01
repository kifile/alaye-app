@echo off
REM Frontend Code Formatting Script for Windows
REM Usage: format-frontend.bat [options]

REM Set default values
set "DO_CHECK=0"
set "DO_VERBOSE=0"

REM Simple argument parsing
for %%A in (%*) do (
    if "%%A"=="--check" set "DO_CHECK=1"
    if "%%A"=="--verbose" set "DO_VERBOSE=1"
    if "%%A"=="--help" goto :help
    if "%%A"=="-h" goto :help
)

REM Check prerequisites
if not exist "frontend" (
    echo ERROR: frontend directory not found
    exit /b 1
)

where node >nul 2>&1
if %ERRORLEVEL% neq 0 (
    echo ERROR: Node.js not found
    exit /b 1
)

echo Frontend Code Formatting
if "%DO_CHECK%"=="1" (
    echo Mode: Check only
) else (
    echo Mode: Format
)

REM Change to frontend directory
cd frontend

REM Run Prettier
echo.
echo Running Prettier...
if "%DO_CHECK%"=="1" (
    if "%DO_VERBOSE%"=="1" (
        call npm run format:check
    ) else (
        call npm run format:check >nul 2>&1
    )
) else (
    if "%DO_VERBOSE%"=="1" (
        call npm run format
    ) else (
        call npm run format >nul 2>&1
    )
)

if %ERRORLEVEL% neq 0 (
    echo ERROR: Prettier failed
    cd ..
    exit /b 1
)
echo Prettier: OK

REM Run ESLint
echo.
echo Running ESLint...
if "%DO_CHECK%"=="1" (
    if "%DO_VERBOSE%"=="1" (
        call npm run lint:check
    ) else (
        call npm run lint:check >nul 2>&1
    )
) else (
    if "%DO_VERBOSE%"=="1" (
        call npm run lint
    ) else (
        call npm run lint >nul 2>&1
    )
)

if %ERRORLEVEL% neq 0 (
    echo WARNING: ESLint found issues
    if "%DO_CHECK%"=="1" (
        cd ..
        exit /b 1
    )
) else (
    echo ESLint: OK
)

REM Return to project root
cd ..

echo.
echo Frontend formatting completed successfully
exit /b 0

:help
echo Frontend Code Formatting Script
echo.
echo Usage: %~nx0 [options]
echo.
echo Options:
echo   --check     Check code format without modifying files
echo   --verbose   Show detailed output
echo   --help      Show this help message
echo.
echo Examples:
echo   %~nx0                 Format all frontend files
echo   %~nx0 --check         Check format only
echo   %~nx0 --verbose       Show detailed output
exit /b 0