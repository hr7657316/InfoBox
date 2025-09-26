#!/usr/bin/env python3

import smtplib
import json
import os
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class EmailService:
    def __init__(self):
        """Initialize email service with SMTP configuration"""
        self.smtp_server = os.getenv("SMTP_SERVER", "smtp.gmail.com")
        self.smtp_port = int(os.getenv("SMTP_PORT", "587"))
        self.email_user = os.getenv("EMAIL_USER")
        self.email_password = os.getenv("EMAIL_PASSWORD")
        
        # KMRL role-based email mapping
        self.role_emails = {
            "HR": os.getenv("HR_EMAIL", "hr@kmrl.co.in"),
            "Engineer": os.getenv("ENGINEER_EMAIL", "engineer@kmrl.co.in"),
            "Railway Inspector": os.getenv("INSPECTOR_EMAIL", "inspector@kmrl.co.in"),
            "Contractor": os.getenv("CONTRACTOR_EMAIL", "contractor@kmrl.co.in"),
            "Manager": os.getenv("MANAGER_EMAIL", "manager@kmrl.co.in"),
            "Finance Officer": os.getenv("FINANCE_EMAIL", "finance@kmrl.co.in"),
            "General Staff": os.getenv("GENERAL_EMAIL", "general@kmrl.co.in"),
            "Safety": os.getenv("SAFETY_EMAIL", "safety@kmrl.co.in"),
            "Operations": os.getenv("OPERATIONS_EMAIL", "operations@kmrl.co.in")
        }
    
    def get_recipients_from_metadata(self, metadata):
        """Extract recipient emails based on metadata intended audiences"""
        recipients = []
        intended_audiences = metadata.get('intended_audiences', [])
        document_categories = metadata.get('document_categories', [])
        
        # Get emails based on intended audiences
        for audience in intended_audiences:
            if audience in self.role_emails:
                recipients.append(self.role_emails[audience])
        
        # If no specific audience, use document categories
        if not recipients:
            for category in document_categories:
                if category in self.role_emails:
                    recipients.append(self.role_emails[category])
        
        # Remove duplicates and filter out None values
        recipients = list(set([email for email in recipients if email]))
        
        # If still no recipients, send to general staff
        if not recipients:
            recipients = [self.role_emails["General Staff"]]
        
        return recipients
    
    def get_role_summary(self, metadata):
        """Get a summary of detected roles and their email addresses"""
        recipients = self.get_recipients_from_metadata(metadata)
        role_info = []
        
        for email in recipients:
            # Find role name for this email
            role = next((role for role, addr in self.role_emails.items() if addr == email), "Unknown")
            role_info.append({
                'role': role,
                'email': email
            })
        
        return role_info
    
    def create_email_content(self, document_name, metadata, summary_data):
        """Create HTML email content with summary and metadata"""
        
        # Extract key information
        doc_title = metadata.get('document_title', document_name)
        from_whom = metadata.get('from_whom', 'N/A')
        deadline = metadata.get('deadline', 'N/A')
        job_to_do = metadata.get('job_to_do', 'N/A')
        categories = ', '.join(metadata.get('document_categories', []))
        entities = ', '.join(metadata.get('entities', []))
        
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <style>
                body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                .header {{ background: linear-gradient(135deg, #2196F3, #1976D2); color: white; padding: 20px; border-radius: 8px; margin-bottom: 20px; }}
                .section {{ margin-bottom: 20px; padding: 15px; border-left: 4px solid #2196F3; background: #f8f9fa; }}
                .metadata-field {{ margin-bottom: 10px; }}
                .label {{ font-weight: bold; color: #2196F3; }}
                .urgent {{ color: #f44336; font-weight: bold; }}
                .summary-box {{ background: white; padding: 20px; border-radius: 8px; border: 1px solid #ddd; }}
                .malayalam {{ background: #e3f2fd; padding: 15px; border-radius: 8px; margin-top: 15px; }}
            </style>
        </head>
        <body>
            <div class="header">
                <h2>🚄 KMRL Document Assignment</h2>
                <p>Document: <strong>{doc_title}</strong></p>
            </div>
            
            <div class="section">
                <h3>📋 Document Details</h3>
                <div class="metadata-field"><span class="label">From:</span> {from_whom}</div>
                <div class="metadata-field"><span class="label">Categories:</span> {categories}</div>
                <div class="metadata-field"><span class="label">Entities:</span> {entities}</div>
                {"<div class='metadata-field urgent'><span class='label'>⏰ Deadline:</span> " + deadline + "</div>" if deadline != 'N/A' and deadline != 'null' else ""}
                {"<div class='metadata-field urgent'><span class='label'>✅ Action Required:</span> " + job_to_do + "</div>" if job_to_do != 'N/A' and job_to_do != 'null' else ""}
            </div>
            
            <div class="section">
                <h3>📊 Document Summary</h3>
                <div class="summary-box">
                    <h4>English Summary:</h4>
                    <p>{summary_data.get('summary', 'Summary not available')}</p>
                    
                    <div class="malayalam">
                        <h4>Malayalam Summary:</h4>
                        <p>{summary_data.get('malayalam_summary', 'Malayalam summary not available')}</p>
                    </div>
                </div>
            </div>
            
            <div class="section">
                <h3>📎 Attachment</h3>
                <p>The original document is attached to this email for your review.</p>
            </div>
            
            <hr>
            <p><small>This email was automatically generated by the KMRL Document Processing System.</small></p>
        </body>
        </html>
        """
        
        return html_content

    def send_assignment_email(self, document_filename, metadata, summary_data, original_file_path):
        """Send assignment email with document, summary, and metadata"""
        try:
            if not self.email_user or not self.email_password:
                return {
                    'success': False,
                    'error': 'Email credentials not configured. Please set EMAIL_USER and EMAIL_PASSWORD in .env file.'
                }
            
            # Get recipients based on metadata
            recipients = self.get_recipients_from_metadata(metadata)
            
            if not recipients:
                return {
                    'success': False,
                    'error': 'No valid recipients found for this document.'
                }
            
            # Create email
            msg = MIMEMultipart()
            msg['From'] = self.email_user
            msg['To'] = ', '.join(recipients)
            
            doc_title = metadata.get('document_title', document_filename)
            deadline = metadata.get('deadline', '')
            urgency = " [URGENT]" if deadline not in ['N/A', 'null', ''] else ""
            
            msg['Subject'] = f"KMRL Document Assignment: {doc_title}{urgency}"
            
            # Create HTML content
            html_content = self.create_email_content(document_filename, metadata, summary_data)
            msg.attach(MIMEText(html_content, 'html'))
            
            # Attach original document if it exists
            if original_file_path and Path(original_file_path).exists():
                with open(original_file_path, "rb") as attachment:
                    part = MIMEBase('application', 'octet-stream')
                    part.set_payload(attachment.read())
                    encoders.encode_base64(part)
                    part.add_header(
                        'Content-Disposition',
                        f'attachment; filename= {Path(original_file_path).name}'
                    )
                    msg.attach(part)
            
            # Send email with detailed logging
            print(f"Attempting to send email to: {recipients}")
            print(f"From: {self.email_user}")
            print(f"Subject: {msg['Subject']}")
            
            server = smtplib.SMTP(self.smtp_server, self.smtp_port)
            server.set_debuglevel(1)  # Enable debug output
            server.starttls()
            server.login(self.email_user, self.email_password)
            text = msg.as_string()
            result = server.sendmail(self.email_user, recipients, text)
            server.quit()
            
            print(f"SMTP send result: {result}")
            
            return {
                'success': True,
                'recipients': recipients,
                'message': f'✅ Email sent successfully to {len(recipients)} recipients!\n\nSent from: {self.email_user}\nSent to: {", ".join(recipients)}\nSubject: {msg["Subject"]}'
            }
            
        except Exception as e:
            return {
                'success': False,
                'error': f'Failed to send email: {str(e)}'
            }