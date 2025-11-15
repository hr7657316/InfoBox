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
   cd kmrl-railway-system
   ```

2. **Set up Python environment**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   pip install -r requirements.txt
   ```

3. **Configure environment variables**
   Create `.env` file with:
   ```env
   # Database
   DATABASE_URL=postgresql://user:password@localhost:5432/kmrl_db
   REDIS_URL=redis://localhost:6379/0
   
   # API Keys
   UNSTRUCTURED_API_KEY=your_unstructured_api_key
   GEMINI_API_KEY=your_gemini_api_key
   WHATSAPP_API_KEY=your_whatsapp_api_key
   SMS_API_KEY=your_sms_api_key
   
   # App Settings
   SECRET_KEY=your_secret_key
   DEBUG=True
   ```

4. **Initialize database**
   ```bash
   flask db upgrade
   flask init-db
   ```

5. **Run the application**
   ```bash
   # Start Redis server (in a new terminal)
   redis-server
   
   # Start Celery worker (in a new terminal)
   celery -A app.celery worker --loglevel=info
   
   # Start the Flask application
   flask run
   ```

6. **Access the application**
   - Admin Dashboard: http://localhost:5000/admin
   - Department Dashboard: http://localhost:5000/department

## 🏗️ System Architecture

```
kmrl-railway-system/
├── app/
│   ├── __init__.py         # Flask application factory
│   ├── models.py           # Database models
│   ├── routes/             # Application routes
│   │   ├── admin.py        # Admin dashboard routes
│   │   ├── department.py   # Department dashboard routes
│   │   ├── api.py          # REST API endpoints
│   │   └── auth.py         # Authentication routes
│   ├── services/
│   │   ├── document_processor.py  # Document processing logic
│   │   ├── notification.py        # Notification service
│   │   ├── rag_system.py          # RAG implementation
│   │   └── routing_engine.py      # Smart routing logic
│   └── utils/
│       ├── validators.py   # Input validation
│       └── helpers.py      # Helper functions
├── migrations/             # Database migrations
├── static/                 # Static files (JS, CSS, images)
├── templates/              # HTML templates
│   ├── admin/              # Admin dashboard templates
│   ├── department/         # Department dashboard templates
│   └── auth/               # Authentication templates
├── tests/                  # Test suite
├── .env.example           # Example environment variables
├── config.py              # Configuration settings
├── requirements.txt       # Python dependencies
└── wsgi.py                # WSGI entry point
```

## 🔧 API Documentation

### Authentication
```http
POST /api/auth/login
Content-Type: application/json

{
  "username": "admin@kmrl.in",
  "password": "your_password"
}
```

### Document Processing
```http
POST /api/documents/upload
Authorization: Bearer <token>
Content-Type: multipart/form-data

{
  "file": <file_upload>,
  "department": "hr|engineering|procurement|safety|finance|operations",
  "priority": "low|medium|high|critical"
}
```

### Job Card Management
```http
POST /api/jobcards
Authorization: Bearer <token>
Content-Type: application/json

{
  "title": "Fire Safety Training",
  "description": "Conduct fire safety training for station staff",
  "department": "safety",
  "deadline": "2025-10-31",
  "priority": "high"
}
```

## 🤝 Contributing

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 📞 Contact

For support or queries, please contact:
- Email: support@kmrl.in
- Phone: +91-XXX-XXXX-XXXX

---

<div align="center">
  <h3>Built with ❤️ for KMRL</h3>
  <p>Transforming Railway Management with AI</p>
</div>
