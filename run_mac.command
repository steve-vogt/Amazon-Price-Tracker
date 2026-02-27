#!/bin/bash
# ============================================
#  Amazon Price Tracker — Double-click to run
# ============================================

# Go to the folder where this script lives
cd "$(dirname "$0")"

# Check for Python 3
if ! command -v python3 &> /dev/null; then
    echo ""
    echo "❌ Python 3 is not installed."
    echo ""
    echo "To install, paste these into Terminal:"
    echo ""
    echo '  /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"'
    echo "  brew install python3"
    echo ""
    echo "Then double-click this file again."
    echo ""
    read -p "Press Enter to close..."
    exit 1
fi

echo "🚀 Starting Amazon Price Tracker..."
echo "   (First run auto-installs dependencies — takes ~2 min)"
echo ""

python3 amazon_price_tracker.py
