#!/usr/bin/env bash
# wardrobe-twin-agent setup script
# Run this once after cloning the repository.

set -e

echo "============================================="
echo "  wardrobe-twin-agent - Setup"
echo "============================================="
echo ""

# 1. Python backend
echo ">>> Setting up Python virtual environment..."
python3.11 -m venv .venv
source .venv/bin/activate || { .venv\Scripts\Activate.ps1 2>/dev/null; }

echo ">>> Installing core Python dependencies (lightweight)..."
pip install -e .

echo ""
echo ">>> Optional: Install heavy ML dependencies for full features:"
echo "    pip install -e \".[ml-heavy]\""
echo "    This includes: detectron2, mediapipe, segment-anything, scikit-learn"
echo "    Note: detectron2 may require special install on some platforms."
echo "    See: https://detectron2.readthedocs.io/en/latest/tutorials/install.html"
echo ""

# 2. UI
echo ">>> Setting up Electron + React UI..."
cd ui
npm install
cd ..

echo ""
echo ">>> Creating data directories..."
mkdir -p data/models data/avatars data/wardrobe_images data/cache

echo ""
echo ">>> Copying .env template..."
if [ ! -f .env ]; then
    cp .env.example .env
    echo "    Created .env - edit it to add your API keys"
else
    echo "    .env already exists, keeping it"
fi

echo ""
echo "============================================="
echo "  Setup complete!"
echo "============================================="
echo ""
echo "  To start the backend:"
echo "    source .venv/bin/activate  (Linux/Mac)"
echo "    .venv\\Scripts\\Activate.ps1  (Windows)"
echo "    python -m backend.api.server"
echo ""
echo "  To start the UI:"
echo "    cd ui && npm run dev"
echo ""
echo "  To load the browser extension:"
echo "    1. Open Chrome -> chrome://extensions"
echo "    2. Enable Developer mode"
echo "    3. Load unpacked -> select the extension/ folder"
echo ""
echo "  API keys (optional, for LLM advisor):"
echo "    Edit .env and add your ANTHROPIC_API_KEY and/or OPENAI_API_KEY"
echo ""
