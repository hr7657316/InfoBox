from flask import Flask, render_template, request, jsonify, send_file
from flask_cors import CORS
import os
import json
from pathlib import Path
from werkzeug.utils import secure_filename
from dotenv import load_dotenv
import requests
from gemini_service import GeminiService
from metadata_extractor import MetadataExtractor
from email_service import EmailService

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
    
    return jsonify({
        'success': True,
        'uploaded_files': uploaded_files,
        'message': f'Successfully uploaded {len(uploaded_files)} files'
    })

@app.route('/process', methods=['POST'])
def process_documents():
    """Process documents using Unstructured API"""
    try:
        # Get API key from environment
        api_key = os.getenv("UNSTRUCTURED_API_KEY")
        if not api_key:
            return jsonify({'success': False, 'error': 'API key not found'}), 500
        
        # Get files from input directory
        input_dir = Path(app.config['INPUT_FOLDER'])
        if not input_dir.exists():
            return jsonify({'success': False, 'error': 'No files to process'}), 400
            
        files_to_process = [f for f in input_dir.glob('*') if f.is_file() and allowed_file(f.name)]
        
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
        
        # Step 2: Automatically generate summaries
        summary_results = {'success': True, 'count': 0, 'errors': []}
        try:
            gemini = GeminiService()
            json_files = list(output_dir.glob('*.json'))
            summary_dir = Path(app.config['SUMMARY_FOLDER'])
            summary_dir.mkdir(exist_ok=True)
            
            for json_file in json_files:
                try:
                    result = gemini.summarize_and_translate_document(str(json_file))
                    if not result['error']:
                        output_file = summary_dir / f"{json_file.stem}_summary.json"
                        summary_data = {
                            'original_file': json_file.name,
                            'timestamp': str(json_file.stat().st_mtime),
                            'summary': result['summary'],
                            'malayalam_summary': result['malayalam_summary']
                        }
                        with open(output_file, 'w', encoding='utf-8') as f:
                            json.dump(summary_data, f, indent=2, ensure_ascii=False)
                        summary_results['count'] += 1
                    else:
                        summary_results['errors'].append(f"{json_file.name}: {result['summary']}")
                except Exception as e:
                    summary_results['errors'].append(f"{json_file.name}: {str(e)}")
        except Exception as e:
            summary_results['success'] = False
            summary_results['error'] = str(e)
        
        # Step 3: Automatically generate metadata
        metadata_results = {'success': True, 'count': 0, 'errors': []}
        try:
            extractor = MetadataExtractor()
            json_files = list(output_dir.glob('*.json'))
            metadata_dir = Path(app.config['METADATA_FOLDER'])
            metadata_dir.mkdir(exist_ok=True)
            
            for json_file in json_files:
                try:
                    result = extractor.extract_metadata_from_json_file(str(json_file))
                    if not result['error']:
                        output_file = metadata_dir / f"{json_file.stem}_metadata.json"
                        metadata_data = {
                            'original_file': json_file.name,
                            'timestamp': str(json_file.stat().st_mtime),
                            'extraction_text': result['extraction_text'],
                            'metadata': result['metadata']
                        }
                        with open(output_file, 'w', encoding='utf-8') as f:
                            json.dump(metadata_data, f, indent=2, ensure_ascii=False)
                        metadata_results['count'] += 1
                    else:
                        metadata_results['errors'].append(f"{json_file.name}: {result['message']}")
                except Exception as e:
                    metadata_results['errors'].append(f"{json_file.name}: {str(e)}")
        except Exception as e:
            metadata_results['success'] = False
            metadata_results['error'] = str(e)
        
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
    """Get original document file"""
    # Remove .json extension and look for original file
    base_name = filename.replace('.json', '')
    input_dir = Path(app.config['INPUT_FOLDER'])
    
    # Look for file with various extensions
    for ext in ['pdf', 'doc', 'docx', 'txt', 'png', 'jpg', 'jpeg']:
        original_file = input_dir / f"{base_name}.{ext}"
        if original_file.exists():
            return send_file(str(original_file))
    
    return jsonify({'success': False, 'error': 'Original file not found'}), 404

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

@app.route('/reload-config', methods=['POST'])
def reload_config():
    """Reload configuration from .env file"""
    try:
        from dotenv import load_dotenv
        load_dotenv(override=True)
        return jsonify({
            'success': True,
            'message': 'Configuration reloaded successfully'
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
