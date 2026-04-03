#!/bin/bash
set -e

echo ""
echo " DFU Wound Intelligence — Starting..."
echo ""

if ! command -v python3 &>/dev/null; then
    echo "[ERROR] Python 3 not found."
    exit 1
fi

# Create venv if needed
if [ ! -d "venv" ]; then
    python3 -m venv venv
fi
source venv/bin/activate

pip install -q --upgrade pip
pip install -q -r backend/requirements.txt

echo ""
echo " Backend : http://localhost:5000"
echo " Frontend: Open frontend/index.html in your browser"
echo " Press Ctrl+C to stop."
echo ""

cd backend && python app.py
