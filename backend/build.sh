#!/bin/bash
# Build script for Render to install CPU-only PyTorch
# This script MUST be executable: chmod +x build.sh
# Configure Render to use this as build command or it will run automatically if named build.sh in root

set -e

echo "=========================================="
echo "Installing CPU-only PyTorch for memory efficiency..."
echo "=========================================="

# Set environment variable to prevent CUDA installation
export TORCH_INSTALL_URL="https://download.pytorch.org/whl/cpu"

# Install PyTorch CPU-only version FIRST (before sentence-transformers pulls in CUDA version)
pip install torch==2.9.0 torchvision torchaudio --index-url https://download.pytorch.org/whl/cpu

# Install other dependencies (sentence-transformers will now use the CPU-only torch)
pip install -r requirements.txt

echo "=========================================="
echo "Build completed successfully!"
echo "PyTorch CPU-only installed (~500MB saved vs CUDA)"
echo "=========================================="

