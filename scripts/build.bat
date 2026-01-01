@echo off
echo Building pywebview application with Nuitka...
echo.

REM Check if nuitka is installed
python -c "import nuitka" 2>nul
if errorlevel 1 (
    echo Error: Nuitka is not installed. Please install it first:
    echo pip install nuitka
    pause
    exit /b 1
)

REM Check if main.py exists
if not exist "main.py" (
    echo Error: main.py not found. Please run this script from the project root directory.
    pause
    exit /b 1
)

REM Create build directory if it doesn't exist
if not exist "build" mkdir "build"

echo Building frontend resources...
echo Output will be saved to: frontend\out
echo.

REM Build frontend resources
cd frontend
call npm run build
if errorlevel 1 (
    echo.
    echo Frontend build failed! Please check the error messages above.
    cd ..
    pause
    exit /b 1
)
cd ..

echo Frontend build completed successfully!
echo.
echo Starting Nuitka compilation...
echo Output will be saved to: build\alaye.exe
echo.

nuitka ^
    --onefile ^
    --windows-console-mode=disable ^
    --output-dir=build ^
    --output-filename=alaye.exe ^
    --remove-output ^
    --assume-yes-for-downloads ^
    --enable-plugin=pywebview ^
    --include-data-dir=frontend/out=frontend/out ^
    main.py

if errorlevel 1 (
    echo.
    echo Build failed! Please check the error messages above.
    pause
    exit /b 1
) else (
    echo.
    echo Build completed successfully!
    echo Executable location: build\alaye.exe
    echo.
    echo To run the application:
    echo   build\alaye.exe
)

pause