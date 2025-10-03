#!/usr/bin/env python3
"""
Admin Dashboard Integration Script
This script provides functions to integrate the admin dashboard with the department dashboard
for automatic job card and document routing.
"""

import requests
import json
from datetime import datetime
from pathlib import Path

# Configuration
DEPARTMENT_DASHBOARD_URL = "http://localhost:8081"
ROUTE_ENDPOINT = "/route-job-card"

def route_document_to_department(document_data):
    """
    Route a document from admin dashboard to appropriate department dashboard
    
    Args:
        document_data (dict): Document information from admin dashboard
        
    Returns:
        dict: Response from department dashboard
    """
    try:
        # Prepare data for department routing
        routing_data = {
            'id': document_data.get('id', 'AUTO'),
            'filename': document_data.get('filename', 'Unknown Document'),
            'type': document_data.get('type', 'General Document'),
            'content': document_data.get('content', ''),
            'summary': document_data.get('summary', ''),
            'metadata': document_data.get('metadata', {}),
            'timestamp': document_data.get('timestamp', datetime.now().isoformat())
        }
        
        # Send to department dashboard
        response = requests.post(
            f"{DEPARTMENT_DASHBOARD_URL}{ROUTE_ENDPOINT}",
            json=routing_data,
            headers={'Content-Type': 'application/json'},
            timeout=10
        )
        
        if response.status_code == 200:
            result = response.json()
            print(f"✅ Successfully routed {routing_data['filename']} to {result.get('department', 'unknown')} department")
            return result
        else:
            print(f"❌ Failed to route document: {response.status_code} - {response.text}")
            return {'success': False, 'error': f'HTTP {response.status_code}'}
            
    except requests.exceptions.RequestException as e:
        print(f"❌ Network error routing document: {e}")
        return {'success': False, 'error': str(e)}
    except Exception as e:
        print(f"❌ Error routing document: {e}")
        return {'success': False, 'error': str(e)}

def route_hr_notice_example():
    """Example function showing how to route the HR notice from your image"""
    
    # Sample data based on your actual job card image  
    hr_notice_data = {
        'id': 'DOC004',
        'filename': 'DOC004_HR_Notice',
        'type': 'HR Notice',
        'from': 'HR Portal (hr@kmrl.in)',
        'categories': ['HR Notice', 'Training', 'Safety'],
        'action_required': 'Schedule mandatory fire safety and evacuation refresher training sessions for station staff and collect their acknowledgments',
        'deadline': '2025-09-20',
        'content': 'Action Required: Schedule mandatory fire safety and evacuation refresher training sessions for station staff and collect their acknowledgments. | Deadline: 2025-09-20',
        'summary': 'HR notice requiring fire safety training coordination',
        'metadata': {
            'department_hint': 'hr',
            'urgency': 'high',
            'requires_action': True,
            'actionable_for_admin': False,
            'actionable_for_department': True,
            'document_category': 'Actionable Notice'
        },
        'timestamp': '2025-09-28T11:43:00'
    }
    
    print("🚀 Routing HR Notice to Department Dashboard...")
    result = route_document_to_department(hr_notice_data)
    
    if result.get('success'):
        print(f"📄 Document ID: {result.get('document_id')}")
        print(f"📋 Job Card ID: {result.get('job_id')}")
        print(f"🏢 Routed to: {result.get('department', 'Unknown')} Department")
        print(f"💡 Reason: {result.get('routing_reason', 'N/A')}")
    
    return result

def add_assign_work_button_integration():
    """
    Sample JavaScript code that can be added to your admin dashboard
    to integrate the 'Assign Work' button with department routing
    """
    
    js_code = """
    // Add this JavaScript to your admin dashboard for the 'Assign Work' button
    function assignWorkToDepartment(jobCardData) {
        // Extract actionable data from the job card
        const routingData = {
            id: jobCardData.id || 'AUTO',
            filename: jobCardData.filename,
            type: jobCardData.type || 'General Document',
            from: jobCardData.from || 'Admin Dashboard',
            categories: jobCardData.categories || [],
            action_required: extractActionFromJobCard(jobCardData),
            deadline: extractDeadlineFromJobCard(jobCardData),
            content: buildContentFromJobCard(jobCardData),
            summary: jobCardData.summary || '',
            metadata: {
                ...jobCardData.metadata,
                actionable_for_admin: false,
                actionable_for_department: true,
                requires_action: true,
                urgency: determineUrgencyFromJobCard(jobCardData)
            },
            timestamp: new Date().toISOString()
        };
        
        console.log('Routing job card to department:', routingData);
        
        // Send to department dashboard
        fetch('http://localhost:8081/route-job-card', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(routingData)
        })
        .then(response => response.json())
        .then(result => {
            if (result.success) {
                showAlert(`Job card successfully routed to ${result.department} department`, 'success');
                console.log('Routing result:', result);
                
                // Optionally update the UI to show it's been assigned
                updateJobCardStatus(jobCardData.id, 'assigned_to_department');
            } else {
                showAlert(`Failed to route job card: ${result.error}`, 'error');
            }
        })
        .catch(error => {
            console.error('Error routing job card:', error);
            showAlert('Network error while routing job card', 'error');
        });
    }
    
    // Helper functions to extract data from job card
    function extractActionFromJobCard(jobCard) {
        // Look for "Action Required:" in the job card content
        const content = jobCard.content || jobCard.actionableText || '';
        const actionMatch = content.match(/Action Required:?\\s*([^|]+)/i);
        return actionMatch ? actionMatch[1].trim() : '';
    }
    
    function extractDeadlineFromJobCard(jobCard) {
        // Look for "Deadline:" in the job card content
        const content = jobCard.content || jobCard.actionableText || '';
        const deadlineMatch = content.match(/Deadline:?\\s*(\\d{4}-\\d{2}-\\d{2})/i);
        return deadlineMatch ? deadlineMatch[1] : '';
    }
    
    function buildContentFromJobCard(jobCard) {
        const action = extractActionFromJobCard(jobCard);
        const deadline = extractDeadlineFromJobCard(jobCard);
        return `Action Required: ${action} | Deadline: ${deadline}`;
    }
    
    function determineUrgencyFromJobCard(jobCard) {
        const text = (jobCard.content || '').toLowerCase();
        if (text.includes('urgent') || text.includes('critical') || text.includes('mandatory')) {
            return 'high';
        }
        return 'medium';
    }
    
    // Example usage for your job card from the image
    const exampleJobCard = {
        id: 'DOC004',
        filename: 'DOC004_HR_Notice',
        type: 'HR Notice',
        from: 'HR Portal (hr@kmrl.in)',
        categories: ['HR Notice', 'Training', 'Safety'],
        content: 'Action Required: Schedule mandatory fire safety and evacuation refresher training sessions for station staff and collect their acknowledgments | Deadline: 2025-09-20',
        summary: 'HR notice requiring fire safety training coordination'
    };
    
    // Attach to 'Assign Work' button - call this when button is clicked
    document.querySelector('.assign-work-btn').addEventListener('click', () => {
        const currentJobCard = getCurrentJobCardData(); // Your function to get current job card data
        assignWorkToDepartment(currentJobCard);
    });
    """
    
    return js_code

def test_routing_system():
    """Test the routing system with various document types"""
    
    test_documents = [
        {
            'id': 'DOC001',
            'filename': 'Safety_Protocol_Update',
            'type': 'Safety Document',
            'content': 'Updated safety protocols for railway operations and emergency procedures'
        },
        {
            'id': 'DOC002', 
            'filename': 'Engineering_Maintenance_Report',
            'type': 'Technical Report',
            'content': 'Railway track maintenance report and infrastructure updates'
        },
        {
            'id': 'DOC003',
            'filename': 'Budget_Allocation_Finance',
            'type': 'Financial Document',
            'content': 'Quarterly budget allocation and financial planning document'
        },
        {
            'id': 'DOC004',
            'filename': 'DOC004_HR_Notice',
            'type': 'HR Notice',
            'content': 'Human Resources notice regarding employee policies'
        }
    ]
    
    print("🧪 Testing Document Routing System...")
    print("=" * 50)
    
    for doc in test_documents:
        print(f"\n📄 Testing: {doc['filename']}")
        result = route_document_to_department(doc)
        
        if result.get('success'):
            print(f"   ✅ Routed to: {result.get('department', 'Unknown')} Department")
        else:
            print(f"   ❌ Failed: {result.get('error', 'Unknown error')}")
    
    print("\n" + "=" * 50)
    print("🏁 Testing complete!")

if __name__ == '__main__':
    print("🚊 KMRL Admin Dashboard Integration Script")
    print("=" * 50)
    
    # Test with the HR notice from your image
    print("\n1. Testing HR Notice Routing...")
    route_hr_notice_example()
    
    print("\n2. Testing Multiple Document Types...")
    test_routing_system()
    
    print("\n3. JavaScript Integration Code:")
    print("Copy this code to your admin dashboard:")
    print("-" * 30)
    print(add_assign_work_button_integration())
