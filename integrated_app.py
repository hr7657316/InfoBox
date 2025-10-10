#!/usr/bin/env python3
"""
Integrated Data Extraction Pipeline + InfoBox Document Processing System

This application combines:
1. Data extraction pipeline for WhatsApp and Email
2. InfoBox document processing with AI summarization
3. Unified web interface for both functionalities
"""

import os
import sys
import argparse
from pathlib import Path
from threading import Thread
import time

# Add the project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from pipeline.main import PipelineOrchestrator
from pipeline.utils.logger import PipelineLogger
from app_ui import app as infobox_app


class IntegratedApplication:
    """Integrated application combining pipeline and InfoBox functionality"""
    
    def __init__(self, config_path: str = "config.yaml"):
        self.config_path = config_path
        self.pipeline_orchestrator = None
        self.infobox_app = infobox_app
        self.logger = None
        
    def initialize(self):
        """Initialize both pipeline and InfoBox components"""
        print("🚀 Initializing Integrated Data Extraction + Document Processing System...")
        
        # Initialize pipeline orchestrator
        self.pipeline_orchestrator = PipelineOrchestrator(self.config_path)
        
        if not self.pipeline_orchestrator.initialize():
            print("❌ Pipeline initialization failed")
            return False
        
        self.logger = self.pipeline_orchestrator.logger
        print("✅ Pipeline initialized successfully")
        
        # Create necessary directories for InfoBox
        directories = [
            "documents-testing",
            "output_documenty", 
            "uploads",
            "summaries",
            "metadata"
        ]
        
        for directory in directories:
            os.makedirs(directory, exist_ok=True)
        
        print("✅ InfoBox directories created")
        print("✅ Integrated system initialized successfully")
        return True
    
    def run_pipeline_extraction(self, test_mode=False):
        """Run the data extraction pipeline"""
        if not self.pipeline_orchestrator:
            print("❌ Pipeline not initialized")
            return None
        
        print("🔄 Running data extraction pipeline...")
        
        if test_mode:
            # Run with mock data
            from run_pipeline import run_mock_extraction
            results = run_mock_extraction(self.pipeline_orchestrator)
        else:
            # Run actual extraction
            results = self.pipeline_orchestrator.run_extraction()
        
        return results
    
    def start_web_interface(self, host="127.0.0.1", port=9090):
        """Start the InfoBox web interface"""
        print(f"🌐 Starting web interface at http://{host}:{port}")
        self.infobox_app.run(host=host, port=port, debug=True, use_reloader=False)
    
    def run_integrated_mode(self, host="127.0.0.1", port=9090):
        """Run both pipeline and web interface in integrated mode"""
        if not self.initialize():
            return False
        
        print("🎯 Starting integrated mode...")
        print("=" * 60)
        print("📊 Data Extraction Pipeline: Ready")
        print("📄 Document Processing (InfoBox): Ready")
        print(f"🌐 Web Interface: http://{host}:{port}")
        print("=" * 60)
        
        # Start web interface
        self.start_web_interface(host, port)
        
        return True


def main():
    """Main entry point for the integrated application"""
    parser = argparse.ArgumentParser(description='Integrated Data Extraction + Document Processing System')
    parser.add_argument(
        '--config',
        default='config.yaml',
        help='Path to configuration file (default: config.yaml)'
    )
    parser.add_argument(
        '--mode',
        choices=['integrated', 'pipeline-only', 'infobox-only'],
        default='integrated',
        help='Application mode (default: integrated)'
    )
    parser.add_argument(
        '--host',
        default='127.0.0.1',
        help='Web interface host (default: 127.0.0.1)'
    )
    parser.add_argument(
        '--port',
        type=int,
        default=9090,
        help='Web interface port (default: 9090)'
    )
    parser.add_argument(
        '--test-pipeline',
        action='store_true',
        help='Run pipeline in test mode with mock data'
    )
    parser.add_argument(
        '--validate-only',
        action='store_true',
        help='Only validate configuration without running'
    )
    
    args = parser.parse_args()
    
    try:
        app = IntegratedApplication(args.config)
        
        if args.mode == 'integrated':
            # Run integrated mode with both pipeline and InfoBox
            print("🎯 Starting Integrated Mode")
            print("Features available:")
            print("  📊 Data Extraction Pipeline (WhatsApp + Email)")
            print("  📄 Document Processing with AI Summarization")
            print("  🌐 Unified Web Interface")
            print("  📧 Smart Email Assignment")
            print("  🤖 AI-Powered Analysis")
            
            if args.validate_only:
                if app.initialize():
                    print("✅ Configuration validation successful")
                    return 0
                else:
                    print("❌ Configuration validation failed")
                    return 1
            
            # Try to initialize, but fallback to InfoBox-only if pipeline fails
            try:
                return 0 if app.run_integrated_mode(args.host, args.port) else 1
            except Exception as e:
                print(f"⚠️  Pipeline initialization failed: {str(e)}")
                print("🔄 Falling back to InfoBox-only mode...")
                print("📄 Document Processing features will be available")
                print("📊 Data Extraction requires valid API credentials in config.yaml")
                
                # Create directories for InfoBox
                directories = ["documents-testing", "output_documenty", "uploads", "summaries", "metadata"]
                for directory in directories:
                    os.makedirs(directory, exist_ok=True)
                
                print(f"🌐 InfoBox web interface starting at http://{args.host}:{args.port}")
                app.start_web_interface(args.host, args.port)
                return 0
            
        elif args.mode == 'pipeline-only':
            # Run only the data extraction pipeline
            print("📊 Starting Pipeline-Only Mode")
            
            if not app.initialize():
                print("❌ Pipeline initialization failed")
                return 1
            
            if args.validate_only:
                print("✅ Pipeline configuration validation successful")
                return 0
            
            results = app.run_pipeline_extraction(args.test_pipeline)
            
            if results:
                successful = sum(1 for r in results.values() if r.success)
                total = len(results)
                print(f"📈 Pipeline completed: {successful}/{total} sources successful")
                return 0 if successful > 0 else 1
            else:
                print("❌ Pipeline execution failed")
                return 1
                
        elif args.mode == 'infobox-only':
            # Run only the InfoBox document processing
            print("📄 Starting InfoBox-Only Mode")
            
            # Create directories
            directories = ["documents-testing", "output_documenty", "uploads", "summaries", "metadata"]
            for directory in directories:
                os.makedirs(directory, exist_ok=True)
            
            print(f"🌐 InfoBox web interface starting at http://{args.host}:{args.port}")
            app.start_web_interface(args.host, args.port)
            return 0
        
    except KeyboardInterrupt:
        print("\n⏹️  Application interrupted by user")
        return 130
    except Exception as e:
        print(f"❌ Application failed: {str(e)}")
        return 1


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)