#!/bin/bash

# Create clean white DMG background if not exists

set -e

BG_FILE="scripts/dmg-background.png"

# Check if background already exists
if [ -f "$BG_FILE" ]; then
    echo "✓ Background exists: $BG_FILE"
    exit 0
fi

WIDTH=720
HEIGHT=400

echo "Creating clean white background..."

if command -v magick &> /dev/null; then
    # ImageMagick v7 - text at top, not center
    magick -size ${WIDTH}x${HEIGHT} gradient:#FFFFFF-#FFFEFE \
        -fill "#555555" \
        -font Helvetica \
        -pointsize 18 \
        -gravity north \
        -annotate +0+50 'Drag Alaye to Applications' \
        "$BG_FILE"
    echo "✓ Created: $BG_FILE"
elif command -v convert &> /dev/null; then
    # ImageMagick v6
    convert -size ${WIDTH}x${HEIGHT} gradient:#FFFFFF-#FFFEFE \
        -fill "#555555" \
        -font Helvetica \
        -pointsize 18 \
        -gravity north \
        -annotate +0+50 'Drag Alaye to Applications' \
        "$BG_FILE"
    echo "✓ Created: $BG_FILE"
else
    echo "✗ ImageMagick not found"
    exit 1
fi
