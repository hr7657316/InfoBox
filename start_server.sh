#!/bin/bash
# Startup script for the Integrated Data Extraction + InfoBox System

echo "🚀 Starting Integrated Data Extraction + InfoBox System..."
echo "============================================================"

# Activate virtual environment
echo "📦 Activating virtual environment..."
source venv/bin/activate

# Check if dependencies are installed
echo "🔍 Checking dependencies..."
python -c "import flask, requests, google.generativeai" 2>/dev/null
if [ $? -ne 0 ]; then
    echo "❌ Dependencies missing. Installing..."
    pip install -r requirements.txt
fi

# Create necessary directories
echo "📁 Creating directories..."
mkdir -p documents-testing output_documenty uploads summaries metadata logs data

# Start the integrated application
echo "🌐 Starting web server on port 9090..."
echo "📄 Document Processing: Available"
echo "📊 Data Extraction: Available"
echo "🤖 AI Integration: Ready"
echo ""
echo "🌍 Access the web interface at: http://127.0.0.1:9090"
echo "⏹️  Press Ctrl+C to stop the server"
echo ""

# Run the integrated application
python integrated_app.py --mode integrated --port 9090