# 🚊 KMRL Railway Management System

**AI-Powered Document Intelligence Platform** for Kochi Metro Rail Limited (KMRL) - Streamlining document processing, job card management, and inter-department communication with advanced AI capabilities.




## 🌟 Key Features

### 📄 Document Intelligence
- **Automated Document Processing** - AI-powered classification and routing
- **Multilingual OCR** - Support for multiple languages with Nanonets integration
- **Smart Metadata Extraction** - Automatic tagging and categorization
- **Dual RAG System** - Universal and department-specific knowledge retrieval

### 🏗️ Job Card Management
- **One-Click Job Assignment** - Instant routing to relevant departments
- **Real-time Status Tracking** - Monitor job progress (Pending → In Progress → Done)
- **Priority-based Task Management** - Urgent items highlighted
- **Automated Department Routing** - AI-powered target department detection

### 🔔 Instant Notifications
- **Multi-Channel Alerts** - Email, WhatsApp, SMS, and Push notifications
- **One-Click Acknowledgment** - Quick response from department staff
- **Delivery Confirmation** - Track notification status in real-time
- **Escalation Workflow** - Automatic follow-up for unacknowledged items

### 📊 Department Dashboards
- **Role-Based Access Control** - Customized views for each department
- **Compliance Tracking** - Regulatory deadline monitoring
- **RMS Query System** - Inter-department communication
- **Document Repository** - Easy access to department-specific files

### 🛡️ Compliance & Security
- **Regulatory Monitoring** - Railway Safety Act and Environmental Protection Act tracking
- **Audit Trails** - Complete action logging
- **Role-Based Permissions** - Granular access control
- **Data Encryption** - Secure document storage and transmission

### 🛡️ Q & A over documents
- **Document Processing** - AI-powered classification and routing
- **Multilingual OCR** - Support for multiple languages with Nanonets integration
- **Smart Metadata Extraction** - Automatic tagging and categorization
- **Dual RAG System** - Universal and department-specific knowledge retrieval




## 🚀 Quick Start

### Prerequisites
- Python 3.9+
- PostgreSQL 13+
- Redis (for task queue)
- Node.js 16+ (for frontend assets)

### Installation

1. **Clone the repository**
   ```bash
   git clone https://github.com/your-org/kmrl-railway-system.git
   
   ```

Install Dependencies:

pip install flask flask-cors python-dotenv requests google-generativeai
Configure API Keys: Create .env file:

UNSTRUCTURED_API_KEY=your_unstructured_api_key_here
GEMINI_API_KEY=your_gemini_api_key_here
Run Application:

python app.py
Access: Open http://127.0.0.1:5000

Usage
Upload: Upload documents via web interface
Process: Click "Process Documents" to send to API
View: Check results in JSON format
Convert: Convert JSON to Markdown for readability
Summarize: Generate AI summaries with Malayalam translations
Compare: Use side-by-side view with confidence scores
Project Structure
unstructured/
├── app.py                 # Main Flask application
├── json_to_markdown.py    # JSON to Markdown converter
├── gemini_service.py      # AI summarization and translation
├── .env                   # API configuration
├── templates/             # HTML templates
├── uploads/               # Uploaded documents
├── output_documenty/      # JSON processing results
├── markdown_output/       # Converted Markdown files
└── summaries/             # AI summaries with translations
Requirements
Python 3.9+
Valid Unstructured API key
Valid Google Gemini API key
Flask and dependencies (see app.py imports)# InfoBox