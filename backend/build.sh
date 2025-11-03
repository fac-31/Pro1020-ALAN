#!/bin/bash
# Build script for Render to install CPU-only PyTorch

set -e

echo "Installing CPU-only PyTorch for memory efficiency..."

# Install PyTorch CPU-only version before other dependencies
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cpu

# Install other dependencies
pip install -r requirements.txt

echo "Build completed successfully!"

