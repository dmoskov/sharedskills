#!/bin/bash
# This script sets up NetworkX in your PYTHONPATH

NETWORKX_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/networkx"

echo "Setting up NetworkX from: $NETWORKX_DIR"

# Add to PYTHONPATH
export PYTHONPATH="$NETWORKX_DIR:$PYTHONPATH"

echo "NetworkX has been added to PYTHONPATH"
echo "You can now import networkx in Python"
echo ""
echo "To make this permanent, add this line to your ~/.bashrc or ~/.zshrc:"
echo "export PYTHONPATH=\"$NETWORKX_DIR:\$PYTHONPATH\""