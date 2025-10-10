#!/usr/bin/env python3

import google.generativeai as genai
import os
import json
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class GeminiService:
    def __init__(self):
        """Initialize Gemini API"""
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key or api_key == "your_gemini_api_key_here":
            raise ValueError("Please set your GEMINI_API_KEY in the .env file")
        
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel('gemini-1.5-flash')
    
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
                    text_content.append(f"\n## {text}\n")
                elif element_type == 'Table':
                    text_content.append(f"\n**Table:**\n{text}\n")
                else:
                    text_content.append(text)
        
        return '\n'.join(text_content)
    
    def summarize_document(self, json_file_path, max_words=200):
        """Generate a summary of the document"""
        try:
            # Read the JSON file
            with open(json_file_path, 'r', encoding='utf-8') as f:
                json_data = json.load(f)
            
            # Extract text content
            full_text = self.extract_text_from_json(json_data)
            
            if not full_text.strip():
                return "No text content found to summarize."
            
            # Create summary prompt
            prompt = f"""
            Please provide a comprehensive summary of the following document in exactly {max_words} words or less. 
            Focus on the main points, key information, and important details:

            {full_text}

            Summary:
            """
            
            # Generate summary
            response = self.model.generate_content(prompt)
            return response.text.strip()
            
        except Exception as e:
            return f"Error generating summary: {str(e)}"
    
    def translate_to_malayalam(self, text):
        """Translate text to Malayalam"""
        try:
            prompt = f"""
            Please translate the following text to Malayalam language. 
            Maintain the meaning and context accurately:

            {text}

            Malayalam Translation:
            """
            
            response = self.model.generate_content(prompt)
            return response.text.strip()
            
        except Exception as e:
            return f"Error translating to Malayalam: {str(e)}"
    
    def summarize_and_translate_document(self, json_file_path, max_words=200):
        """Generate both summary and Malayalam translation"""
        try:
            # Get English summary
            summary = self.summarize_document(json_file_path, max_words)
            
            if summary.startswith("Error") or summary.startswith("No text"):
                return {
                    'summary': summary,
                    'malayalam_summary': "Translation not available",
                    'error': True
                }
            
            # Translate summary to Malayalam
            malayalam_summary = self.translate_to_malayalam(summary)
            
            return {
                'summary': summary,
                'malayalam_summary': malayalam_summary,
                'error': False
            }
            
        except Exception as e:
            return {
                'summary': f"Error: {str(e)}",
                'malayalam_summary': "Translation not available",
                'error': True
            }

def process_all_documents(input_dir="output_documenty", output_dir="summaries"):
    """Process all JSON files and create summaries"""
    
    # Create output directory
    os.makedirs(output_dir, exist_ok=True)
    
    if not os.path.exists(input_dir):
        print(f"Input directory {input_dir} does not exist")
        return False
    
    json_files = list(Path(input_dir).glob('*.json'))
    
    if not json_files:
        print(f"No JSON files found in {input_dir}")
        return False
    
    # Initialize Gemini service
    try:
        gemini = GeminiService()
    except ValueError as e:
        print(f"Error initializing Gemini: {e}")
        return False
    
    success_count = 0
    
    for json_file in json_files:
        print(f"Processing {json_file.name}...")
        
        # Generate summary and translation
        result = gemini.summarize_and_translate_document(str(json_file))
        
        if not result['error']:
            # Save results
            output_file = Path(output_dir) / f"{json_file.stem}_summary.json"
            
            summary_data = {
                'original_file': json_file.name,
                'timestamp': str(Path(json_file).stat().st_mtime),
                'summary': result['summary'],
                'malayalam_summary': result['malayalam_summary']
            }
            
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(summary_data, f, indent=2, ensure_ascii=False)
            
            print(f"✓ Summary saved to {output_file}")
            success_count += 1
        else:
            print(f"✗ Failed to process {json_file.name}: {result['summary']}")
    
    print(f"Successfully processed {success_count}/{len(json_files)} files")
    return success_count > 0

if __name__ == "__main__":
    process_all_documents()
