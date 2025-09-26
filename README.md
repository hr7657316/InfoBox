# Document Processing System

A clean and efficient document processing system using the Unstructured API.

## Features

- 📁 **File Upload**: Web interface for document upload
- 🔄 **API Processing**: Direct integration with Unstructured API
- 📝 **JSON to Markdown**: Convert structured data to readable format
- 🧠 **AI Summarization**: Generate intelligent summaries using Gemini AI
- 🌐 **Malayalam Translation**: Translate summaries to Malayalam language
- 🔍 **Side-by-side Comparison**: View original documents with confidence scores
- 🌐 **Web Interface**: Complete dashboard for file management

## Setup

1. **Install Dependencies**:
   ```bash
   pip install flask flask-cors python-dotenv requests google-generativeai
   ```

2. **Configure API Keys**:
   Create `.env` file:
   ```
   UNSTRUCTURED_API_KEY=your_unstructured_api_key_here
   GEMINI_API_KEY=your_gemini_api_key_here
   ```

3. **Run Application**:
   ```bash
   python app.py
   ```

4. **Access**: Open http://127.0.0.1:5000

## Usage

1. **Upload**: Upload documents via web interface
2. **Process**: Click "Process Documents" to send to API
3. **View**: Check results in JSON format
4. **Convert**: Convert JSON to Markdown for readability
5. **Summarize**: Generate AI summaries with Malayalam translations
6. **Compare**: Use side-by-side view with confidence scores

## Project Structure

```
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
```

## Requirements

- Python 3.9+
- Valid Unstructured API key
- Valid Google Gemini API key
- Flask and dependencies (see app.py imports)# InfoBox
