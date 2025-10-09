#!/usr/bin/env python3

import textwrap
import langextract as lx
import json
import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class MetadataExtractor:
    def __init__(self):
        """Initialize the metadata extractor with KMRL-specific prompt and examples"""
        
        # 1. Define a structured prompt for KMRL requirements
        self.prompt = textwrap.dedent("""\
        Extract structured metadata and classify the document.

        Fields to extract:
        - document_title
        - from_whom (author/originator)
        - to_whom (direct recipient)
        - for_whom (intended audience if implied)
        - date
        - time
        - deadline
        - entities (departments, people, contractors)
        - job_to_do (action or task)
        - document_categories (can be MULTIPLE: HR, Engineering, Operations, Safety, Finance, Procurement, Legal, General Notice)
        - intended_audiences (can be MULTIPLE: Engineer, HR, Railway Inspector, Contractor, Manager, Finance Officer, General Staff)

        Rules:
        - Use exact text from the document wherever possible.
        - For classification fields (categories & audiences), return a LIST (not single value).
        - Do not paraphrase or create extra text.
        """)

        # 2. Provide an example with MULTIPLE categories/audiences
        self.examples = [
            lx.data.ExampleData(
                text=(
                    "Subject: New Safety & HR Guidelines for Contractors\n"
                    "From: HR & Safety Divisions, KMRL\n"
                    "To: All Contractors, HR Managers, Safety Inspectors\n"
                    "Date: 21 Sept 2025\n"
                    "Contractors must complete safety refresher training and submit compliance reports by 30 Sept 2025."
                ),
                extractions=[
                    lx.data.Extraction(
                        extraction_class="document_metadata",
                        extraction_text="New Safety & HR Guidelines for Contractors",
                        attributes={
                            "document_title": "New Safety & HR Guidelines for Contractors",
                            "from_whom": "HR & Safety Divisions, KMRL",
                            "to_whom": "All Contractors, HR Managers, Safety Inspectors",
                            "for_whom": "Contractors, HR, Safety Inspectors",
                            "date": "21 Sept 2025",
                            "deadline": "30 Sept 2025",
                            "job_to_do": "Complete safety refresher training and submit compliance reports",
                            "entities": ["HR Division", "Safety Division", "Contractors", "HR Managers", "Safety Inspectors"],
                            "document_categories": ["HR", "Safety"],
                            "intended_audiences": ["Contractor", "HR", "Railway Inspector"]
                        }
                    )
                ]
            )
        ]

    def extract_text_from_json(self, json_data):
        """Extract readable text from Unstructured JSON data"""
        if isinstance(json_data, str):
            json_data = json.loads(json_data)
        
        text_content = []
        
        for element in json_data:
            element_type = element.get('type', '')
            text = element.get('text', '').strip()
            
            if text:
                if element_type in ['Title', 'Header']:
                    text_content.append(f"Subject: {text}")
                elif element_type == 'Table':
                    text_content.append(f"Table: {text}")
                else:
                    text_content.append(text)
        
        return '\n'.join(text_content)

    def extract_metadata_from_json_file(self, json_file_path):
        """Extract metadata from a processed JSON file"""
        try:
            # Read the JSON file
            with open(json_file_path, 'r', encoding='utf-8') as f:
                json_data = json.load(f)
            
            # Extract text content
            full_text = self.extract_text_from_json(json_data)
            
            if not full_text.strip():
                return {
                    'error': True,
                    'message': "No text content found to extract metadata from."
                }
            
            # Run extraction using langextract
            result = lx.extract(
                text_or_documents=full_text,
                prompt_description=self.prompt,
                examples=self.examples,
                model_id="gemini-1.5-flash"
            )
            
            # Parse the result - LangExtract returns an AnnotatedDocument
            if result and hasattr(result, 'extractions') and result.extractions:
                extracted_data = result.extractions[0]  # Get first extraction
                
                # Clean up the metadata
                metadata = {
                    'document_title': extracted_data.attributes.get('document_title', ''),
                    'from_whom': extracted_data.attributes.get('from_whom', ''),
                    'to_whom': extracted_data.attributes.get('to_whom', ''),
                    'for_whom': extracted_data.attributes.get('for_whom', ''),
                    'date': extracted_data.attributes.get('date', ''),
                    'time': extracted_data.attributes.get('time', ''),
                    'deadline': extracted_data.attributes.get('deadline', ''),
                    'entities': extracted_data.attributes.get('entities', []),
                    'job_to_do': extracted_data.attributes.get('job_to_do', ''),
                    'document_categories': extracted_data.attributes.get('document_categories', []),
                    'intended_audiences': extracted_data.attributes.get('intended_audiences', [])
                }
                
                return {
                    'error': False,
                    'metadata': metadata,
                    'extraction_text': extracted_data.extraction_text
                }
            else:
                return {
                    'error': True,
                    'message': "No metadata could be extracted from the document."
                }
                
        except Exception as e:
            return {
                'error': True,
                'message': f"Error extracting metadata: {str(e)}"
            }

    def process_all_documents(self, input_dir="output_documenty", output_dir="metadata"):
        """Process all JSON files and extract metadata"""
        
        # Create output directory
        os.makedirs(output_dir, exist_ok=True)
        
        if not os.path.exists(input_dir):
            print(f"Input directory {input_dir} does not exist")
            return False
        
        json_files = list(Path(input_dir).glob('*.json'))
        
        if not json_files:
            print(f"No JSON files found in {input_dir}")
            return False
        
        success_count = 0
        
        for json_file in json_files:
            print(f"Processing {json_file.name}...")
            
            # Extract metadata
            result = self.extract_metadata_from_json_file(str(json_file))
            
            if not result['error']:
                # Save metadata
                output_file = Path(output_dir) / f"{json_file.stem}_metadata.json"
                
                metadata_data = {
                    'original_file': json_file.name,
                    'timestamp': str(Path(json_file).stat().st_mtime),
                    'extraction_text': result['extraction_text'],
                    'metadata': result['metadata']
                }
                
                with open(output_file, 'w', encoding='utf-8') as f:
                    json.dump(metadata_data, f, indent=2, ensure_ascii=False)
                
                print(f"✓ Metadata saved to {output_file}")
                success_count += 1
            else:
                print(f"✗ Failed to process {json_file.name}: {result['message']}")
        
        print(f"Successfully processed {success_count}/{len(json_files)} files")
        return success_count > 0

if __name__ == "__main__":
    extractor = MetadataExtractor()
    extractor.process_all_documents()
