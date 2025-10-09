#!/bin/bash
# Demo startup script using test configuration

echo "🧪 Starting Demo Mode with Test Configuration..."
echo "============================================================"

# Activate virtual environment
source venv/bin/activate

# Create necessary directories
mkdir -p documents-testing output_documenty uploads summaries metadata logs data test_data

echo "🎯 Starting in Demo Mode:"
echo "  📄 Document Processing: Full functionality"
echo "  📊 Data Extraction: Test/Mock mode"
echo "  🌐 Web Interface: Available"
echo ""
echo "🌍 Access at: http://127.0.0.1:9090"
echo "⏹️  Press Ctrl+C to stop"
echo ""

# Run with test configuration to avoid credential issues
python integrated_app.py --config config.test.yaml --mode integrated --port 9090