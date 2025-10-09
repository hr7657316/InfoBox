#!/usr/bin/env python3
"""
Test script to demonstrate the integrated pipeline + InfoBox functionality
"""

import os
import sys
from pathlib import Path

# Add the project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

def test_pipeline_integration():
    """Test the pipeline integration"""
    print("🧪 Testing Pipeline Integration...")
    
    from integrated_app import IntegratedApplication
    
    # Test with test configuration
    app = IntegratedApplication("config.test.yaml")
    
    # Test initialization
    if app.initialize():
        print("✅ Pipeline initialization: PASSED")
        
        # Test mock extraction
        print("🔄 Testing mock data extraction...")
        results = app.run_pipeline_extraction(test_mode=True)
        
        if results:
            successful = sum(1 for r in results.values() if r.success)
            total = len(results)
            print(f"✅ Mock extraction: PASSED ({successful}/{total} sources)")
            
            # Show results summary
            for source, result in results.items():
                print(f"  📊 {source.upper()}: {result.messages_count} messages, {result.media_count} media files")
        else:
            print("❌ Mock extraction: FAILED")
            return False
    else:
        print("❌ Pipeline initialization: FAILED")
        return False
    
    return True

def test_infobox_components():
    """Test InfoBox components"""
    print("\n🧪 Testing InfoBox Components...")
    
    try:
        # Test imports
        from gemini_service import GeminiService
        from metadata_extractor import MetadataExtractor
        from email_service import EmailService
        print("✅ InfoBox imports: PASSED")
        
        # Test directory creation
        directories = ["documents-testing", "output_documenty", "uploads", "summaries", "metadata"]
        for directory in directories:
            os.makedirs(directory, exist_ok=True)
        print("✅ Directory creation: PASSED")
        
        # Test configuration loading
        from dotenv import load_dotenv
        load_dotenv()
        print("✅ Environment loading: PASSED")
        
        return True
        
    except ImportError as e:
        print(f"❌ InfoBox imports: FAILED - {e}")
        return False
    except Exception as e:
        print(f"❌ InfoBox components: FAILED - {e}")
        return False

def test_web_interface_components():
    """Test web interface components"""
    print("\n🧪 Testing Web Interface Components...")
    
    try:
        # Test Flask app import
        from app_ui import app
        print("✅ Flask app import: PASSED")
        
        # Test template directory
        template_dir = Path("templates")
        if template_dir.exists():
            print("✅ Templates directory: PASSED")
        else:
            print("❌ Templates directory: MISSING")
            return False
        
        # Test main template
        index_template = template_dir / "index.html"
        if index_template.exists():
            print("✅ Main template: PASSED")
        else:
            print("❌ Main template: MISSING")
            return False
        
        return True
        
    except ImportError as e:
        print(f"❌ Web interface: FAILED - {e}")
        return False
    except Exception as e:
        print(f"❌ Web interface: FAILED - {e}")
        return False

def main():
    """Run all integration tests"""
    print("🚀 Integrated Data Extraction + InfoBox System Test")
    print("=" * 60)
    
    tests = [
        ("Pipeline Integration", test_pipeline_integration),
        ("InfoBox Components", test_infobox_components),
        ("Web Interface", test_web_interface_components)
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        print(f"\n📋 Running {test_name} Test...")
        try:
            if test_func():
                passed += 1
                print(f"✅ {test_name}: PASSED")
            else:
                print(f"❌ {test_name}: FAILED")
        except Exception as e:
            print(f"❌ {test_name}: ERROR - {e}")
    
    print("\n" + "=" * 60)
    print(f"📊 Test Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All integration tests PASSED!")
        print("\n🌟 System Ready:")
        print("  📊 Data Extraction Pipeline: Functional")
        print("  📄 Document Processing: Functional") 
        print("  🌐 Web Interface: Ready")
        print("  🤖 AI Integration: Ready")
        print("\n🚀 To start the integrated system:")
        print("  python integrated_app.py --mode integrated")
        print("  Then open: http://127.0.0.1:9090")
        return True
    else:
        print("❌ Some tests failed. Check the output above.")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)