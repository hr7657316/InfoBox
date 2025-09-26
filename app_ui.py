from flask import Flask, render_template, request, jsonify, send_file, Response
from flask_cors import CORS
import os
import json
from pathlib import Path
from werkzeug.utils import secure_filename
from dotenv import load_dotenv
import requests
from datetime import datetime
from gemini_service import GeminiService
from metadata_extractor import MetadataExtractor
from email_service import EmailService
from rag_system import RAGSystem

# Load environment variables
load_dotenv()

app = Flask(__name__)
CORS(app)

# Configuration
app.config['INPUT_FOLDER'] = 'documents-testing'
app.config['OUTPUT_FOLDER'] = 'output_documenty'
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['SUMMARY_FOLDER'] = 'summaries'
app.config['METADATA_FOLDER'] = 'metadata'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size

# Allowed file extensions
ALLOWED_EXTENSIONS = {'pdf', 'png', 'jpg', 'jpeg', 'gif', 'tiff', 'bmp', 'doc', 'docx', 'txt'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/')
def index():
    """Main UI"""
    return render_template('index.html')

@app.route('/upload', methods=['POST'])
def upload_files():
    """Handle file uploads"""
    if 'files' not in request.files:
        return jsonify({'error': 'No files selected'}), 400
    
    files = request.files.getlist('files')
    uploaded_files = []
    
    # Create directories
    os.makedirs(app.config['INPUT_FOLDER'], exist_ok=True)
    
    for file in files:
        if file and file.filename and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            filepath = os.path.join(app.config['INPUT_FOLDER'], filename)
            file.save(filepath)
            uploaded_files.append(filename)
    
    # Store newly uploaded files in session or temporary storage
    import json
    temp_file = Path(app.config['INPUT_FOLDER']) / '.pending_files.json'
    with open(temp_file, 'w') as f:
        json.dump(uploaded_files, f)
    
    return jsonify({
        'success': True,
        'uploaded_files': uploaded_files,
        'message': f'Successfully uploaded {len(uploaded_files)} files'
    })

@app.route('/process', methods=['POST'])
def process_documents():
    """Process ONLY newly uploaded documents using Unstructured API"""
    try:
        # Get API key from environment
        api_key = os.getenv("UNSTRUCTURED_API_KEY")
        if not api_key:
            return jsonify({'success': False, 'error': 'API key not found'}), 500
        
        # Get files from input directory
        input_dir = Path(app.config['INPUT_FOLDER'])
        if not input_dir.exists():
            return jsonify({'success': False, 'error': 'No files to process'}), 400
        
        # Check for pending files (newly uploaded ones)
        temp_file = input_dir / '.pending_files.json'
        if temp_file.exists():
            with open(temp_file, 'r') as f:
                pending_files = json.load(f)
            
            # Filter to only process these specific files
            files_to_process = []
            for filename in pending_files:
                file_path = input_dir / filename
                if file_path.exists() and allowed_file(filename):
                    files_to_process.append(file_path)
            
            # Clear the pending files after reading
            temp_file.unlink()
        else:
            # If no pending file exists (manual trigger), check what's NOT already processed
            output_dir = Path(app.config['OUTPUT_FOLDER'])
            output_dir.mkdir(exist_ok=True)
            
            # Get list of already processed files
            processed_files = set(f.stem for f in output_dir.glob('*.json'))
            
            # Only process files that haven't been processed yet
            all_input_files = [f for f in input_dir.glob('*') if f.is_file() and allowed_file(f.name)]
            files_to_process = [f for f in all_input_files if f.stem not in processed_files]
        
        if not files_to_process:
            return jsonify({'success': False, 'error': 'No valid files to process'}), 400
        
        processed_count = 0
        errors = []
        
        # API endpoint and headers
        url = "https://api.unstructuredapp.io/general/v0/general"
        headers = {"unstructured-api-key": api_key}
        data = {"strategy": "auto", "languages": ["eng"]}
        
        # Create output directory
        output_dir = Path(app.config['OUTPUT_FOLDER'])
        output_dir.mkdir(exist_ok=True)
        
        # Process each file
        for file_path in files_to_process:
            try:
                with open(file_path, "rb") as f:
                    files = {"files": f}
                    response = requests.post(url, headers=headers, data=data, files=files, timeout=60)
                
                if response.status_code == 200:
                    # Save JSON result
                    output_file = output_dir / f"{file_path.stem}.json"
                    
                    with open(output_file, 'w') as f:
                        json.dump(response.json(), f, indent=2)
                    
                    processed_count += 1
                else:
                    errors.append(f"{file_path.name}: API returned {response.status_code}")
                    
            except Exception as e:
                errors.append(f"{file_path.name}: {str(e)}")
        
        if processed_count == 0:
            return jsonify({
                'success': False,
                'error': 'Failed to process any documents',
                'details': errors
            }), 500
        
        # Step 2 & 3: Generate metadata and summaries with optimized single API call
        import google.generativeai as genai
        import time
        
        summary_dir = Path(app.config['SUMMARY_FOLDER'])
        metadata_dir = Path(app.config['METADATA_FOLDER'])
        summary_dir.mkdir(exist_ok=True)
        metadata_dir.mkdir(exist_ok=True)
        
        summary_results = {'success': True, 'count': 0, 'errors': []}
        metadata_results = {'success': True, 'count': 0, 'errors': []}
        
        # Configure Gemini API
        api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
        if api_key:
            genai.configure(api_key=api_key)
            
            # Try to find a working model
            model = None
            models_to_try = ['gemini-pro-latest', 'gemini-pro', 'gemini-1.5-flash']
            for model_name in models_to_try:
                try:
                    test_model = genai.GenerativeModel(model_name)
                    test_model.generate_content("test")
                    model = test_model
                    print(f"✅ Using {model_name} for metadata and summaries")
                    break
                except:
                    continue
            
            if model:
                # Only process the newly created JSON files
                newly_processed_files = []
                for file_path in files_to_process:
                    json_output = output_dir / f"{file_path.stem}.json"
                    if json_output.exists():
                        newly_processed_files.append(json_output)
                
                for i, json_file in enumerate(newly_processed_files):
                    if i > 0:
                        time.sleep(15)  # Wait between API calls to avoid rate limits
                    
                    try:
                        # Read and extract text from processed document
                        with open(json_file, 'r', encoding='utf-8') as f:
                            json_data = json.load(f)
                        
                        text_parts = []
                        for element in json_data:
                            text = element.get('text', '').strip()
                            if text:
                                text_parts.append(text)
                        
                        document_text = ' '.join(text_parts)
                        
                        if document_text:
                            # Single API call for both metadata and summary
                            prompt = '''
                            Analyze this KMRL document and return ONLY a JSON object with metadata and summary.
                            
                            Return this exact JSON structure:
                            {
                              "metadata": {
                                "document_title": "title",
                                "from_whom": "sender",
                                "to_whom": "recipient", 
                                "for_whom": "audience",
                                "date": "date",
                                "time": "time",
                                "deadline": "deadline",
                                "entities": ["list of entities"],
                                "job_to_do": "action required",
                                "document_categories": ["categories"],
                                "intended_audiences": ["audiences"]
                              },
                              "summary": {
                                "english": "English summary",
                                "malayalam": "Malayalam summary",
                                "key_points": ["point1", "point2"]
                              }
                            }
                            
                            Document to analyze:\n''' + document_text[:3000]
                            
                            response = model.generate_content(prompt)
                            response_text = response.text.strip()
                            
                            # Clean response
                            if response_text.startswith('```json'):
                                response_text = response_text.replace('```json', '').replace('```', '').strip()
                            
                            result = json.loads(response_text)
                            
                            # Save metadata
                            if 'metadata' in result:
                                metadata_file = metadata_dir / f"{json_file.stem}_metadata.json"
                                metadata_data = {
                                    'original_file': json_file.name,
                                    'timestamp': str(json_file.stat().st_mtime),
                                    'extraction_text': document_text[:500],
                                    'metadata': result['metadata']
                                }
                                with open(metadata_file, 'w', encoding='utf-8') as f:
                                    json.dump(metadata_data, f, indent=2, ensure_ascii=False)
                                metadata_results['count'] += 1
                            
                            # Save summary
                            if 'summary' in result:
                                summary_file = summary_dir / f"{json_file.stem}_summary.json"
                                summary_data = {
                                    'original_file': json_file.name,
                                    'timestamp': str(json_file.stat().st_mtime),
                                    'summary': result['summary'].get('english', ''),
                                    'malayalam_summary': result['summary'].get('malayalam', ''),
                                    'key_points': result['summary'].get('key_points', [])
                                }
                                with open(summary_file, 'w', encoding='utf-8') as f:
                                    json.dump(summary_data, f, indent=2, ensure_ascii=False)
                                summary_results['count'] += 1
                                
                            print(f"✅ Generated metadata and summary for {json_file.name}")
                            
                    except Exception as e:
                        error_msg = f"{json_file.name}: {str(e)[:100]}"
                        metadata_results['errors'].append(error_msg)
                        summary_results['errors'].append(error_msg)
                        print(f"❌ Failed {json_file.name}: {str(e)[:100]}")
            else:
                metadata_results['errors'].append("No working Gemini model found")
                summary_results['errors'].append("No working Gemini model found")
        else:
            metadata_results['errors'].append("No API key configured")
            summary_results['errors'].append("No API key configured")
        
        # Return comprehensive results
        return jsonify({
            'success': True,
            'message': f'Successfully processed {processed_count} documents with automated pipeline',
            'processing': {
                'documents_processed': processed_count,
                'errors': errors if errors else None
            },
            'summaries': {
                'generated': summary_results['count'],
                'success': summary_results['success'],
                'errors': summary_results['errors'] if summary_results['errors'] else None
            },
            'metadata': {
                'generated': metadata_results['count'],
                'success': metadata_results['success'],
                'errors': metadata_results['errors'] if metadata_results['errors'] else None
            }
        })
            
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/generate-summaries', methods=['POST'])
def generate_summaries():
    """Generate summaries for all processed documents using Gemini API"""
    try:
        # Initialize Gemini service
        gemini = GeminiService()
        
        # Get all JSON files from output directory
        output_dir = Path(app.config['OUTPUT_FOLDER'])
        if not output_dir.exists():
            return jsonify({'success': False, 'error': 'No processed documents found'}), 400
            
        json_files = list(output_dir.glob('*.json'))
        if not json_files:
            return jsonify({'success': False, 'error': 'No processed documents found'}), 400
        
        # Create summaries directory
        summary_dir = Path(app.config['SUMMARY_FOLDER'])
        summary_dir.mkdir(exist_ok=True)
        
        success_count = 0
        errors = []
        
        for json_file in json_files:
            try:
                # Generate summary and translation
                result = gemini.summarize_and_translate_document(str(json_file))
                
                if not result['error']:
                    # Save summary
                    output_file = summary_dir / f"{json_file.stem}_summary.json"
                    summary_data = {
                        'original_file': json_file.name,
                        'timestamp': str(json_file.stat().st_mtime),
                        'summary': result['summary'],
                        'malayalam_summary': result['malayalam_summary']
                    }
                    
                    with open(output_file, 'w', encoding='utf-8') as f:
                        json.dump(summary_data, f, indent=2, ensure_ascii=False)
                    
                    success_count += 1
                else:
                    errors.append(f"{json_file.name}: {result['summary']}")
                    
            except Exception as e:
                errors.append(f"{json_file.name}: {str(e)}")
        
        if success_count > 0:
            return jsonify({
                'success': True,
                'message': f'Successfully generated summaries for {success_count} documents',
                'summaries_generated': success_count,
                'errors': errors if errors else None
            })
        else:
            return jsonify({
                'success': False,
                'error': 'Failed to generate any summaries',
                'details': errors
            }), 500
            
    except ValueError as e:
        return jsonify({'success': False, 'error': str(e)}), 500
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/get-summary/<filename>')
def get_summary(filename):
    """Get summary for a specific document"""
    summary_dir = Path(app.config['SUMMARY_FOLDER'])
    
    # Try to find summary file (with or without _summary suffix)
    summary_file = summary_dir / f"{filename.replace('.json', '')}_summary.json"
    
    if summary_file.exists():
        try:
            with open(summary_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                return jsonify({
                    'success': True,
                    'filename': filename,
                    'summary': data['summary'],
                    'malayalam_summary': data['malayalam_summary'],
                    'timestamp': data['timestamp']
                })
        except Exception as e:
            return jsonify({'success': False, 'error': str(e)}), 500
    else:
        return jsonify({'success': False, 'error': 'Summary not found. Generate summaries first.'}), 404

@app.route('/generate-metadata', methods=['POST'])
def generate_metadata():
    """Generate metadata for all processed documents using langextract"""
    try:
        # Initialize metadata extractor
        extractor = MetadataExtractor()
        
        # Get all JSON files from output directory
        output_dir = Path(app.config['OUTPUT_FOLDER'])
        if not output_dir.exists():
            return jsonify({'success': False, 'error': 'No processed documents found'}), 400
            
        json_files = list(output_dir.glob('*.json'))
        if not json_files:
            return jsonify({'success': False, 'error': 'No processed documents found'}), 400
        
        # Create metadata directory
        metadata_dir = Path(app.config['METADATA_FOLDER'])
        metadata_dir.mkdir(exist_ok=True)
        
        success_count = 0
        errors = []
        
        for json_file in json_files:
            try:
                # Extract metadata
                result = extractor.extract_metadata_from_json_file(str(json_file))
                
                if not result['error']:
                    # Save metadata
                    output_file = metadata_dir / f"{json_file.stem}_metadata.json"
                    metadata_data = {
                        'original_file': json_file.name,
                        'timestamp': str(json_file.stat().st_mtime),
                        'extraction_text': result['extraction_text'],
                        'metadata': result['metadata']
                    }
                    
                    with open(output_file, 'w', encoding='utf-8') as f:
                        json.dump(metadata_data, f, indent=2, ensure_ascii=False)
                    
                    success_count += 1
                else:
                    errors.append(f"{json_file.name}: {result['message']}")
                    
            except Exception as e:
                errors.append(f"{json_file.name}: {str(e)}")
        
        if success_count > 0:
            return jsonify({
                'success': True,
                'message': f'Successfully generated metadata for {success_count} documents',
                'metadata_generated': success_count,
                'errors': errors if errors else None
            })
        else:
            return jsonify({
                'success': False,
                'error': 'Failed to generate any metadata',
                'details': errors
            }), 500
            
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/get-metadata/<filename>')
def get_metadata(filename):
    """Get metadata for a specific document"""
    metadata_dir = Path(app.config['METADATA_FOLDER'])
    
    # Try to find metadata file (with or without _metadata suffix)
    metadata_file = metadata_dir / f"{filename.replace('.json', '')}_metadata.json"
    
    if metadata_file.exists():
        try:
            with open(metadata_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                return jsonify({
                    'success': True,
                    'filename': filename,
                    'metadata': data['metadata'],
                    'extraction_text': data['extraction_text'],
                    'timestamp': data['timestamp']
                })
        except Exception as e:
            return jsonify({'success': False, 'error': str(e)}), 500
    else:
        return jsonify({'success': False, 'error': 'Metadata not found. Generate metadata first.'}), 404

@app.route('/check-processed-status')
def check_processed_status():
    """Check which files are already processed"""
    try:
        input_dir = Path(app.config['INPUT_FOLDER'])
        output_dir = Path(app.config['OUTPUT_FOLDER'])
        
        if not input_dir.exists():
            return jsonify({'success': True, 'input_files': [], 'processed_files': []})
        
        # Get all input files
        input_files = [f.name for f in input_dir.glob('*') if f.is_file() and allowed_file(f.name)]
        
        # Get all processed files
        processed_files = []
        if output_dir.exists():
            for json_file in output_dir.glob('*.json'):
                # Check if corresponding input file exists
                for ext in ['pdf', 'doc', 'docx', 'txt', 'png', 'jpg', 'jpeg']:
                    if (input_dir / f"{json_file.stem}.{ext}").exists():
                        processed_files.append(f"{json_file.stem}.{ext}")
                        break
        
        return jsonify({
            'success': True,
            'input_files': input_files,
            'processed_files': processed_files,
            'unprocessed_files': [f for f in input_files if f not in processed_files]
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/get-reports')
def get_reports():
    """Get all processed reports"""
    output_dir = Path(app.config['OUTPUT_FOLDER'])
    reports = []
    
    if output_dir.exists():
        for json_file in output_dir.glob('*.json'):
            try:
                with open(json_file, 'r') as f:
                    data = json.load(f)
                    reports.append({
                        'filename': json_file.name,
                        'name': json_file.stem,
                        'data': data,
                        'size': len(data) if isinstance(data, list) else 1
                    })
            except Exception as e:
                print(f"Error reading {json_file}: {e}")
    
    return jsonify(reports)

@app.route('/get-report/<filename>')
def get_report(filename):
    """Get specific report data"""
    output_dir = Path(app.config['OUTPUT_FOLDER'])
    json_file = output_dir / filename
    
    if json_file.exists():
        try:
            with open(json_file, 'r') as f:
                data = json.load(f)
                return jsonify({
                    'success': True,
                    'filename': filename,
                    'data': data
                })
        except Exception as e:
            return jsonify({'success': False, 'error': str(e)}), 500
    else:
        return jsonify({'success': False, 'error': 'File not found'}), 404

@app.route('/get-original/<filename>')
def get_original(filename):
    """Get original document file or processed JSON as fallback"""
    # Remove .json extension and look for original file
    base_name = filename.replace('.json', '')
    input_dir = Path(app.config['INPUT_FOLDER'])
    
    # Look for file with various extensions
    for ext in ['pdf', 'doc', 'docx', 'txt', 'png', 'jpg', 'jpeg']:
        original_file = input_dir / f"{base_name}.{ext}"
        if original_file.exists():
            return send_file(str(original_file))
    
    # If no original found, return the processed JSON as a viewable document
    output_dir = Path(app.config['OUTPUT_FOLDER'])
    json_file = output_dir / filename
    
    if json_file.exists():
        # Return JSON as a formatted HTML document
        with open(json_file, 'r', encoding='utf-8') as f:
            json_data = json.load(f)
        
        # Extract text content for display
        text_content = []
        for element in json_data:
            if element.get('type') in ['Title', 'Header']:
                text_content.append(f"<h3>{element.get('text', '')}</h3>")
            elif element.get('type') == 'Table':
                text_content.append(f"<div style='background:#f5f5f5; padding:10px; margin:10px 0;'>{element.get('text', '')}</div>")
            else:
                text_content.append(f"<p>{element.get('text', '')}</p>")
        
        html_doc = f'''
        <!DOCTYPE html>
        <html>
        <head>
            <title>{base_name}</title>
            <style>
                body {{
                    font-family: Arial, sans-serif;
                    padding: 20px;
                    background: white;
                    color: #333;
                    line-height: 1.6;
                }}
                h3 {{
                    color: #2c3e50;
                    margin: 20px 0 10px 0;
                }}
                p {{
                    margin: 10px 0;
                }}
            </style>
        </head>
        <body>
            <h1>{base_name}</h1>
            {''.join(text_content)}
        </body>
        </html>
        '''
        
        return html_doc, 200, {'Content-Type': 'text/html'}
    
    return jsonify({'success': False, 'error': 'Document not found'}), 404

@app.route('/get-assignment-preview/<filename>')
def get_assignment_preview(filename):
    """Get assignment preview showing detected roles and email addresses"""
    try:
        # Get metadata
        metadata_dir = Path(app.config['METADATA_FOLDER'])
        metadata_file = metadata_dir / f"{filename.replace('.json', '')}_metadata.json"
        
        if not metadata_file.exists():
            return jsonify({'success': False, 'error': 'Metadata not found'}), 404
        
        with open(metadata_file, 'r', encoding='utf-8') as f:
            metadata_data = json.load(f)
        
        # Initialize email service
        email_service = EmailService()
        
        # Get role summary
        role_info = email_service.get_role_summary(metadata_data['metadata'])
        
        return jsonify({
            'success': True,
            'filename': filename,
            'document_title': metadata_data['metadata'].get('document_title', filename),
            'intended_audiences': metadata_data['metadata'].get('intended_audiences', []),
            'document_categories': metadata_data['metadata'].get('document_categories', []),
            'role_info': role_info,
            'deadline': metadata_data['metadata'].get('deadline', 'N/A'),
            'job_to_do': metadata_data['metadata'].get('job_to_do', 'N/A')
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/get-compliance-data')
def get_compliance_data():
    """Get compliance and regulatory deadlines from actual processed documents"""
    try:
        output_dir = Path(app.config['OUTPUT_FOLDER'])
        metadata_dir = Path(app.config['METADATA_FOLDER'])
        
        compliance_items = []
        
        if output_dir.exists():
            for json_file in output_dir.glob('*.json'):
                try:
                    # Get metadata for this document
                    metadata_file = metadata_dir / f"{json_file.stem}_metadata.json"
                    if metadata_file.exists():
                        with open(metadata_file, 'r', encoding='utf-8') as f:
                            metadata_data = json.load(f)
                        
                        doc_metadata = metadata_data.get('metadata', {})
                        
                        # Extract deadline information
                        deadline = doc_metadata.get('deadline', '')
                        document_title = doc_metadata.get('document_title', json_file.stem)
                        job_to_do = doc_metadata.get('job_to_do', 'N/A')
                        doc_categories = doc_metadata.get('document_categories', [])
                        entities = doc_metadata.get('entities', [])
                        from_whom = doc_metadata.get('from_whom', 'Unknown')
                        
                        # Only include documents with actual deadlines
                        if deadline and deadline.lower() not in ['n/a', 'null', '', 'none']:
                            # Determine assigned personnel based on categories and entities
                            assigned_to = determine_assigned_personnel(doc_categories, entities)
                            
                            # Determine compliance category
                            compliance_category = determine_compliance_category(doc_categories, document_title, job_to_do)
                            
                            # Parse deadline and calculate status
                            parsed_deadline = parse_deadline_date(deadline)
                            status_info = calculate_compliance_status(parsed_deadline, deadline)
                            
                            compliance_items.append({
                                'filename': f"{json_file.stem}_metadata",  # Use metadata filename format
                                'title': document_title,
                                'description': f"{job_to_do} - {document_title}",
                                'deadline': parsed_deadline if parsed_deadline else deadline,
                                'original_deadline': deadline,
                                'category': compliance_category,
                                'status': status_info['status'],
                                'days_until': status_info['days_until'],
                                'assigned_to': assigned_to,
                                'from_whom': from_whom,
                                'reminder_sent': False,  # In real system, this would come from database
                                'compliance_status': metadata_data.get('compliance_status', 'pending')  # Add current status
                            })
                            
                except Exception as e:
                    print(f"Error processing compliance data for {json_file}: {e}")
        
        # Sort by deadline urgency
        compliance_items.sort(key=lambda x: x['days_until'] if isinstance(x['days_until'], int) else 999)
        
        return jsonify({
            'success': True,
            'compliance_items': compliance_items,
            'summary': {
                'total_items': len(compliance_items),
                'urgent': len([item for item in compliance_items if isinstance(item['days_until'], int) and item['days_until'] < 7]),
                'overdue': len([item for item in compliance_items if isinstance(item['days_until'], int) and item['days_until'] < 0])
            }
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

def determine_assigned_personnel(categories, entities):
    """Determine who should be assigned based on document categories and entities"""
    # Map categories to personnel
    category_assignments = {
        'Safety': 'Safety Officers',
        'HR': 'HR Manager', 
        'Engineering': 'Engineering Team',
        'Operations': 'Operations Manager',
        'Finance': 'Finance Officer',
        'Procurement': 'Procurement Manager'
    }
    
    # Check categories first
    for category in categories:
        if category in category_assignments:
            return category_assignments[category]
    
    # If no category match, use entities if available
    if entities:
        return ', '.join(entities[:2])  # First 2 entities
    
    return 'General Staff'

def determine_compliance_category(categories, title, job_to_do):
    """Determine compliance category from document data"""
    # Use document categories if available
    if categories:
        return categories[0]
    
    # Otherwise, infer from title and job
    title_lower = title.lower()
    job_lower = job_to_do.lower()
    
    if any(word in title_lower + job_lower for word in ['safety', 'compliance', 'audit']):
        return 'Safety'
    elif any(word in title_lower + job_lower for word in ['hr', 'training', 'policy']):
        return 'HR'
    elif any(word in title_lower + job_lower for word in ['engineering', 'technical']):
        return 'Engineering'
    elif any(word in title_lower + job_lower for word in ['finance', 'budget']):
        return 'Finance'
    else:
        return 'General'

def parse_deadline_date(deadline_str):
    """Parse deadline string to date format"""
    import re
    from datetime import datetime, timedelta
    
    # Try to extract date patterns
    date_patterns = [
        r'(\d{4})-(\d{1,2})-(\d{1,2})',  # YYYY-MM-DD
        r'(\d{1,2})/(\d{1,2})/(\d{4})',   # MM/DD/YYYY
        r'(\d{1,2})-(\d{1,2})-(\d{4})',   # MM-DD-YYYY
    ]
    
    for pattern in date_patterns:
        match = re.search(pattern, deadline_str)
        if match:
            try:
                if 'YYYY' in pattern:
                    year, month, day = match.groups()
                else:
                    month, day, year = match.groups()
                return f"{year}-{month.zfill(2)}-{day.zfill(2)}"
            except:
                continue
    
    # If no date pattern found, create a reasonable deadline based on urgency keywords
    deadline_lower = deadline_str.lower()
    today = datetime.now()
    
    if 'urgent' in deadline_lower or 'immediate' in deadline_lower:
        future_date = today + timedelta(days=3)
    elif 'week' in deadline_lower:
        future_date = today + timedelta(days=7)
    elif 'month' in deadline_lower:
        future_date = today + timedelta(days=30)
    else:
        future_date = today + timedelta(days=14)  # Default 2 weeks
    
    return future_date.strftime('%Y-%m-%d')

def calculate_compliance_status(parsed_deadline, original_deadline):
    """Calculate compliance status and days until deadline"""
    from datetime import datetime
    
    try:
        if parsed_deadline:
            deadline_date = datetime.strptime(parsed_deadline, '%Y-%m-%d')
            today = datetime.now()
            days_until = (deadline_date - today).days
            
            if days_until < 0:
                status = 'overdue'
            elif days_until < 7:
                status = 'urgent' 
            elif days_until < 30:
                status = 'upcoming'
            else:
                status = 'future'
                
            return {'status': status, 'days_until': days_until}
    except:
        pass
    
    # Fallback based on original deadline text
    deadline_lower = original_deadline.lower()
    if 'urgent' in deadline_lower or 'immediate' in deadline_lower:
        return {'status': 'urgent', 'days_until': 3}
    elif 'overdue' in deadline_lower or 'expired' in deadline_lower:
        return {'status': 'overdue', 'days_until': -1}
    else:
        return {'status': 'upcoming', 'days_until': 14}

@app.route('/get-role-dashboard/<role>')
def get_role_dashboard(role):
    """Get role-specific dashboard with filtered documents and notifications"""
    try:
        output_dir = Path(app.config['OUTPUT_FOLDER'])
        metadata_dir = Path(app.config['METADATA_FOLDER'])
        
        role_documents = []
        cross_team_notifications = []
        
        # Role-based document filtering rules
        role_filters = {
            'Admin': ['all'],  # Admin sees everything
            'Engineer': ['Engineering', 'Operations', 'Safety'],
            'Inspector': ['Safety', 'Compliance', 'Engineering'],
            'HR': ['HR', 'General Notice', 'Safety'],
            'Finance': ['Finance', 'Procurement', 'HR'],
            'Procurement': ['Procurement', 'Finance', 'Engineering'],
            'Safety': ['Safety', 'Operations', 'Engineering'],
            'Operations': ['Operations', 'Safety', 'Engineering']
        }
        
        # Cross-team impact detection rules
        cross_impact_rules = {
            'Engineering': ['Procurement', 'Safety', 'Operations'],
            'Safety': ['HR', 'Operations', 'Engineering'],
            'Procurement': ['Finance', 'Engineering'],
            'Finance': ['HR', 'Procurement'],
            'HR': ['Safety', 'Operations']
        }
        
        if output_dir.exists():
            for json_file in output_dir.glob('*.json'):
                try:
                    # Get metadata for this document
                    metadata_file = metadata_dir / f"{json_file.stem}_metadata.json"
                    if metadata_file.exists():
                        with open(metadata_file, 'r', encoding='utf-8') as f:
                            metadata_data = json.load(f)
                        
                        doc_metadata = metadata_data.get('metadata', {})
                        doc_categories = doc_metadata.get('document_categories', [])
                        
                        # Check if document is relevant to this role
                        user_filters = role_filters.get(role, [])
                        is_relevant = False
                        
                        if 'all' in user_filters:
                            is_relevant = True
                        else:
                            for category in doc_categories:
                                if category in user_filters:
                                    is_relevant = True
                                    break
                        
                        if is_relevant:
                            # Extract actionable parts for this role
                            actionable_summary = extract_actionable_content(
                                doc_metadata, json_file.stem, role
                            )
                            
                            role_documents.append({
                                'filename': json_file.name,
                                'name': json_file.stem,
                                'categories': doc_categories,
                                'actionable_content': actionable_summary,
                                'priority': determine_priority(doc_metadata, role),
                                'deadline': doc_metadata.get('deadline', 'N/A'),
                                'from_whom': doc_metadata.get('from_whom', 'N/A')
                            })
                        
                        # Check for cross-team notifications
                        for category in doc_categories:
                            if category in cross_impact_rules:
                                affected_teams = cross_impact_rules[category]
                                if role in affected_teams:
                                    cross_team_notifications.append({
                                        'document': json_file.stem,
                                        'source_department': category,
                                        'impact_reason': get_impact_reason(category, role),
                                        'action_required': get_required_action(category, role),
                                        'priority': 'high' if 'urgent' in doc_metadata.get('deadline', '').lower() else 'medium'
                                    })
                                    
                except Exception as e:
                    print(f"Error processing {json_file}: {e}")
        
        return jsonify({
            'success': True,
            'role': role,
            'documents': role_documents,
            'notifications': cross_team_notifications,
            'summary': {
                'total_documents': len(role_documents),
                'pending_notifications': len(cross_team_notifications),
                'high_priority': len([d for d in role_documents if d['priority'] == 'high'])
            }
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

def extract_actionable_content(metadata, document_name, role):
    """Extract role-specific actionable content from document metadata"""
    job_to_do = metadata.get('job_to_do', 'N/A')
    deadline = metadata.get('deadline', 'N/A')
    entities = metadata.get('entities', [])
    
    # Role-specific content extraction
    role_extractions = {
        'HR': f"Training/Policy Action: {job_to_do}. Staff affected: {', '.join(entities[:3]) if entities else 'All staff'}",
        'Engineer': f"Technical Implementation: {job_to_do}. Review required for: {', '.join(entities[:3]) if entities else 'Systems'}",
        'Inspector': f"Compliance Check: {job_to_do}. Inspection scope: {', '.join(entities[:3]) if entities else 'All areas'}",
        'Finance': f"Budget Impact: {job_to_do}. Cost centers: {', '.join(entities[:3]) if entities else 'TBD'}",
        'Safety': f"Safety Protocol: {job_to_do}. Areas affected: {', '.join(entities[:3]) if entities else 'All operations'}",
        'Procurement': f"Material/Service Requirements: {job_to_do}. Vendors: {', '.join(entities[:3]) if entities else 'TBD'}"
    }
    
    actionable_content = role_extractions.get(role, f"Action Required: {job_to_do}")
    
    if deadline != 'N/A' and deadline != 'null':
        actionable_content += f" | Deadline: {deadline}"
    
    return actionable_content

def determine_priority(metadata, role):
    """Determine document priority for specific role"""
    deadline = metadata.get('deadline', '').lower()
    job_to_do = metadata.get('job_to_do', '').lower()
    
    # High priority conditions
    if any(word in deadline for word in ['urgent', 'immediate', 'asap']):
        return 'high'
    if any(word in job_to_do for word in ['urgent', 'critical', 'emergency']):
        return 'high'
    
    # Medium priority for role-specific keywords
    role_keywords = {
        'Safety': ['safety', 'compliance', 'inspection'],
        'HR': ['training', 'policy', 'staff'],
        'Engineer': ['technical', 'design', 'implementation'],
        'Finance': ['budget', 'cost', 'payment']
    }
    
    if role in role_keywords:
        if any(keyword in job_to_do for keyword in role_keywords[role]):
            return 'medium'
    
    return 'low'

def get_impact_reason(source_department, affected_role):
    """Get reason why document from source department affects the role"""
    impact_reasons = {
        ('Engineering', 'Procurement'): 'Design changes may require material specification updates',
        ('Engineering', 'Safety'): 'Technical changes require safety protocol review',
        ('Safety', 'HR'): 'Safety updates require staff training and policy changes',
        ('Safety', 'Operations'): 'Safety protocols affect operational procedures',
        ('Procurement', 'Finance'): 'Procurement decisions impact budget allocations',
        ('HR', 'Safety'): 'HR policies affect safety training requirements'
    }
    
    return impact_reasons.get((source_department, affected_role), 
                            f'{source_department} changes may affect {affected_role} operations')

def get_required_action(source_department, affected_role):
    """Get required action for affected role"""
    required_actions = {
        ('Engineering', 'Procurement'): 'Review material specifications and adjust orders',
        ('Engineering', 'Safety'): 'Update safety protocols and conduct risk assessment',
        ('Safety', 'HR'): 'Update training materials and staff guidelines',
        ('Safety', 'Operations'): 'Implement new safety procedures in operations',
        ('Procurement', 'Finance'): 'Adjust budget allocations and cost projections',
        ('HR', 'Safety'): 'Coordinate training programs with safety requirements'
    }
    
    return required_actions.get((source_department, affected_role),
                              f'Review and coordinate with {source_department} team')

@app.route('/assign-work/<filename>', methods=['POST'])
def assign_work(filename):
    """Send assignment email with document, summary, and metadata"""
    try:
        # Get metadata
        metadata_dir = Path(app.config['METADATA_FOLDER'])
        metadata_file = metadata_dir / f"{filename.replace('.json', '')}_metadata.json"
        
        if not metadata_file.exists():
            return jsonify({'success': False, 'error': 'Metadata not found. Generate metadata first.'}), 404
        
        with open(metadata_file, 'r', encoding='utf-8') as f:
            metadata_data = json.load(f)
        
        # Get summary
        summary_dir = Path(app.config['SUMMARY_FOLDER'])
        summary_file = summary_dir / f"{filename.replace('.json', '')}_summary.json"
        
        summary_data = {}
        if summary_file.exists():
            with open(summary_file, 'r', encoding='utf-8') as f:
                summary_data = json.load(f)
        
        # Find original document
        base_name = filename.replace('.json', '')
        input_dir = Path(app.config['INPUT_FOLDER'])
        original_file_path = None
        
        for ext in ['pdf', 'doc', 'docx', 'txt', 'png', 'jpg', 'jpeg']:
            potential_file = input_dir / f"{base_name}.{ext}"
            if potential_file.exists():
                original_file_path = str(potential_file)
                break
        
        # Initialize email service and send email
        email_service = EmailService()
        result = email_service.send_assignment_email(
            filename,
            metadata_data['metadata'],
            summary_data,
            original_file_path
        )
        
        return jsonify(result)
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

# RAG System Endpoints
@app.route('/index-documents', methods=['POST'])
def index_documents():
    """Index all processed documents into Pinecone for RAG"""
    try:
        rag = RAGSystem()
        result = rag.index_all_processed_documents(
            output_dir=app.config['OUTPUT_FOLDER'],
            metadata_dir=app.config['METADATA_FOLDER']
        )
        return jsonify(result)
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/rag-chat', methods=['POST'])
def rag_chat():
    """Chat with documents using RAG"""
    try:
        data = request.json
        query = data.get('query', '')
        role = data.get('role', 'Admin')
        conversation_history = data.get('conversation_history', [])
        
        if not query:
            return jsonify({'success': False, 'error': 'Query is required'}), 400
        
        rag = RAGSystem()
        response = rag.chat_with_documents(query, role, conversation_history)
        
        return jsonify(response)
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/rag-chat-stream', methods=['POST'])
def rag_chat_stream():
    """Stream chat with documents using RAG"""
    try:
        data = request.json
        query = data.get('query', '')
        role = data.get('role', 'Admin')
        conversation_history = data.get('conversation_history', [])
        
        if not query:
            return jsonify({'success': False, 'error': 'Query is required'}), 400
        
        rag = RAGSystem()
        
        def generate():
            try:
                for chunk in rag.chat_with_documents_stream(query, role, conversation_history):
                    yield chunk
            except Exception as e:
                error_data = {'type': 'error', 'error': str(e)}
                yield f"data: {json.dumps(error_data)}\n\n"
        
        return Response(
            generate(),
            mimetype='text/event-stream',
            headers={
                'Cache-Control': 'no-cache',
                'Connection': 'keep-alive',
                'Access-Control-Allow-Origin': '*',
                'Access-Control-Allow-Headers': 'Content-Type'
            }
        )
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/update-action-status', methods=['POST'])
def update_action_status():
    """Update the status of a pending action"""
    try:
        data = request.json
        filename = data.get('filename', '')
        new_status = data.get('status', '')
        
        if not filename or not new_status:
            return jsonify({'success': False, 'error': 'Filename and status are required'}), 400
        
        # Load the document metadata
        metadata_path = Path(app.config['METADATA_FOLDER']) / f"{filename}.json"
        if not metadata_path.exists():
            return jsonify({'success': False, 'error': 'Document not found'}), 404
        
        with open(metadata_path, 'r') as f:
            metadata = json.load(f)
        
        # Update the status
        metadata['compliance_status'] = new_status
        metadata['last_updated'] = datetime.now().isoformat()
        
        # Save updated metadata
        with open(metadata_path, 'w') as f:
            json.dump(metadata, f, indent=2)
        
        return jsonify({
            'success': True, 
            'message': f'Status updated to {new_status}',
            'filename': filename,
            'new_status': new_status
        })
        
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/rag-search', methods=['POST'])
def rag_search():
    """Search documents using vector similarity"""
    try:
        data = request.json
        query = data.get('query', '')
        role = data.get('role', 'Admin')
        top_k = data.get('top_k', 5)
        
        if not query:
            return jsonify({'success': False, 'error': 'Query is required'}), 400
        
        rag = RAGSystem()
        results = rag.search_documents(query, role, top_k)
        
        return jsonify({
            'success': True,
            'results': results,
            'count': len(results)
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/debug-index', methods=['GET'])
def debug_index():
    """Debug what's in the Pinecone index"""
    try:
        rag = RAGSystem()
        stats = rag.debug_index_stats()
        return jsonify({
            'success': True,
            'stats': stats
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

if __name__ == '__main__':
    # Create necessary directories
    os.makedirs(app.config['INPUT_FOLDER'], exist_ok=True)
    os.makedirs(app.config['OUTPUT_FOLDER'], exist_ok=True)
    os.makedirs(app.config['SUMMARY_FOLDER'], exist_ok=True)
    os.makedirs(app.config['METADATA_FOLDER'], exist_ok=True)
    
    app.run(debug=True, port=8080, host='127.0.0.1')
