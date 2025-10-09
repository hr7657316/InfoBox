#!/usr/bin/env python3
"""
Entry point script for the data extraction pipeline

This script provides a command-line interface to run the extraction pipeline
with proper module imports and error handling.
"""

import sys
import os
import argparse
from pathlib import Path

# Add the project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from pipeline.main import PipelineOrchestrator
from pipeline.utils.logger import PipelineLogger
from pipeline.utils.test_data_generator import TestDataGenerator
from pipeline.models import ExtractionResult


def run_mock_extraction(orchestrator):
    """Run extraction with mock data for testing purposes"""
    import time
    from datetime import datetime
    
    # Generate test data
    test_generator = TestDataGenerator()
    test_data = test_generator.generate_extraction_result_data()
    
    # Simulate extraction time
    start_time = datetime.now()
    time.sleep(1)  # Simulate processing time
    
    results = {}
    
    # Create mock WhatsApp result
    whatsapp_messages = test_data['whatsapp_messages']
    media_count = sum(1 for msg in whatsapp_messages if msg.media_url)
    
    # Save test data using storage manager
    try:
        whatsapp_output_paths = orchestrator.storage_manager.save_whatsapp_data(whatsapp_messages)
        whatsapp_success = True
        whatsapp_errors = []
    except Exception as e:
        whatsapp_output_paths = {}
        whatsapp_success = False
        whatsapp_errors = [f"Failed to save WhatsApp test data: {str(e)}"]
    
    results['whatsapp'] = ExtractionResult(
        source='whatsapp',
        success=whatsapp_success,
        messages_count=len(whatsapp_messages),
        media_count=media_count,
        errors=whatsapp_errors,
        execution_time=1.2,
        output_paths=whatsapp_output_paths
    )
    
    # Create mock Email result
    emails = test_data['emails']
    attachment_count = sum(len(email.attachments) for email in emails)
    
    try:
        email_output_paths = orchestrator.storage_manager.save_email_data(emails)
        email_success = True
        email_errors = []
    except Exception as e:
        email_output_paths = {}
        email_success = False
        email_errors = [f"Failed to save email test data: {str(e)}"]
    
    results['email'] = ExtractionResult(
        source='email',
        success=email_success,
        messages_count=len(emails),
        media_count=attachment_count,
        errors=email_errors,
        execution_time=0.8,
        output_paths=email_output_paths
    )
    
    # Log the mock extraction
    total_time = (datetime.now() - start_time).total_seconds()
    orchestrator.logger.log_info(
        f"Mock extraction completed: {len([r for r in results.values() if r.success])}/{len(results)} sources successful",
        "orchestrator",
        execution_time=total_time,
        test_mode=True
    )
    
    return results


def main():
    """Main entry point for the pipeline"""
    parser = argparse.ArgumentParser(description='Data Extraction Pipeline')
    parser.add_argument(
        '--config', 
        default='config.yaml',
        help='Path to configuration file (default: config.yaml)'
    )
    parser.add_argument(
        '--test-mode',
        action='store_true',
        help='Run in test mode with mock data generation'
    )
    parser.add_argument(
        '--mock-mode',
        action='store_true',
        help='Run with mock data instead of real API calls'
    )
    parser.add_argument(
        '--validate-only',
        action='store_true',
        help='Only validate configuration without running extraction'
    )
    
    args = parser.parse_args()
    
    try:
        # Initialize the pipeline orchestrator
        orchestrator = PipelineOrchestrator(args.config)
        
        # Initialize the pipeline
        if not orchestrator.initialize():
            print("❌ Pipeline initialization failed. Check logs for details.")
            return 1
        
        print("✅ Pipeline initialized successfully")
        
        # If validate-only mode, just check configuration and exit
        if args.validate_only:
            print("✅ Configuration validation completed successfully")
            return 0
        
        # Run the extraction
        if args.test_mode or args.mock_mode:
            print("🧪 Running in test mode with mock data...")
            results = run_mock_extraction(orchestrator)
        else:
            print("🚀 Starting data extraction...")
            results = orchestrator.run_extraction()
        
        # Print results summary
        print("\n📊 Extraction Results:")
        print("=" * 50)
        
        total_messages = 0
        total_media = 0
        successful_sources = 0
        
        for source, result in results.items():
            status = "✅ SUCCESS" if result.success else "❌ FAILED"
            print(f"{source.upper()}: {status}")
            print(f"  Messages: {result.messages_count}")
            print(f"  Media: {result.media_count}")
            print(f"  Execution time: {result.execution_time:.2f}s")
            
            if result.errors:
                print(f"  Errors: {len(result.errors)}")
                for error in result.errors[:3]:  # Show first 3 errors
                    print(f"    - {error}")
                if len(result.errors) > 3:
                    print(f"    ... and {len(result.errors) - 3} more errors")
            
            if result.output_paths:
                print(f"  Output files:")
                for file_type, path in result.output_paths.items():
                    print(f"    {file_type}: {path}")
            
            print()
            
            total_messages += result.messages_count
            total_media += result.media_count
            if result.success:
                successful_sources += 1
        
        print(f"📈 Summary: {successful_sources}/{len(results)} sources successful")
        print(f"📝 Total messages extracted: {total_messages}")
        print(f"📎 Total media files: {total_media}")
        
        # Return appropriate exit code
        return 0 if successful_sources == len(results) else 1
        
    except KeyboardInterrupt:
        print("\n⏹️  Pipeline execution interrupted by user")
        return 130
    except Exception as e:
        print(f"❌ Pipeline execution failed: {str(e)}")
        return 1


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)