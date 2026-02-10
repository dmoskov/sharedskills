#!/bin/bash
# Setup script for Asana CLI
set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
BIN_DIR="${HOME}/bin"

echo "Setting up Asana CLI..."

# Create venv if it doesn't exist
if [ ! -d "$SCRIPT_DIR/.venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv "$SCRIPT_DIR/.venv"
fi

# Install dependencies
echo "Installing dependencies..."
"$SCRIPT_DIR/.venv/bin/pip" install -q -r "$SCRIPT_DIR/requirements.txt"

# Create ~/bin if needed
mkdir -p "$BIN_DIR"

# Symlink the wrapper
if [ -L "$BIN_DIR/asana" ]; then
    rm "$BIN_DIR/asana"
fi
ln -s "$SCRIPT_DIR/bin/asana" "$BIN_DIR/asana"
echo "Linked: $BIN_DIR/asana -> $SCRIPT_DIR/bin/asana"

# Check PATH
if [[ ":$PATH:" != *":$BIN_DIR:"* ]]; then
    echo ""
    echo "Add ~/bin to your PATH if not already present:"
    echo "  export PATH=\"\$HOME/bin:\$PATH\""
    echo ""
fi

# Verify
echo ""
echo "Setup complete. Test with:"
echo "  asana workspaces"
echo ""
echo "Auth required - set one of:"
echo "  export ASANA_ACCESS_TOKEN=\"your_token\"   # Quick start"
echo "  cd $SCRIPT_DIR && python3 oauth_setup.py  # Recommended"
