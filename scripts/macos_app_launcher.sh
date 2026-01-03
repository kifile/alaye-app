#!/bin/zsh
# Login Shell Wrapper for Alaye App
# This script ensures the app launches with user's login shell environment
# including all environment variables from .zshrc, .bash_profile, etc.

set -e

# Get the directory where this script is located
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

# Path to the actual binary executable
BINARY_EXECUTABLE="$SCRIPT_DIR/main.bin"

# Detect user's default shell from environment
# Fall back to zsh (macOS default since Catalina) if not set
USER_SHELL="${SHELL:-/bin/zsh}"

# Verify the binary exists
if [ ! -f "$BINARY_EXECUTABLE" ]; then
    echo "Error: Cannot find executable binary at $BINARY_EXECUTABLE" >&2
    exit 1
fi

# Ensure the binary is executable
chmod +x "$BINARY_EXECUTABLE"

# Launch the binary through the user's interactive shell
# This ensures all shell configuration files are loaded:
# - For zsh: .zprofile, .zshrc (interactive mode loads both)
# - For bash: .bash_profile, .bashrc
# - Including NVM, pyenv, rvm, and other environment managers
#
# Note: We use interactive shell (-i) instead of login shell (-l) because
# many users (like NVM) configure PATH differently in .zshrc vs .zprofile

# Use exec to replace the shell process with the binary
# This preserves the environment and is more efficient
exec "$USER_SHELL" -i -c "exec \"$BINARY_EXECUTABLE\" \"\$@\"" shell "$@"
