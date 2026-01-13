@echo off
setlocal EnableDelayedExpansion
echo Building pywebview application with Nuitka...
echo.

REM Check if nuitka is installed
uv run python -c "import nuitka" 2>nul
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
call npm ci
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

uv run nuitka ^
    --onefile ^
    --windows-console-mode=disable ^
    --output-dir=build ^
    --output-filename=alaye.exe ^
    --remove-output ^
    --assume-yes-for-downloads ^
    --enable-plugin=pywebview ^
    --include-data-dir=frontend/out=frontend/out ^
    --include-data-dir=alembic=alembic ^
    --include-data-files=alembic.ini=alembic.ini ^
    --windows-icon-from-ico=assets/icon.ico ^
    --nofollow-import-to=pytest ^
    --nofollow-import-to=unittest ^
    --nofollow-import-to=test ^
    main.py

echo.
echo ============================================================================
echo.

if not exist "build\alaye.exe" (
    echo ERROR: Executable not found at build\alaye.exe
    echo.
    pause
    exit /b 1
)

echo Build completed successfully!
echo Executable location: build\alaye.exe
echo.
echo.

REM Create ZIP package
echo Creating ZIP package...
echo.

uv run python scripts/create_zip.py build/alaye.exe build

echo.
echo ============================================================================
echo.

if exist "build\alaye-windows-*.zip" (
    echo ZIP package created successfully!
    echo Check the build directory for the ZIP file.
) else (
    echo Warning: ZIP creation may have failed.
    echo But executable was created successfully at build\alaye.exe
)

echo.
pause