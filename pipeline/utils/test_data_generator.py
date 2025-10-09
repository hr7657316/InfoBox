"""
Test data generator for pipeline testing and validation
"""

from datetime import datetime, timedelta
from typing import List, Dict, Any
import random
import uuid
from pipeline.models import WhatsAppMessage, Email


class TestDataGenerator:
    """Generate realistic test data for pipeline validation"""
    
    def __init__(self):
        self.sample_phone_numbers = [
            "+1234567890",
            "+9876543210", 
            "+5555551234",
            "+1111222333"
        ]
        
        self.sample_emails = [
            "john.doe@example.com",
            "jane.smith@company.org",
            "test.user@domain.net",
            "admin@testsite.com"
        ]
        
        self.sample_subjects = [
            "Meeting Reminder",
            "Project Update",
            "Weekly Report",
            "Important Notice",
            "Follow-up Required"
        ]
        
        self.sample_messages = [
            "Hello, how are you doing today?",
            "Can we schedule a meeting for tomorrow?",
            "Please review the attached document.",
            "Thanks for your help with the project.",
            "Looking forward to hearing from you."
        ]
    
    def generate_whatsapp_messages(self, count: int = 5) -> List[WhatsAppMessage]:
        """
        Generate sample WhatsApp messages for testing
        
        Args:
            count: Number of messages to generate
            
        Returns:
            List of WhatsAppMessage objects
        """
        messages = []
        
        for i in range(count):
            # Generate timestamp within last 30 days
            days_ago = random.randint(0, 30)
            hours_ago = random.randint(0, 23)
            minutes_ago = random.randint(0, 59)
            
            timestamp = datetime.now() - timedelta(
                days=days_ago, 
                hours=hours_ago, 
                minutes=minutes_ago
            )
            
            # Randomly choose message type
            message_types = ["text", "image", "audio", "video", "document"]
            message_type = random.choice(message_types)
            
            # Generate media info for non-text messages
            media_url = None
            media_filename = None
            media_size = None
            
            if message_type != "text":
                media_url = f"https://example.com/media/{uuid.uuid4()}.{message_type}"
                media_filename = f"test_media_{i+1}.{message_type}"
                media_size = random.randint(1024, 1024*1024)  # 1KB to 1MB
            
            message = WhatsAppMessage(
                id=f"whatsapp_msg_{i+1}_{uuid.uuid4().hex[:8]}",
                timestamp=timestamp,
                sender_phone=random.choice(self.sample_phone_numbers),
                message_content=random.choice(self.sample_messages),
                message_type=message_type,
                media_url=media_url,
                media_filename=media_filename,
                media_size=media_size
            )
            
            messages.append(message)
        
        return messages
    
    def generate_emails(self, count: int = 3) -> List[Email]:
        """
        Generate sample emails for testing
        
        Args:
            count: Number of emails to generate
            
        Returns:
            List of Email objects
        """
        emails = []
        
        for i in range(count):
            # Generate timestamp within last 30 days
            days_ago = random.randint(0, 30)
            hours_ago = random.randint(0, 23)
            minutes_ago = random.randint(0, 59)
            
            timestamp = datetime.now() - timedelta(
                days=days_ago,
                hours=hours_ago,
                minutes=minutes_ago
            )
            
            # Generate attachments randomly
            attachments = []
            if random.choice([True, False]):  # 50% chance of having attachments
                num_attachments = random.randint(1, 3)
                for j in range(num_attachments):
                    attachment = {
                        "filename": f"attachment_{j+1}.pdf",
                        "size": random.randint(1024, 1024*1024),
                        "content_type": "application/pdf"
                    }
                    attachments.append(attachment)
            
            # Generate email body
            body_text = f"This is a test email message #{i+1}. " + random.choice(self.sample_messages)
            body_html = f"<html><body><p>{body_text}</p></body></html>"
            
            email = Email(
                id=f"email_{i+1}_{uuid.uuid4().hex[:8]}",
                timestamp=timestamp,
                sender_email=random.choice(self.sample_emails),
                recipient_emails=["test@example.com"],
                subject=random.choice(self.sample_subjects),
                body_text=body_text,
                body_html=body_html,
                attachments=attachments,
                is_read=random.choice([True, False]),
                folder="INBOX"
            )
            
            emails.append(email)
        
        return emails
    
    def generate_extraction_result_data(self) -> Dict[str, Any]:
        """
        Generate complete test data for extraction results
        
        Returns:
            Dictionary containing test messages and emails
        """
        return {
            'whatsapp_messages': self.generate_whatsapp_messages(5),
            'emails': self.generate_emails(3)
        }