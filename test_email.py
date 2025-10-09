#!/usr/bin/env python3

import smtplib
import os
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def test_email():
    """Test email sending functionality"""
    
    # Get credentials
    email_user = os.getenv("EMAIL_USER")
    email_password = os.getenv("EMAIL_PASSWORD")
    
    print(f"Testing email from: {email_user}")
    print(f"Password configured: {'Yes' if email_password else 'No'}")
    
    if not email_user or not email_password:
        print("❌ Email credentials not configured!")
        return
    
    # Create test email
    msg = MIMEMultipart()
    msg['From'] = email_user
    msg['To'] = "astroknowladge@gmail.com"
    msg['Subject'] = "🧪 KMRL Email System Test"
    
    body = """
    <html>
    <body>
        <h2>🚄 KMRL Document Processing System</h2>
        <p>This is a test email to verify the email system is working correctly.</p>
        <p><strong>✅ If you receive this email, the system is configured properly!</strong></p>
        <hr>
        <p><small>Sent from KMRL Document Processing System</small></p>
    </body>
    </html>
    """
    
    msg.attach(MIMEText(body, 'html'))
    
    try:
        # Send email
        print("Connecting to SMTP server...")
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.set_debuglevel(1)  # Show detailed logs
        server.starttls()
        print("Logging in...")
        server.login(email_user, email_password)
        print("Sending email...")
        result = server.sendmail(email_user, ["astroknowladge@gmail.com"], msg.as_string())
        server.quit()
        
        print(f"✅ Email sent successfully!")
        print(f"SMTP result: {result}")
        print(f"📧 Check astroknowladge@gmail.com inbox (and spam folder)")
        
    except Exception as e:
        print(f"❌ Email failed: {str(e)}")

if __name__ == "__main__":
    test_email()
