# 🚊 InfoBox - KMRL Railway Management System

**AI-Powered Document Intelligence Platform** for Kochi Metro Rail Limited (KMRL) - Streamlining document processing, job card management, and inter-department communication with advanced AI capabilities.

[![Python](https://img.shields.io/badge/Python-3.9+-blue.svg)](https://python.org)
[![Flask](https://img.shields.io/badge/Flask-2.0+-green.svg)](https://flask.palletsprojects.com/)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

## 📋 Table of Contents
- [Overview](#overview)
- [Demo Video](#-demo-video)
- [System Architecture](#️-system-architecture)
- [Key Features](#-key-features)
- [Quick Start](#-quick-start)
- [Installation](#installation)
- [Usage](#usage)
- [Project Structure](#project-structure)
- [API Documentation](#api-documentation)
- [Contributing](#contributing)
- [License](#license)

## Overview

InfoBox is a comprehensive document intelligence platform designed specifically for railway management systems. It leverages cutting-edge AI technologies to automate document processing, enhance inter-department communication, and ensure regulatory compliance.

## � Demo

https://github.com/user-attachments/assets/c3e06a8a-08c9-43ad-aa1e-0daae7c66fc7

o Video


Watch InfoBox in action! This demo showcases the complete document processing workflow and key features of the KMRL Railway Management System:

> **🎬 Demo**: *Document Overload at Kochi Metro Rail Limited - InfoBox Solution*

### 📹 Video Highlights
- **Document Upload & Processing** - See how documents are automatically classified and routed
- **AI-Powered Intelligence** - Watch real-time OCR, metadata extraction, and content analysis
- **Department Dashboards** - Explore role-based interfaces for different departments
- **Job Card Management** - Observe automated job assignment and tracking
- **Multi-channel Notifications** - Experience instant alerts and acknowledgments
- **Q&A System** - Interact with documents using natural language queries

### 🎯 What You'll See
- Complete end-to-end document workflow
- Real-time AI processing capabilities
- User-friendly interface design
- Multi-department coordination
- Compliance and regulatory tracking


---

## �🏗️ System Architecture

The InfoBox platform follows a modular, microservices-based architecture designed for scalability and maintainability:

![System Architecture](docs/images/system-architecture.png)

### Architecture Components

- **Frontend Layer** - React-based user interface with department-specific dashboards
- **API Gateway** - Flask-based REST API handling all client requests
- **Document Processing Engine** - AI-powered document classification and extraction
- **RAG System** - Retrieval Augmented Generation for intelligent document querying
- **Notification Service** - Multi-channel alert system (Email, SMS, WhatsApp)
- **Database Layer** - PostgreSQL for structured data, Redis for caching
- **External Integrations** - Unstructured.io, Google Gemini AI, Nanonets OCR


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

### � Q&A Over Documents
- **Intelligent Document Querying** - Ask questions about uploaded documents
- **Context-Aware Responses** - AI-powered answers with source citations
- **Multi-language Support** - Query documents in multiple languages
- **Confidence Scoring** - Reliability indicators for AI responses





## 🚀 Quick Start

### Prerequisites
- **Python 3.12.5** (Recommended - tested and verified)
- Valid API keys for:
  - Unstructured.io
  - Google Gemini AI
  - Groq API
  - Pinecone (for vector database)

### Installation

1. **Clone the repository**
   ```bash
   git clone https://github.com/hr7657316/InfoBox.git
   cd InfoBox
   ```

2. **Create Virtual Environment**
   ```bash
   # Create virtual environment with Python 3.12
   python3.12 -m venv venv
   
   # Activate virtual environment
   # On macOS/Linux:
   source venv/bin/activate
   
   # On Windows:
   # venv\Scripts\activate
   ```

3. **Install Dependencies**
   ```bash
   # Upgrade pip first
   pip install --upgrade pip
   
   # Install all requirements
   pip install -r requirements.txt
   ```

4. **Configure Environment Variables**
   
   Copy the example environment file and configure your API keys:
   ```bash
   cp .env.example .env
   ```
   
   Edit `.env` file with your API keys and configuration:
   ```env
   # AI Service API Keys
   UNSTRUCTURED_API_KEY=your_unstructured_api_key_here
   GEMINI_API_KEY=your_gemini_api_key_here
   GROQ_API_KEY=your_groq_api_key_here
   PINECONE_API_KEY=your_pinecone_api_key_here
   
   # Email Configuration (for notifications)
   EMAIL_USER=your_email@gmail.com
   EMAIL_PASSWORD=your_app_password
   SMTP_SERVER=smtp.gmail.com
   SMTP_PORT=587
   
   # KMRL Department Email Addresses
   HR_EMAIL=hr@kmrl.org
   ENGINEER_EMAIL=engineer@kmrl.org
   INSPECTOR_EMAIL=inspector@kmrl.org
   CONTRACTOR_EMAIL=contractor@kmrl.org
   MANAGER_EMAIL=manager@kmrl.org
   FINANCE_EMAIL=finance@kmrl.org
   GENERAL_EMAIL=general@kmrl.org
   SAFETY_EMAIL=safety@kmrl.org
   OPERATIONS_EMAIL=operations@kmrl.org
   ```
   
   > ⚠️ **Security Note**: Never commit your `.env` file to version control. Use `.env.example` as a template.

5. **Run the Applications**

   **For Frontend Applications:**
   ```bash
   # Main UI Dashboard (recommended for most users)
   python app_ui.py
   
   # Department-specific Dashboard
   python department_app.py
   ```
   
   **For CLI Document Processing:**
   ```bash
   # Command-line document processing
   python app.py
   ```

6. **Access the Applications**
   
   - **Main Dashboard**: `http://127.0.0.1:5000`
   - **Department Dashboard**: `http://127.0.0.1:5001` (if running department_app.py)
   
   > 💡 **Tip**: Start with `python app_ui.py` for the best user experience with the web interface.

## Usage

### Basic Workflow

1. **Upload Documents** - Use the web interface to upload documents
2. **Process Documents** - Click "Process Documents" to send to AI processing
3. **View Results** - Check processing results in JSON format
4. **Convert & Summarize** - Generate Markdown summaries with Malayalam translations
5. **Query Documents** - Ask questions about your documents using the Q&A feature

### Advanced Features

- **Department Routing** - Documents are automatically routed to relevant departments
- **Job Card Creation** - Generate job cards with one-click assignment
- **Compliance Monitoring** - Track regulatory deadlines and requirements
- **Multi-channel Notifications** - Receive alerts via email, SMS, or push notifications

### Email Notification System

InfoBox includes a comprehensive email notification system for real-time alerts:

**Configuration Requirements:**
- Configure SMTP settings in `.env` file
- Set up department-specific email addresses
- Use Gmail App Passwords for enhanced security

**Notification Types:**
- Document processing completion alerts
- Job card assignments and status updates
- Compliance deadline reminders
- Inter-department communication alerts
- System status notifications

**Department-Specific Routing:**
- Each KMRL department has dedicated email addresses
- Automatic routing based on document classification
- Role-based notification preferences

## Project Structure

```
InfoBox/
├── app.py                      # Main Flask application
├── app_ui.py                   # UI components and routes
├── department_app.py           # Department-specific functionality
├── gemini_service.py           # AI summarization and translation
├── confidence_scorer.py        # Confidence scoring for AI responses
├── metadata_extractor.py       # Document metadata extraction
├── processing.py               # Document processing pipeline
├── rag_system.py              # RAG (Retrieval Augmented Generation) system
├── email_service.py           # Email notification service
├── admin_integration.py       # Admin panel integration
├── requirements.txt           # Python dependencies
├── .env.example              # Environment variables template
├── templates/                # HTML templates
│   ├── index.html
│   ├── department_dashboard.html
│   └── test_routing.html
├── static/                   # Static assets (CSS, JS, images)
├── documents-testing/        # Test documents
├── incoming_documents/       # Document intake folder
├── output_documenty/         # JSON processing results
├── summaries/               # AI-generated summaries
├── metadata/                # Extracted metadata
├── job_cards/               # Generated job cards
├── compliance_alerts/       # Compliance monitoring
├── rms_data/                # Railway Management System data
└── rms_queries/             # Query history and responses
```

## API Documentation

### Core Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/` | GET | Main dashboard |
| `/upload` | POST | Upload documents |
| `/process` | POST | Process uploaded documents |
| `/department/<dept_name>` | GET | Department-specific dashboard |
| `/api/query` | POST | Query documents using AI |
| `/api/job-cards` | GET | Retrieve job cards |
| `/api/compliance` | GET | Compliance status |

### Authentication

The system uses role-based authentication. Contact your system administrator for access credentials.

## Contributing

We welcome contributions! Please follow these steps:

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/amazing-feature`
3. Commit your changes: `git commit -m 'Add amazing feature'`
4. Push to the branch: `git push origin feature/amazing-feature`
5. Open a Pull Request

### Development Guidelines

- Follow PEP 8 style guidelines
- Add tests for new features
- Update documentation as needed
- Ensure all existing tests pass

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Support

For support and questions:
- 📧 Email: support@infobox-kmrl.com
- 📚 Documentation: [Wiki](https://github.com/hr7657316/InfoBox/wiki)
- 🐛 Issues: [GitHub Issues](https://github.com/hr7657316/InfoBox/issues)

---

**Made with ❤️ for Kochi Metro Rail Limited (KMRL)**
