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
    --nofollow-import-to=alembic \
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

        # Copy the wrapper script to main
        cp "scripts/macos_app_launcher.sh" "$BINARY_PATH"

        # Make the wrapper executable
        chmod +x "$BINARY_PATH"

        echo -e "${GREEN}Login shell wrapper installed successfully!${NC}"
        echo -e "${CYAN}The app will now launch with your shell environment (.zshrc, .bash_profile, etc.)${NC}"
    fi
fi

if [ $? -eq 0 ]; then
    echo ""
    echo -e "${GREEN}Build completed successfully!${NC}"
    echo -e "${GREEN}Executable location: build/$EXECUTABLE_NAME${NC}"
    echo ""

    # Create package for different platforms
    if [ "$OS" = "Darwin" ]; then
        # macOS: Create DMG installer
        echo -e "${CYAN}Creating DMG installer...${NC}"

        DMG_NAME="alaye-darwin-$(date +%Y%m%d).dmg"
        DMG_PATH="build/$DMG_NAME"

        # Create a temporary directory for DMG contents
        TEMP_DIR=$(mktemp -d)
        cp -R "build/$EXECUTABLE_NAME" "$TEMP_DIR/"

        # Create DMG
        hdiutil create -volname "Alaye" -srcfolder "$TEMP_DIR" -ov -format UDZO "$DMG_PATH"

        # Clean up temporary directory
        rm -rf "$TEMP_DIR"

        if [ $? -eq 0 ]; then
            echo ""
            echo -e "${GREEN}DMG created successfully!${NC}"
            echo -e "${GREEN}DMG location: $DMG_PATH${NC}"
            echo ""
            echo -e "${CYAN}To install:${NC}"
            echo -e "${YELLOW}  1. Open $DMG_PATH${NC}"
            echo -e "${YELLOW}  2. Drag Alaye.app to Applications folder${NC}"
        else
            echo ""
            echo -e "${YELLOW}Warning: DMG creation failed, but app bundle was created successfully.${NC}"
            echo -e "${YELLOW}You can still run the app directly from: build/$EXECUTABLE_NAME${NC}"
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