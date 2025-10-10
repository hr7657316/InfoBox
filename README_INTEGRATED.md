# 🚀 Integrated Data Extraction + Document Processing System

> **A comprehensive solution combining automated data extraction from WhatsApp/Email with AI-powered document processing and intelligent assignment workflows.**

[![Python](https://img.shields.io/badge/Python-3.8+-blue.svg)](https://python.org)
[![Flask](https://img.shields.io/badge/Flask-2.3.3-green.svg)](https://flask.palletsprojects.com/)
[![AI Powered](https://img.shields.io/badge/AI-Powered-orange.svg)](https://ai.google.dev/)

## 🎯 Overview

This integrated system combines two powerful capabilities:

1. **📊 Data Extraction Pipeline** - Automated extraction from WhatsApp Business API and Email (IMAP)
2. **📄 InfoBox Document Processing** - AI-powered document analysis with smart assignment workflows

### 🌟 Key Features

| Feature Category | Capabilities |
|------------------|-------------|
| **📊 Data Extraction** | WhatsApp Business API, Email IMAP, Multi-account support, Scheduled extraction |
| **📄 Document Processing** | PDF/DOC/Image parsing, AI summarization, Malayalam translation, Metadata extraction |
| **🤖 AI Integration** | Google Gemini AI, Unstructured API, Smart content analysis, Role-based routing |
| **🌐 Web Interface** | Modern responsive UI, Real-time processing, Document management, Assignment workflows |
| **📧 Smart Assignment** | Role-based email routing, Professional templates, Automated notifications |

---

## 🚀 Quick Start

### 📋 Prerequisites

- **Python 3.8+**
- **Virtual Environment** (recommended)
- **API Keys**: Google Gemini, Unstructured API (optional)
- **Email Account**: Gmail with app password for notifications

### ⚡ Installation

1. **Clone and Setup**
```bash
git clone <repository-url>
cd data-extraction-pipeline
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
```

2. **Install Dependencies**
```bash
pip install -r requirements.txt
```

3. **Configure Environment**
```bash
cp .env.example .env
# Edit .env with your API keys and credentials
```

4. **Test Integration**
```bash
python test_integration.py
```

5. **Start Integrated System**
```bash
python integrated_app.py --mode integrated
```

6. **Access Web Interface**
Open: **http://127.0.0.1:9090**

---

## 🎯 Usage Modes

### 🔄 Integrated Mode (Recommended)
```bash
python integrated_app.py --mode integrated
```
- Full system with both pipeline and document processing
- Unified web interface
- All features available

### 📊 Pipeline Only Mode
```bash
python integrated_app.py --mode pipeline-only --config config.test.yaml --test-pipeline
```
- Data extraction pipeline only
- Command-line interface
- Good for automation/scheduling

### 📄 InfoBox Only Mode
```bash
python integrated_app.py --mode infobox-only --port 9090
```
- Document processing only
- Web interface for document upload and analysis
- AI summarization and assignment

---

## 📊 Data Extraction Pipeline

### Supported Sources
- **WhatsApp Business API** - Messages, media, metadata
- **Email (IMAP)** - Gmail, Outlook, custom servers
- **Multi-account Support** - Process multiple accounts simultaneously

### Features
- ✅ Automated scheduling
- ✅ Rate limiting and retry logic
- ✅ Media file download
- ✅ Deduplication
- ✅ Multiple output formats (JSON, CSV)
- ✅ Comprehensive error handling
- ✅ Notification system

### Configuration
Edit `config.yaml` or `config.test.yaml`:

```yaml
# WhatsApp Configuration
whatsapp:
  enabled: true
  api_provider: "business_api"
  business_api:
    phone_number_id: "your_phone_id"
    access_token: "your_access_token"

# Email Configuration  
email:
  enabled: true
  accounts:
    - name: "primary_gmail"
      email: "your@gmail.com"
      auth_method: "oauth2"
      oauth2:
        client_id: "your_client_id"
        client_secret: "your_client_secret"
        refresh_token: "your_refresh_token"
```

---

## 📄 InfoBox Document Processing

### Document Support
- **Formats**: PDF, DOC, DOCX, TXT, Images (PNG, JPG, etc.)
- **Processing**: Text extraction, structure analysis, metadata extraction
- **AI Analysis**: Summarization, translation, role detection

### AI Features
- **🤖 Smart Summarization** - Google Gemini AI
- **🌍 Malayalam Translation** - Bilingual support
- **🏷️ Metadata Extraction** - KMRL-specific fields
- **📧 Role-based Assignment** - Automatic email routing

### Web Interface Features
- **📤 Drag & Drop Upload** - Multiple file support
- **⚡ Real-time Processing** - Live progress updates
- **📊 Document Dashboard** - Grid view with actions
- **🔍 Content Preview** - Summaries and metadata
- **📧 Assignment Workflow** - Smart email routing

---

## 🤖 AI Integration

### Google Gemini AI
- **Summarization**: Intelligent content analysis
- **Translation**: English to Malayalam
- **Role Detection**: Automatic audience identification

### Unstructured API (Optional)
- **Document Parsing**: Advanced structure extraction
- **Multi-format Support**: PDF, Office documents, images
- **Content Analysis**: Tables, forms, layouts

### LangExtract
- **Metadata Extraction**: KMRL-specific fields
- **Structured Output**: JSON format
- **Custom Templates**: Configurable extraction patterns

---

## 📧 Smart Assignment System

### Role-based Routing
| Role | Document Types | Email Address |
|------|---------------|---------------|
| **HR** | Personnel, policies | hr@kmrl.co.in |
| **Engineer** | Technical specs, reports | engineer@kmrl.co.in |
| **Inspector** | Safety, compliance | inspector@kmrl.co.in |
| **Contractor** | Work orders, agreements | contractor@kmrl.co.in |
| **Manager** | Administrative | manager@kmrl.co.in |
| **Finance** | Budget, invoices | finance@kmrl.co.in |

### Email Features
- **📧 Professional Templates** - HTML formatted
- **📎 Attachment Handling** - Original documents included
- **⏰ Deadline Highlighting** - Important dates emphasized
- **🔄 Real-time Configuration** - Update addresses without restart

---

## 🛠️ Configuration

### Environment Variables (.env)
```bash
# Data Extraction Pipeline
WHATSAPP_ACCESS_TOKEN=your_token
GMAIL_CLIENT_ID=your_client_id
EMAIL_PRIMARY_ADDRESS=your@gmail.com

# InfoBox Document Processing
UNSTRUCTURED_API_KEY=your_unstructured_key
GOOGLE_API_KEY=your_gemini_key
EMAIL_USER=notifications@yourdomain.com
EMAIL_PASSWORD=your_app_password

# Role-based Email Addresses
HR_EMAIL=hr@kmrl.co.in
ENGINEER_EMAIL=engineer@kmrl.co.in
# ... (see .env.example for complete list)
```

### Configuration Files
- **`config.yaml`** - Production configuration
- **`config.test.yaml`** - Test configuration with mock data
- **`.env`** - Environment variables (not in git)
- **`.env.example`** - Template for environment setup

---

## 🧪 Testing

### Integration Test
```bash
python test_integration.py
```

### Pipeline Test
```bash
python integrated_app.py --config config.test.yaml --mode pipeline-only --test-pipeline
```

### Configuration Validation
```bash
python integrated_app.py --validate-only
```

### Mock Data Extraction
```bash
python run_pipeline.py --config config.test.yaml --mock-mode
```

---

## 🚀 Deployment

### Docker Deployment
```bash
# Build and deploy
./scripts/deploy.sh

# Or manual Docker
docker-compose up -d
```

### Local Development
```bash
# Setup environment
./scripts/setup.sh

# Start integrated system
python integrated_app.py --mode integrated
```

### Production Deployment
1. Configure production credentials in `.env`
2. Update `config.yaml` with production settings
3. Use Docker deployment for scalability
4. Set up reverse proxy (nginx) for production

---

## 📁 Project Structure

```
integrated-system/
├── 🐍 Core Pipeline
│   ├── pipeline/              # Data extraction pipeline
│   ├── run_pipeline.py        # Pipeline entry point
│   └── integrated_app.py      # Integrated application
├── 📄 InfoBox Components
│   ├── app_ui.py              # Flask web application
│   ├── gemini_service.py      # AI summarization
│   ├── metadata_extractor.py  # Metadata extraction
│   └── email_service.py       # Email assignment
├── 🌐 Web Interface
│   └── templates/
│       └── index.html         # Modern web UI
├── 🧪 Testing
│   ├── test_integration.py    # Integration tests
│   └── tests/                 # Comprehensive test suite
├── 📋 Configuration
│   ├── config.yaml           # Production config
│   ├── config.test.yaml      # Test config
│   ├── .env.example          # Environment template
│   └── requirements.txt      # Dependencies
├── 🚀 Deployment
│   ├── scripts/              # Deployment scripts
│   ├── Dockerfile           # Container config
│   └── docker-compose.yml   # Orchestration
└── 📚 Documentation
    ├── README_INTEGRATED.md  # This file
    ├── DEPLOYMENT.md         # Deployment guide
    └── docs/                 # Additional documentation
```

---

## 🔧 API Endpoints

### Pipeline Endpoints
| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/api/pipeline/status` | GET | Pipeline status |
| `/api/pipeline/extract` | POST | Trigger extraction |
| `/api/pipeline/results` | GET | Get extraction results |

### InfoBox Endpoints
| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/upload` | POST | Upload documents |
| `/process` | POST | Process documents |
| `/get-summary/<filename>` | GET | Get AI summary |
| `/get-metadata/<filename>` | GET | Get metadata |
| `/assign-work/<filename>` | POST | Send assignment email |

---

## 🔍 Monitoring and Logs

### Log Files
- **`logs/pipeline.log`** - Pipeline execution logs
- **`logs/infobox.log`** - Document processing logs
- **Console Output** - Real-time status updates

### Monitoring
- **Health Checks** - Built-in system validation
- **Error Tracking** - Comprehensive error handling
- **Performance Metrics** - Execution time tracking
- **Success Rates** - Source-wise success tracking

---

## 🤝 Contributing

1. **Fork the repository**
2. **Create feature branch** (`git checkout -b feature/AmazingFeature`)
3. **Run tests** (`python test_integration.py`)
4. **Commit changes** (`git commit -m 'Add AmazingFeature'`)
5. **Push to branch** (`git push origin feature/AmazingFeature`)
6. **Open Pull Request**

---

## 📞 Support

- **Integration Issues**: Run `python test_integration.py`
- **Configuration Help**: Check `.env.example` and `config.yaml`
- **API Setup**: See `docs/` directory for setup guides
- **Deployment**: Use `./scripts/deploy.sh` for automated deployment

---

## 🎉 Success Stories

### ✅ Validated Integration
- **Pipeline + InfoBox**: Seamlessly integrated
- **AI Processing**: Google Gemini + LangExtract working
- **Web Interface**: Modern, responsive, functional
- **Smart Assignment**: Role-based routing operational

### 📊 Test Results
```
🎉 All integration tests PASSED!

🌟 System Ready:
  📊 Data Extraction Pipeline: Functional
  📄 Document Processing: Functional
  🌐 Web Interface: Ready
  🤖 AI Integration: Ready
```

---

<div align="center">

**🚀 Integrated Data Extraction + Document Processing System**

*Combining automated data extraction with AI-powered document intelligence*

**Ready for Production Deployment**

</div>