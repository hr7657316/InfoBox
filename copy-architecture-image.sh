#!/bin/bash

# Script to copy the system architecture image to the correct location
# Usage: ./copy-architecture-image.sh path/to/your/architecture/image.png

if [ $# -eq 0 ]; then
    echo "Usage: $0 <path-to-architecture-image>"
    echo "Example: $0 ~/Downloads/system-architecture.png"
    exit 1
fi

SOURCE_IMAGE="$1"
DEST_DIR="docs/images"
DEST_FILE="$DEST_DIR/system-architecture.png"

# Create directory if it doesn't exist
mkdir -p "$DEST_DIR"

# Copy the image
if [ -f "$SOURCE_IMAGE" ]; then
    cp "$SOURCE_IMAGE" "$DEST_FILE"
    echo "✅ Architecture image copied to $DEST_FILE"
    echo "📝 The README.md has been updated to reference this image"
    echo "🚀 Ready to commit and push!"
else
    echo "❌ Error: Source image file not found: $SOURCE_IMAGE"
    exit 1
fi