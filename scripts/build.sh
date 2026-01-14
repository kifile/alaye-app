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
npm ci
if ! npm run build; then
    echo ""
    echo -e "${RED}Frontend build failed! Please check the error messages above.${NC}"
    cd ..
    exit 1
fi
cd ..

echo -e "${GREEN}Frontend build completed successfully!${NC}"
echo ""
echo -e "${CYAN}Creating alembic_migrations.zip...${NC}"

# Create zip file using Python script (cross-platform)
cd "$(dirname "$0")/.."
uv run python scripts/create_alembic_zip.py build/alembic_migrations.zip

if [ $? -eq 0 ]; then
    echo -e "${GREEN}alembic_migrations.zip created successfully!${NC}"
else
    echo -e "${RED}Failed to create alembic_migrations.zip${NC}"
    exit 1
fi

cd "$(dirname "$0")/.."

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
        EXECUTABLE_NAME="alaye.app"
        # --macos-app-name sets the display name in Info.plist
        EXTRA_ARGS="--macos-app-name=com.kifile.alaye --macos-app-icon=assets/icon.ico"
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

# Nuitka command (using uv to ensure correct environment)
uv run nuitka \
    $NUITKA_MODE \
    $EXTRA_ARGS \
    --output-dir=build \
    --remove-output \
    --assume-yes-for-downloads \
    --enable-plugin=pywebview \
    --include-data-dir=frontend/out=frontend/out \
    --include-data-files=build/alembic_migrations.zip=alembic_migrations.zip \
    --include-data-files=alembic.ini=alembic.ini \
    --nofollow-import-to=pytest \
    --nofollow-import-to=unittest \
    --nofollow-import-to=test \
    main.py

# For macOS: Setup app bundle with login shell wrapper
if [ "$OS" = "Darwin" ]; then
    if [ -d "build/main.app" ]; then
        echo -e "${CYAN}Renaming main.app to $EXECUTABLE_NAME...${NC}"
        mv "build/main.app" "build/$EXECUTABLE_NAME"
    fi

    # Setup login shell wrapper for macOS app
    APP_MACOS_PATH="build/$EXECUTABLE_NAME/Contents/MacOS"
    BINARY_PATH="$APP_MACOS_PATH/main"

    if [ -f "$BINARY_PATH" ]; then
        echo -e "${CYAN}Setting up login shell wrapper for macOS app...${NC}"

        # Rename the binary executable to main.bin
        mv "$BINARY_PATH" "$APP_MACOS_PATH/main.bin"

        # Fix hardcoded library paths from build environment
        # This is needed when using Python from conda/miniconda, which hardcodes
        # absolute paths to libpython3.X.dylib in the binary
        echo -e "${CYAN}Fixing hardcoded library paths...${NC}"
        MAIN_BIN="$APP_MACOS_PATH/main.bin"

        # Check if there are any hardcoded user paths
        # Note: otool -L output has leading tabs, so don't use ^ anchor
        HARDCODED_PATHS=$(otool -L "$MAIN_BIN" 2>/dev/null | grep "/Users/" || true)

        if [ -n "$HARDCODED_PATHS" ]; then
            echo "$HARDCODED_PATHS"
            # Replace absolute paths with @executable_path
            # This makes dyld search for libraries relative to the executable
            for lib in $(otool -L "$MAIN_BIN" 2>/dev/null | grep "/Users/" | awk '{print $1}'); do
                lib_name=$(basename "$lib")
                echo -e "  ${YELLOW}Fixing: $lib -> @executable_path/$lib_name${NC}"
                install_name_tool -change "$lib" "@executable_path/$lib_name" "$MAIN_BIN"
            done
            echo -e "${GREEN}Library paths fixed successfully!${NC}"
            # Re-sign the binary after install_name_tool modifications
            echo -e "${CYAN}Re-signing binary after path fix...${NC}"
            codesign --force --sign - "$MAIN_BIN" 2>&1 | grep -v "replacing existing" || true
            echo -e "${GREEN}Binary re-signed successfully!${NC}"
        else
            echo -e "${GREEN}No hardcoded library paths found, skipping...${NC}"
        fi

        # Copy the wrapper script to main
        cp "scripts/macos_app_launcher.sh" "$BINARY_PATH"

        # Make the wrapper executable
        chmod +x "$BINARY_PATH"

        echo -e "${GREEN}Login shell wrapper installed successfully!${NC}"
        echo -e "${CYAN}The app will now launch with your shell environment (.zshrc, .bash_profile, etc.)${NC}"

        # Re-sign the entire app bundle to ensure all code signatures are valid
        echo -e "${CYAN}Re-signing app bundle...${NC}"
        codesign --force --deep --sign - "build/$EXECUTABLE_NAME" 2>&1 | grep -v "replacing existing" || true
        echo -e "${GREEN}App bundle re-signed successfully!${NC}"
    fi
fi

if [ $? -eq 0 ]; then
    echo ""
    echo -e "${GREEN}Build completed successfully!${NC}"
    echo -e "${GREEN}Executable location: build/$EXECUTABLE_NAME${NC}"
    echo ""

    # Create package for different platforms
    if [ "$OS" = "Darwin" ]; then
        # macOS: Create DMG installer with node-appdmg
        echo -e "${CYAN}Creating DMG installer...${NC}"

        # Check if node-appdmg is available
        if ! command -v appdmg &> /dev/null && [ ! -f "node_modules/.bin/appdmg" ]; then
            echo -e "${YELLOW}⚠ node-appdmg not found${NC}"
            echo -e "${CYAN}Install it: npm install -g appdmg${NC}"
            echo -e "${YELLOW}Skipping DMG creation${NC}"
        else
            # Generate background image
            if [ -f "scripts/create-dmg-background.sh" ]; then
                echo -e "${CYAN}Generating background...${NC}"
                bash scripts/create-dmg-background.sh
            fi

            DMG_NAME="alaye-darwin-$(date +%Y%m%d).dmg"
            DMG_PATH="build/$DMG_NAME"

            echo -e "${CYAN}Building DMG...${NC}"
            echo -e "${CYAN}  Volume: Alaye${NC}"
            echo -e "${CYAN}  Size: 720x400${NC}"
            echo -e "${CYAN}  Icons: 100px${NC}"

            # Use appdmg or npx
            if command -v appdmg &> /dev/null; then
                appdmg scripts/dmg-config.json "$DMG_PATH"
            else
                npx appdmg scripts/dmg-config.json "$DMG_PATH"
            fi

            if [ $? -eq 0 ]; then
                echo ""
                echo -e "${GREEN}========================================${NC}"
                echo -e "${GREEN}DMG created successfully!${NC}"
                echo -e "${GREEN}========================================${NC}"
                echo -e "${GREEN}DMG location: $DMG_PATH${NC}"
                echo ""
                echo -e "${CYAN}Size: $(ls -lh "$DMG_PATH" | awk '{print $5}')${NC}"
                echo ""
                echo -e "${CYAN}To install:${NC}"
                echo -e "${YELLOW}  1. Open $DMG_PATH${NC}"
                echo -e "${YELLOW}  2. Drag Alaye.app to Applications folder${NC}"
            else
                echo ""
                echo -e "${YELLOW}⚠ DMG creation failed, but app bundle was created successfully.${NC}"
                echo -e "${YELLOW}You can still run the app from: build/$EXECUTABLE_NAME${NC}"
            fi
        fi
    elif [ "$OS" = "Linux" ]; then
        # Linux: Create tar.gz package
        echo -e "${CYAN}Creating tar.gz package...${NC}"

        TAR_NAME="alaye-linux-$(date +%Y%m%d).tar.gz"
        TAR_PATH="build/$TAR_NAME"

        # Create tar.gz
        tar -czf "$TAR_PATH" -C "build" "$EXECUTABLE_NAME"

        if [ $? -eq 0 ]; then
            echo ""
            echo -e "${GREEN}tar.gz package created successfully!${NC}"
            echo -e "${GREEN}Package location: $TAR_PATH${NC}"
            echo ""
            echo -e "${CYAN}To distribute:${NC}"
            echo -e "${YELLOW}  1. Share $TAR_PATH${NC}"
            echo -e "${YELLOW}  2. Users extract: tar -xzf $TAR_NAME${NC}"
            echo -e "${YELLOW}  3. Run: ./$EXECUTABLE_NAME${NC}"
        else
            echo ""
            echo -e "${YELLOW}Warning: Package creation failed, but executable was created successfully.${NC}"
            echo -e "${YELLOW}You can still run the app directly from: build/$EXECUTABLE_NAME${NC}"
        fi
    else
        # Other platforms: Just show executable location
        echo -e "${CYAN}To run the application:${NC}"
        echo -e "${YELLOW}  build/$EXECUTABLE_NAME${NC}"
    fi
else
    echo ""
    echo -e "${RED}Build failed! Please check the error messages above.${NC}"
    exit 1
fi

echo ""