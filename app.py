#!/usr/bin/env python3

import os
import json
from pathlib import Path
from dotenv import load_dotenv
import requests

# Load environment variables
load_dotenv()

# Configuration
INPUT_FOLDER = 'documents-testing'
OUTPUT_FOLDER = 'output_documenty'

# Allowed file extensions
ALLOWED_EXTENSIONS = {'pdf', 'png', 'jpg', 'jpeg', 'gif', 'tiff', 'bmp', 'doc', 'docx', 'txt'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def process_documents():
    """Process documents from input folder using Unstructured API"""
    print("🚀 Starting document processing...")
    
    # Get API key from environment
    api_key = os.getenv("UNSTRUCTURED_API_KEY")
    if not api_key:
        print("❌ Error: UNSTRUCTURED_API_KEY not found in environment")
        return False
    
    # Check input directory
    input_dir = Path(INPUT_FOLDER)
    if not input_dir.exists():
        print(f"❌ Error: Input directory '{INPUT_FOLDER}' does not exist")
        return False
        
    files_to_process = [f for f in input_dir.glob('*') if f.is_file() and allowed_file(f.name)]
    
    if not files_to_process:
        print(f"❌ No valid files to process in '{INPUT_FOLDER}'")
        return False
    
    print(f"📁 Found {len(files_to_process)} files to process")
    
    processed_count = 0
    errors = []
    
    # API endpoint and headers
    url = "https://api.unstructuredapp.io/general/v0/general"
    headers = {"unstructured-api-key": api_key}
    data = {"strategy": "auto", "languages": ["eng"]}
    
    # Create output directory
    output_dir = Path(OUTPUT_FOLDER)
    output_dir.mkdir(exist_ok=True)
    
    # Process each file
    for file_path in files_to_process:
        try:
            print(f"📄 Processing: {file_path.name}")
            with open(file_path, "rb") as f:
                files = {"files": f}
                response = requests.post(url, headers=headers, data=data, files=files, timeout=60)
            
            if response.status_code == 200:
                # Save JSON result
                output_file = output_dir / f"{file_path.stem}.json"
                
                with open(output_file, 'w') as f:
                    json.dump(response.json(), f, indent=2)
                
                print(f"✅ Saved: {output_file}")
                processed_count += 1
            else:
                error_msg = f"{file_path.name}: API returned {response.status_code}"
                print(f"❌ {error_msg}")
                errors.append(error_msg)
                
        except Exception as e:
            error_msg = f"{file_path.name}: {str(e)}"
            print(f"❌ {error_msg}")
            errors.append(error_msg)
    
    # Summary
    print(f"\n📊 Processing Summary:")
    print(f"✅ Successfully processed: {processed_count} files")
    if errors:
        print(f"❌ Errors: {len(errors)}")
        for error in errors:
            print(f"   - {error}")
    
    return processed_count > 0

if __name__ == '__main__':
    # Create necessary directories
    os.makedirs(INPUT_FOLDER, exist_ok=True)
    os.makedirs(OUTPUT_FOLDER, exist_ok=True)
    
    print("📁 Document Processing Script")
    print(f"📂 Input folder: {INPUT_FOLDER}")
    print(f"📂 Output folder: {OUTPUT_FOLDER}")
    print(f"🔑 API Key configured: {bool(os.getenv('UNSTRUCTURED_API_KEY'))}")
    print("-" * 50)
    
    success = process_documents()
    
    if success:
        print("\n🎉 Processing completed successfully!")
    else:
        print("\n💥 Processing failed!")
        exit(1)
