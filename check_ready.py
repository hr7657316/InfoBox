#!/usr/bin/env python3
"""
Quick readiness check for the integrated system
"""

import sys
import os
from pathlib import Path

def check_dependencies():
    """Check if all required dependencies are installed"""
    print("🔍 Checking dependencies...")
    
    required_modules = [
        'flask',
        'requests', 
        'google.generativeai',
        'langextract',
        'werkzeug',
        'dotenv'
    ]
    
    missing = []
    for module in required_modules:
        try:
            __import__(module)
            print(f"  ✅ {module}")
        except ImportError:
            print(f"  ❌ {module}")
            missing.append(module)
    
    return len(missing) == 0

def check_directories():
    """Check if all required directories exist"""
    print("\n📁 Checking directories...")
    
    required_dirs = [
        'documents-testing',
        'output_documenty', 
        'uploads',
        'summaries',
        'metadata',
        'templates',
        'pipeline'
    ]
    
    missing = []
    for directory in required_dirs:
        if Path(directory).exists():
            print(f"  ✅ {directory}/")
        else:
            print(f"  ❌ {directory}/")
            missing.append(directory)
    
    return len(missing) == 0

def check_files():
    """Check if all required files exist"""
    print("\n📄 Checking key files...")
    
    required_files = [
        'integrated_app.py',
        'app_ui.py',
        'gemini_service.py',
        'metadata_extractor.py',
        'email_service.py',
        'templates/index.html',
        'config.yaml',
        'requirements.txt'
    ]
    
    missing = []
    for file_path in required_files:
        if Path(file_path).exists():
            print(f"  ✅ {file_path}")
        else:
            print(f"  ❌ {file_path}")
            missing.append(file_path)
    
    return len(missing) == 0

def main():
    """Run all readiness checks"""
    print("🚀 Integrated System Readiness Check")
    print("=" * 50)
    
    checks = [
        ("Dependencies", check_dependencies),
        ("Directories", check_directories), 
        ("Files", check_files)
    ]
    
    all_passed = True
    
    for check_name, check_func in checks:
        if not check_func():
            all_passed = False
    
    print("\n" + "=" * 50)
    
    if all_passed:
        print("✅ System is ready!")
        print("\n🚀 To start the server:")
        print("  ./start_server.sh")
        print("  OR")
        print("  source venv/bin/activate && python integrated_app.py --mode integrated --port 9090")
        print("\n🌍 Then open: http://127.0.0.1:9090")
        return True
    else:
        print("❌ System is not ready. Please fix the issues above.")
        print("\n🔧 To fix missing dependencies:")
        print("  pip install -r requirements.txt")
        print("\n📁 To create missing directories:")
        print("  mkdir -p documents-testing output_documenty uploads summaries metadata")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)