from flask import Flask, render_template, request, jsonify, send_from_directory
from flask_cors import CORS
import json
import os
from pathlib import Path
from datetime import datetime, timedelta
import uuid

app = Flask(__name__)
CORS(app, origins=['http://127.0.0.1:8080', 'http://localhost:8080', '*'], 
     methods=['GET', 'POST', 'OPTIONS'],
     allow_headers=['Content-Type'])  # Allow admin dashboard to access

# Configuration
QUERIES_FOLDER = Path('rms_queries')
DOCUMENTS_FOLDER = Path('incoming_documents')
JOB_CARDS_FOLDER = Path('job_cards')
COMPLIANCE_FOLDER = Path('compliance_alerts')

# Create necessary directories
for folder in [QUERIES_FOLDER, DOCUMENTS_FOLDER, JOB_CARDS_FOLDER, COMPLIANCE_FOLDER]:
    folder.mkdir(exist_ok=True)

# Department configurations
DEPARTMENTS = {
    'engineering': {
        'name': 'Engineering Department',
        'color': '#FF6B6B',
        'icon': '⚙️'
    },
    'procurement': {
        'name': 'Procurement Department', 
        'color': '#4ECDC4',
        'icon': '🛍️'
    },
    'hr': {
        'name': 'Human Resources',
        'color': '#45B7D1',
        'icon': '👥'
    },
    'safety': {
        'name': 'Safety Department',
        'color': '#F7DC6F',
        'icon': '🦺'
    },
    'finance': {
        'name': 'Finance Department',
        'color': '#BB8FCE',
        'icon': '💰'
    },
    'operations': {
        'name': 'Operations Department',
        'color': '#52C41A',
        'icon': '🚊'
    }
}

@app.route('/')
def index():
    return render_template('department_dashboard.html', departments=DEPARTMENTS)

@app.route('/test')
def test():
    return render_template('department_test.html')

@app.route('/test-routing')
def test_routing_page():
    return render_template('test_routing.html')

@app.route('/raise-query', methods=['POST'])
def raise_query():
    """Handle new RMS query from department"""
    try:
        data = request.json
        
        # Generate unique query ID
        query_id = str(uuid.uuid4())[:8].upper()
        
        # Create query object
        query = {
            'id': query_id,
            'department': data.get('department', 'Unknown'),
            'department_name': DEPARTMENTS.get(data.get('department', ''), {}).get('name', 'Unknown Department'),
            'title': data.get('title', ''),
            'description': data.get('description', ''),
            'priority': data.get('priority', 'medium'),
            'category': data.get('category', 'general'),
            'raised_by': data.get('raised_by', 'Anonymous'),
            'contact': data.get('contact', ''),
            'timestamp': datetime.now().isoformat(),
            'status': 'pending',
            'assigned_to': None,
            'resolution': None,
            'resolved_at': None,
            'attachments': data.get('attachments', [])
        }
        
        # Save query to file
        query_file = QUERIES_FOLDER / f'query_{query_id}.json'
        with open(query_file, 'w') as f:
            json.dump(query, f, indent=2)
        
        return jsonify({
            'success': True,
            'query_id': query_id,
            'message': f'Query {query_id} raised successfully'
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/get-department-queries/<department>')
def get_department_queries(department):
    """Get all queries raised by a specific department"""
    try:
        queries = []
        
        for query_file in QUERIES_FOLDER.glob('query_*.json'):
            with open(query_file, 'r') as f:
                query = json.load(f)
                if query['department'] == department:
                    queries.append(query)
        
        # Sort by timestamp (newest first)
        queries.sort(key=lambda x: x['timestamp'], reverse=True)
        
        return jsonify({
            'success': True,
            'queries': queries,
            'count': len(queries)
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/get-all-queries')
def get_all_queries():
    """Get all RMS queries for admin dashboard"""
    try:
        queries = []
        
        for query_file in QUERIES_FOLDER.glob('query_*.json'):
            with open(query_file, 'r') as f:
                query = json.load(f)
                queries.append(query)
        
        # Sort by timestamp (newest first)
        queries.sort(key=lambda x: x['timestamp'], reverse=True)
        
        return jsonify({
            'success': True,
            'queries': queries,
            'count': len(queries)
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/update-query-status', methods=['POST'])
def update_query_status():
    """Update status of a query (for admin)"""
    try:
        data = request.json
        query_id = data.get('query_id')
        new_status = data.get('status')
        assigned_to = data.get('assigned_to')
        resolution = data.get('resolution')
        
        query_file = QUERIES_FOLDER / f'query_{query_id}.json'
        
        if not query_file.exists():
            return jsonify({'success': False, 'error': 'Query not found'}), 404
        
        with open(query_file, 'r') as f:
            query = json.load(f)
        
        # Update query fields
        query['status'] = new_status
        if assigned_to:
            query['assigned_to'] = assigned_to
        if resolution:
            query['resolution'] = resolution
        if new_status == 'resolved':
            query['resolved_at'] = datetime.now().isoformat()
        
        # Save updated query
        with open(query_file, 'w') as f:
            json.dump(query, f, indent=2)
        
        return jsonify({
            'success': True,
            'message': f'Query {query_id} updated successfully'
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/get-query-statistics')
def get_query_statistics():
    """Get statistics about RMS queries"""
    try:
        stats = {
            'total': 0,
            'pending': 0,
            'in_progress': 0,
            'resolved': 0,
            'by_department': {},
            'by_priority': {'low': 0, 'medium': 0, 'high': 0, 'critical': 0}
        }
        
        for query_file in QUERIES_FOLDER.glob('query_*.json'):
            with open(query_file, 'r') as f:
                query = json.load(f)
                
                stats['total'] += 1
                
                # Status counts
                status = query['status']
                if status == 'pending':
                    stats['pending'] += 1
                elif status == 'in_progress':
                    stats['in_progress'] += 1
                elif status == 'resolved':
                    stats['resolved'] += 1
                
                # Department counts
                dept = query['department']
                if dept not in stats['by_department']:
                    stats['by_department'][dept] = 0
                stats['by_department'][dept] += 1
                
                # Priority counts
                priority = query.get('priority', 'medium')
                stats['by_priority'][priority] += 1
        
        return jsonify({
            'success': True,
            'statistics': stats
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

# Sample data generators (for demo purposes)
def initialize_sample_data():
    """Initialize sample data for demonstration"""
    # Sample incoming documents
    sample_docs = [
        {
            'id': 'DOC001',
            'title': 'Safety Protocol Update - Platform Operations',
            'sender': 'Safety Department',
            'type': 'Safety Circular',
            'priority': 'high',
            'received_date': (datetime.now() - timedelta(days=1)).isoformat(),
            'deadline': (datetime.now() + timedelta(days=7)).isoformat(),
            'status': 'pending',
            'relevant_departments': ['engineering', 'operations'],
            'description': 'Updated safety protocols for platform operations during peak hours'
        },
        {
            'id': 'DOC002', 
            'title': 'Budget Allocation Guidelines Q4',
            'sender': 'Finance Department',
            'type': 'Financial Document',
            'priority': 'medium',
            'received_date': (datetime.now() - timedelta(days=2)).isoformat(),
            'deadline': (datetime.now() + timedelta(days=14)).isoformat(),
            'status': 'pending',
            'relevant_departments': ['finance', 'procurement', 'operations'],
            'description': 'Q4 budget allocation guidelines and spending limits'
        }
    ]
    
    # Sample job cards
    sample_jobs = [
        {
            'id': 'JOB001',
            'task': 'Review safety circular X',
            'department': 'engineering',
            'assigned_by': 'Safety Department',
            'priority': 'high',
            'deadline': (datetime.now() + timedelta(days=5)).isoformat(),
            'status': 'pending',
            'created_date': datetime.now().isoformat(),
            'description': 'Review and approve new safety circular for platform operations',
            'estimated_hours': 4
        },
        {
            'id': 'JOB002',
            'task': 'Vendor contract evaluation',
            'department': 'procurement',
            'assigned_by': 'Finance Department',
            'priority': 'medium',
            'deadline': (datetime.now() + timedelta(days=10)).isoformat(),
            'status': 'in_progress',
            'created_date': (datetime.now() - timedelta(days=3)).isoformat(),
            'description': 'Evaluate vendor contracts for maintenance services',
            'estimated_hours': 8
        }
    ]
    
    # Sample compliance alerts
    sample_compliance = [
        {
            'id': 'COMP001',
            'title': 'Annual Safety Audit Due',
            'department': 'safety',
            'type': 'Regulatory Deadline',
            'priority': 'critical',
            'deadline': (datetime.now() + timedelta(days=3)).isoformat(),
            'status': 'overdue' if datetime.now() > datetime.now() + timedelta(days=3) else 'upcoming',
            'description': 'Annual safety audit documentation and compliance check required',
            'regulation': 'Railway Safety Act 2021'
        },
        {
            'id': 'COMP002',
            'title': 'Environmental Impact Report',
            'department': 'operations',
            'type': 'Environmental Compliance',
            'priority': 'high',
            'deadline': (datetime.now() + timedelta(days=15)).isoformat(),
            'status': 'upcoming',
            'description': 'Quarterly environmental impact assessment report',
            'regulation': 'Environmental Protection Act'
        }
    ]
    
    # Save sample data
    for doc in sample_docs:
        doc_file = DOCUMENTS_FOLDER / f'doc_{doc["id"]}.json'
        with open(doc_file, 'w') as f:
            json.dump(doc, f, indent=2)
    
    for job in sample_jobs:
        job_file = JOB_CARDS_FOLDER / f'job_{job["id"]}.json'
        with open(job_file, 'w') as f:
            json.dump(job, f, indent=2)
    
    for comp in sample_compliance:
        comp_file = COMPLIANCE_FOLDER / f'comp_{comp["id"]}.json'
        with open(comp_file, 'w') as f:
            json.dump(comp, f, indent=2)

@app.route('/get-department-documents/<department>')
def get_department_documents(department):
    """Get all incoming documents relevant to a specific department"""
    try:
        documents = []
        
        for doc_file in DOCUMENTS_FOLDER.glob('doc_*.json'):
            with open(doc_file, 'r') as f:
                doc = json.load(f)
                if department in doc.get('relevant_departments', []):
                    documents.append(doc)
        
        # Sort by priority and date
        priority_order = {'critical': 0, 'high': 1, 'medium': 2, 'low': 3}
        documents.sort(key=lambda x: (priority_order.get(x.get('priority', 'medium'), 2), x.get('received_date', '')))
        
        return jsonify({
            'success': True,
            'documents': documents,
            'count': len(documents)
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/get-department-jobs/<department>')
def get_department_jobs(department):
    """Get all job cards/tasks for a specific department"""
    try:
        jobs = []
        
        for job_file in JOB_CARDS_FOLDER.glob('job_*.json'):
            with open(job_file, 'r') as f:
                job = json.load(f)
                if job.get('department') == department:
                    # Add overdue status if deadline passed
                    deadline = datetime.fromisoformat(job['deadline'])
                    if deadline < datetime.now() and job['status'] != 'done':
                        job['is_overdue'] = True
                    jobs.append(job)
        
        # Sort by deadline
        jobs.sort(key=lambda x: x.get('deadline', ''))
        
        return jsonify({
            'success': True,
            'jobs': jobs,
            'count': len(jobs)
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/get-department-compliance/<department>')
def get_department_compliance(department):
    """Get compliance alerts for a specific department"""
    try:
        alerts = []
        
        for comp_file in COMPLIANCE_FOLDER.glob('comp_*.json'):
            with open(comp_file, 'r') as f:
                alert = json.load(f)
                if alert.get('department') == department:
                    # Update status based on deadline
                    deadline = datetime.fromisoformat(alert['deadline'])
                    days_remaining = (deadline - datetime.now()).days
                    
                    if days_remaining < 0:
                        alert['status'] = 'overdue'
                        alert['urgency'] = 'critical'
                    elif days_remaining <= 3:
                        alert['status'] = 'urgent'
                        alert['urgency'] = 'high'
                    elif days_remaining <= 7:
                        alert['status'] = 'upcoming'
                        alert['urgency'] = 'medium'
                    else:
                        alert['status'] = 'scheduled'
                        alert['urgency'] = 'low'
                    
                    alert['days_remaining'] = days_remaining
                    alerts.append(alert)
        
        # Sort by urgency and deadline
        urgency_order = {'critical': 0, 'high': 1, 'medium': 2, 'low': 3}
        alerts.sort(key=lambda x: (urgency_order.get(x.get('urgency', 'low'), 3), x.get('deadline', '')))
        
        return jsonify({
            'success': True,
            'alerts': alerts,
            'count': len(alerts)
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/update-job-status', methods=['POST'])
def update_job_status():
    """Update the status of a job card"""
    try:
        data = request.json
        job_id = data.get('job_id')
        new_status = data.get('status')
        
        job_file = JOB_CARDS_FOLDER / f'job_{job_id}.json'
        
        if not job_file.exists():
            return jsonify({'success': False, 'error': 'Job not found'}), 404
        
        with open(job_file, 'r') as f:
            job = json.load(f)
        
        job['status'] = new_status
        if new_status == 'done':
            job['completed_date'] = datetime.now().isoformat()
        
        with open(job_file, 'w') as f:
            json.dump(job, f, indent=2)
        
        return jsonify({
            'success': True,
            'message': f'Job {job_id} status updated to {new_status}'
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/get-enhanced-queries/<department>')
def get_enhanced_queries(department):
    """Get enhanced RMS queries with responses for a department"""
    try:
        queries = []
        
        for query_file in QUERIES_FOLDER.glob('query_*.json'):
            with open(query_file, 'r') as f:
                query = json.load(f)
                if query['department'] == department:
                    # Add sample responses for demo
                    if query['status'] != 'pending':
                        query['responses'] = [
                            {
                                'from': 'Admin',
                                'message': 'Query received and under review. Assigned to relevant team.',
                                'timestamp': (datetime.fromisoformat(query['timestamp']) + timedelta(hours=2)).isoformat(),
                                'type': 'status_update'
                            }
                        ]
                        if query['status'] == 'resolved':
                            query['responses'].append({
                                'from': 'Engineering Department',
                                'message': 'Issue has been resolved. Please verify and confirm.',
                                'timestamp': (datetime.fromisoformat(query['timestamp']) + timedelta(days=1)).isoformat(),
                                'type': 'resolution'
                            })
                    queries.append(query)
        
        # Sort by timestamp (newest first)
        queries.sort(key=lambda x: x['timestamp'], reverse=True)
        
        return jsonify({
            'success': True,
            'queries': queries,
            'count': len(queries)
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/route-job-card', methods=['POST'])
def route_job_card():
    """Receive job cards from admin dashboard and route to appropriate departments"""
    try:
        data = request.json
        
        # Extract department routing logic based on document metadata
        department = determine_department_from_metadata(data)
        
        if not department:
            return jsonify({
                'success': False,
                'error': 'Could not determine target department'
            }), 400
        
        # Create job card
        job_card = create_job_card_from_admin_data(data, department)
        
        # Create incoming document entry
        document_entry = create_document_from_admin_data(data, department)
        
        # Save job card
        job_id = job_card['id']
        job_file = JOB_CARDS_FOLDER / f'job_{job_id}.json'
        with open(job_file, 'w') as f:
            json.dump(job_card, f, indent=2)
        
        # Save document entry
        doc_id = document_entry['id']
        doc_file = DOCUMENTS_FOLDER / f'doc_{doc_id}.json'
        with open(doc_file, 'w') as f:
            json.dump(document_entry, f, indent=2)
        
        return jsonify({
            'success': True,
            'message': f'Job card and document routed to {DEPARTMENTS[department]["name"]}',
            'job_id': job_id,
            'document_id': doc_id,
            'department': department
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

def determine_department_from_metadata(data):
    """Determine target department based on document metadata and content"""
    doc_name = data.get('filename', '').lower()
    doc_type = data.get('type', '').lower()
    content = data.get('content', '').lower()
    
    # Department routing rules
    routing_rules = {
        'hr': ['hr', 'human resources', 'employee', 'recruitment', 'payroll', 'leave', 'personnel'],
        'engineering': ['engineering', 'technical', 'maintenance', 'infrastructure', 'construction', 'railway', 'track'],
        'safety': ['safety', 'accident', 'hazard', 'security', 'emergency', 'risk', 'protocol'],
        'finance': ['finance', 'financial', 'budget', 'cost', 'invoice', 'payment', 'accounting', 'audit'],
        'procurement': ['procurement', 'purchase', 'vendor', 'supplier', 'contract', 'tender', 'buying'],
        'operations': ['operation', 'schedule', 'timetable', 'service', 'passenger', 'train', 'station']
    }
    
    # Check filename first
    for dept, keywords in routing_rules.items():
        if any(keyword in doc_name for keyword in keywords):
            return dept
    
    # Check document type
    for dept, keywords in routing_rules.items():
        if any(keyword in doc_type for keyword in keywords):
            return dept
    
    # Check content
    for dept, keywords in routing_rules.items():
        if any(keyword in content for keyword in keywords):
            return dept
    
    # Default fallback based on common patterns
    if 'notice' in doc_name and 'hr' in doc_name:
        return 'hr'
    elif 'circular' in doc_name:
        return 'operations'  # Most circulars go to operations
    
    return 'operations'  # Default department

def create_job_card_from_admin_data(data, department):
    """Create a job card from admin dashboard data"""
    job_id = str(uuid.uuid4())[:8].upper()
    
    # Extract actionable tasks from the data
    action_required = extract_action_required(data)
    deadline = extract_deadline(data)
    
    # Use the actual action as the task, not just "Review"
    task = action_required if action_required else f'{determine_task_type(data)} - {data.get("filename", "Document")}'
    
    return {
        'id': job_id,
        'task': task,
        'department': department,
        'assigned_by': data.get('from', 'Admin Dashboard'),
        'priority': determine_priority_from_data(data),
        'deadline': deadline,
        'status': 'pending',
        'created_date': datetime.now().isoformat(),
        'description': action_required if action_required else f'Process and take action on {data.get("filename", "document")}',
        'estimated_hours': estimate_hours_from_action(action_required),
        'source': 'admin_dashboard',
        'original_doc_id': data.get('id', 'N/A'),
        'metadata': data.get('metadata', {}),
        'action_details': {
            'original_action': action_required,
            'document_categories': data.get('categories', []),
            'sender': data.get('from', 'Unknown'),
            'actionable_for': department
        }
    }

def create_document_from_admin_data(data, department):
    """Create an incoming document entry from admin dashboard data"""
    doc_id = data.get('id', str(uuid.uuid4())[:8].upper())
    
    return {
        'id': doc_id,
        'title': data.get('filename', 'Untitled Document'),
        'sender': 'Admin Dashboard',
        'type': data.get('type', 'General Document'),
        'priority': determine_priority_from_data(data),
        'received_date': datetime.now().isoformat(),
        'deadline': (datetime.now() + timedelta(days=7)).isoformat(),
        'status': 'pending',
        'relevant_departments': [department],
        'description': f'Document received from admin dashboard: {data.get("filename", "N/A")}',
        'source': 'admin_dashboard',
        'metadata': data.get('metadata', {}),
        'summary': data.get('summary', 'Summary not available')
    }

def determine_task_type(data):
    """Determine the type of task based on document data"""
    doc_name = data.get('filename', '').lower()
    doc_type = data.get('type', '').lower()
    
    if 'notice' in doc_name or 'notice' in doc_type:
        return 'Review Notice'
    elif 'circular' in doc_name or 'circular' in doc_type:
        return 'Review Circular'
    elif 'report' in doc_name or 'report' in doc_type:
        return 'Review Report'
    elif 'policy' in doc_name or 'policy' in doc_type:
        return 'Review Policy'
    else:
        return 'Review Document'

def extract_action_required(data):
    """Extract the specific action required from document data"""
    # Check for action in various fields
    action = data.get('action_required', '')
    
    if not action:
        # Try to extract from content
        content = data.get('content', '')
        if 'action required:' in content.lower():
            # Extract text after "Action Required:"
            parts = content.lower().split('action required:')
            if len(parts) > 1:
                action = parts[1].split('|')[0].strip()  # Take part before deadline
    
    if not action:
        # Try metadata
        metadata = data.get('metadata', {})
        action = metadata.get('action', '')
    
    # Clean up the action text
    if action:
        action = action.strip().capitalize()
        if not action.endswith('.'):
            action += '.'
    
    return action

def extract_deadline(data):
    """Extract deadline from document data"""
    # Check for deadline in various formats
    deadline_str = data.get('deadline', '')
    
    if not deadline_str:
        # Try to extract from content
        content = data.get('content', '')
        if 'deadline:' in content.lower():
            parts = content.lower().split('deadline:')
            if len(parts) > 1:
                deadline_str = parts[1].strip().split()[0]  # Take the first word after deadline
    
    if not deadline_str:
        # Try metadata
        metadata = data.get('metadata', {})
        deadline_str = metadata.get('deadline', '')
    
    # Parse deadline or use default
    if deadline_str:
        try:
            # Try parsing various date formats
            if '-' in deadline_str:
                # Format like "2025-09-20"
                deadline_date = datetime.strptime(deadline_str, '%Y-%m-%d')
            else:
                # Default to 7 days from now
                deadline_date = datetime.now() + timedelta(days=7)
            
            return deadline_date.isoformat()
        except ValueError:
            pass
    
    # Default to 7 days from now
    return (datetime.now() + timedelta(days=7)).isoformat()

def estimate_hours_from_action(action):
    """Estimate hours required based on the action description"""
    if not action:
        return 2  # Default
    
    action_lower = action.lower()
    
    # Complex actions requiring more time
    if any(keyword in action_lower for keyword in ['training', 'schedule', 'coordinate', 'organize', 'implement']):
        return 8
    elif any(keyword in action_lower for keyword in ['review', 'analyze', 'evaluate', 'assess']):
        return 4
    elif any(keyword in action_lower for keyword in ['collect', 'gather', 'update', 'notify']):
        return 2
    else:
        return 3  # Default for unknown actions

def determine_priority_from_data(data):
    """Determine priority based on document content and metadata"""
    doc_name = data.get('filename', '').lower()
    content = data.get('content', '').lower()
    action = data.get('action_required', '').lower()
    
    high_priority_keywords = ['urgent', 'critical', 'immediate', 'emergency', 'asap', 'mandatory']
    medium_priority_keywords = ['important', 'priority', 'review', 'action required', 'training']
    
    # Check all relevant fields
    all_text = f"{doc_name} {content} {action}".lower()
    
    if any(keyword in all_text for keyword in high_priority_keywords):
        return 'high'
    elif any(keyword in all_text for keyword in medium_priority_keywords):
        return 'medium'
    else:
        return 'medium'  # Default to medium

@app.route('/test-routing', methods=['POST'])
def test_routing():
    """Test endpoint to simulate routing from admin dashboard"""
    # Simulate the exact job card from your image
    test_data = {
        'id': 'DOC004',
        'filename': 'DOC004_HR_Notice',
        'type': 'HR Notice',
        'from': 'HR Portal (hr@kmrl.in)',
        'categories': ['HR Notice', 'Training', 'Safety'],
        'action_required': 'Schedule mandatory fire safety and evacuation refresher training sessions for station staff and collect their acknowledgments',
        'deadline': '2025-09-20',
        'content': 'Action Required: Schedule mandatory fire safety and evacuation refresher training sessions for station staff and collect their acknowledgments. | Deadline: 2025-09-20',
        'timestamp': '2025-09-28T11:43:00',
        'summary': 'HR notice requiring fire safety training coordination',
        'metadata': {
            'department_hint': 'hr',
            'urgency': 'high',
            'requires_action': True,
            'actionable_for_admin': False,
            'actionable_for_department': True
        }
    }
    
    return route_job_card_with_data(test_data)

def route_job_card_with_data(data):
    """Helper function to route job card with provided data"""
    try:
        # Extract department routing logic based on document metadata
        department = determine_department_from_metadata(data)
        
        if not department:
            return jsonify({
                'success': False,
                'error': 'Could not determine target department'
            }), 400
        
        # Create job card
        job_card = create_job_card_from_admin_data(data, department)
        
        # Create incoming document entry
        document_entry = create_document_from_admin_data(data, department)
        
        # Save job card
        job_id = job_card['id']
        job_file = JOB_CARDS_FOLDER / f'job_{job_id}.json'
        with open(job_file, 'w') as f:
            json.dump(job_card, f, indent=2)
        
        # Save document entry
        doc_id = document_entry['id']
        doc_file = DOCUMENTS_FOLDER / f'doc_{doc_id}.json'
        with open(doc_file, 'w') as f:
            json.dump(document_entry, f, indent=2)
        
        return jsonify({
            'success': True,
            'message': f'Job card and document routed to {DEPARTMENTS[department]["name"]}',
            'job_id': job_id,
            'document_id': doc_id,
            'department': department,
            'routing_reason': f'Routed based on filename and content analysis'
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

if __name__ == '__main__':
    initialize_sample_data()  # Initialize sample data on startup
    app.run(debug=True, port=8081)  # Run on port 8081
