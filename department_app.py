from flask import Flask, render_template, request, jsonify, send_from_directory
from flask_cors import CORS
import json
import os
from pathlib import Path
from datetime import datetime
import uuid

app = Flask(__name__)
CORS(app, origins=['http://127.0.0.1:8080', 'http://localhost:8080', '*'], 
     methods=['GET', 'POST', 'OPTIONS'],
     allow_headers=['Content-Type'])  # Allow admin dashboard to access

# Configuration
QUERIES_FOLDER = Path('rms_queries')
QUERIES_FOLDER.mkdir(exist_ok=True)

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

if __name__ == '__main__':
    app.run(debug=True, port=8081)  # Run on port 8081
