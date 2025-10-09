"""
Enhanced unit tests for data models
"""

import unittest
from datetime import datetime
from dataclasses import FrozenInstanceError

from pipeline.models import WhatsAppMessage, Email, ExtractionResult, BaseExtractor


class TestWhatsAppMessage(unittest.TestCase):
    """Test cases for WhatsAppMessage model"""
    
    def test_whatsapp_message_creation(self):
        """Test creating WhatsAppMessage with required fields"""
        timestamp = datetime(2024, 1, 15, 10, 30, 0)
        
        message = WhatsAppMessage(
            id="msg_123",
            timestamp=timestamp,
            sender_phone="+1234567890",
            message_content="Hello, world!",
            message_type="text"
        )
        
        self.assertEqual(message.id, "msg_123")
        self.assertEqual(message.timestamp, timestamp)
        self.assertEqual(message.sender_phone, "+1234567890")
        self.assertEqual(message.message_content, "Hello, world!")
        self.assertEqual(message.message_type, "text")
        self.assertIsNone(message.media_url)
        self.assertIsNone(message.media_filename)
        self.assertIsNone(message.media_size)
        self.assertIsInstance(message.extracted_at, datetime)
    
    def test_whatsapp_message_with_media(self):
        """Test creating WhatsAppMessage with media fields"""
        timestamp = datetime(2024, 1, 15, 10, 30, 0)
        extracted_at = datetime(2024, 1, 15, 11, 0, 0)
        
        message = WhatsAppMessage(
            id="msg_456",
            timestamp=timestamp,
            sender_phone="+1234567890",
            message_content="Check this image",
            message_type="image",
            media_url="https://example.com/image.jpg",
            media_filename="image_20240115.jpg",
            media_size=1024000,
            extracted_at=extracted_at
        )
        
        self.assertEqual(message.media_url, "https://example.com/image.jpg")
        self.assertEqual(message.media_filename, "image_20240115.jpg")
        self.assertEqual(message.media_size, 1024000)
        self.assertEqual(message.extracted_at, extracted_at)
    
    def test_whatsapp_message_auto_extracted_at(self):
        """Test that extracted_at is automatically set if not provided"""
        before_creation = datetime.now()
        
        message = WhatsAppMessage(
            id="msg_789",
            timestamp=datetime.now(),
            sender_phone="+1234567890",
            message_content="Auto timestamp test",
            message_type="text"
        )
        
        after_creation = datetime.now()
        
        self.assertGreaterEqual(message.extracted_at, before_creation)
        self.assertLessEqual(message.extracted_at, after_creation)
    
    def test_whatsapp_message_types(self):
        """Test different message types"""
        message_types = ["text", "image", "audio", "video", "document"]
        
        for msg_type in message_types:
            message = WhatsAppMessage(
                id=f"msg_{msg_type}",
                timestamp=datetime.now(),
                sender_phone="+1234567890",
                message_content=f"Test {msg_type} message",
                message_type=msg_type
            )
            
            self.assertEqual(message.message_type, msg_type)
    
    def test_whatsapp_message_equality(self):
        """Test WhatsAppMessage equality comparison"""
        timestamp = datetime(2024, 1, 15, 10, 30, 0)
        
        message1 = WhatsAppMessage(
            id="msg_123",
            timestamp=timestamp,
            sender_phone="+1234567890",
            message_content="Hello",
            message_type="text"
        )
        
        message2 = WhatsAppMessage(
            id="msg_123",
            timestamp=timestamp,
            sender_phone="+1234567890",
            message_content="Hello",
            message_type="text"
        )
        
        # Note: extracted_at will be different, so messages won't be equal
        # This tests that the dataclass comparison works as expected
        self.assertNotEqual(message1, message2)  # Due to different extracted_at
        
        # Test with same extracted_at
        message2.extracted_at = message1.extracted_at
        self.assertEqual(message1, message2)
    
    def test_whatsapp_message_string_representation(self):
        """Test string representation of WhatsAppMessage"""
        message = WhatsAppMessage(
            id="msg_123",
            timestamp=datetime(2024, 1, 15, 10, 30, 0),
            sender_phone="+1234567890",
            message_content="Hello",
            message_type="text"
        )
        
        str_repr = str(message)
        self.assertIn("msg_123", str_repr)
        self.assertIn("+1234567890", str_repr)
        self.assertIn("text", str_repr)


class TestEmail(unittest.TestCase):
    """Test cases for Email model"""
    
    def test_email_creation(self):
        """Test creating Email with required fields"""
        timestamp = datetime(2024, 1, 15, 10, 30, 0)
        
        email = Email(
            id="email_123",
            timestamp=timestamp,
            sender_email="sender@example.com",
            recipient_emails=["recipient1@example.com", "recipient2@example.com"],
            subject="Test Subject",
            body_text="Plain text body",
            body_html="<p>HTML body</p>",
            attachments=[],
            is_read=False,
            folder="INBOX"
        )
        
        self.assertEqual(email.id, "email_123")
        self.assertEqual(email.timestamp, timestamp)
        self.assertEqual(email.sender_email, "sender@example.com")
        self.assertEqual(len(email.recipient_emails), 2)
        self.assertIn("recipient1@example.com", email.recipient_emails)
        self.assertIn("recipient2@example.com", email.recipient_emails)
        self.assertEqual(email.subject, "Test Subject")
        self.assertEqual(email.body_text, "Plain text body")
        self.assertEqual(email.body_html, "<p>HTML body</p>")
        self.assertEqual(email.attachments, [])
        self.assertFalse(email.is_read)
        self.assertEqual(email.folder, "INBOX")
        self.assertIsInstance(email.extracted_at, datetime)
    
    def test_email_with_attachments(self):
        """Test creating Email with attachments"""
        attachments = [
            {
                "filename": "document.pdf",
                "size": 1024000,
                "content_type": "application/pdf"
            },
            {
                "filename": "image.jpg",
                "size": 512000,
                "content_type": "image/jpeg"
            }
        ]
        
        email = Email(
            id="email_456",
            timestamp=datetime.now(),
            sender_email="sender@example.com",
            recipient_emails=["recipient@example.com"],
            subject="Email with attachments",
            body_text="Please see attached files",
            body_html="<p>Please see attached files</p>",
            attachments=attachments,
            is_read=True,
            folder="INBOX"
        )
        
        self.assertEqual(len(email.attachments), 2)
        self.assertEqual(email.attachments[0]["filename"], "document.pdf")
        self.assertEqual(email.attachments[1]["filename"], "image.jpg")
        self.assertTrue(email.is_read)
    
    def test_email_auto_extracted_at(self):
        """Test that extracted_at is automatically set if not provided"""
        before_creation = datetime.now()
        
        email = Email(
            id="email_789",
            timestamp=datetime.now(),
            sender_email="sender@example.com",
            recipient_emails=["recipient@example.com"],
            subject="Auto timestamp test",
            body_text="Test body",
            body_html="<p>Test body</p>",
            attachments=[],
            is_read=False,
            folder="INBOX"
        )
        
        after_creation = datetime.now()
        
        self.assertGreaterEqual(email.extracted_at, before_creation)
        self.assertLessEqual(email.extracted_at, after_creation)
    
    def test_email_different_folders(self):
        """Test emails in different folders"""
        folders = ["INBOX", "SENT", "DRAFTS", "SPAM", "TRASH"]
        
        for folder in folders:
            email = Email(
                id=f"email_{folder.lower()}",
                timestamp=datetime.now(),
                sender_email="sender@example.com",
                recipient_emails=["recipient@example.com"],
                subject=f"Email in {folder}",
                body_text="Test body",
                body_html="<p>Test body</p>",
                attachments=[],
                is_read=False,
                folder=folder
            )
            
            self.assertEqual(email.folder, folder)
    
    def test_email_empty_recipient_list(self):
        """Test email with empty recipient list"""
        email = Email(
            id="email_no_recipients",
            timestamp=datetime.now(),
            sender_email="sender@example.com",
            recipient_emails=[],
            subject="No recipients",
            body_text="Test body",
            body_html="<p>Test body</p>",
            attachments=[],
            is_read=False,
            folder="DRAFTS"
        )
        
        self.assertEqual(len(email.recipient_emails), 0)
    
    def test_email_html_only(self):
        """Test email with HTML content only"""
        email = Email(
            id="email_html_only",
            timestamp=datetime.now(),
            sender_email="sender@example.com",
            recipient_emails=["recipient@example.com"],
            subject="HTML only email",
            body_text="",
            body_html="<h1>HTML Content</h1><p>This is HTML only</p>",
            attachments=[],
            is_read=False,
            folder="INBOX"
        )
        
        self.assertEqual(email.body_text, "")
        self.assertIn("<h1>", email.body_html)
    
    def test_email_text_only(self):
        """Test email with text content only"""
        email = Email(
            id="email_text_only",
            timestamp=datetime.now(),
            sender_email="sender@example.com",
            recipient_emails=["recipient@example.com"],
            subject="Text only email",
            body_text="This is plain text content only.",
            body_html="",
            attachments=[],
            is_read=False,
            folder="INBOX"
        )
        
        self.assertEqual(email.body_html, "")
        self.assertEqual(email.body_text, "This is plain text content only.")


class TestExtractionResult(unittest.TestCase):
    """Test cases for ExtractionResult model"""
    
    def test_extraction_result_success(self):
        """Test creating successful ExtractionResult"""
        output_paths = {
            "json": "/path/to/data.json",
            "csv": "/path/to/data.csv",
            "media": "/path/to/media/"
        }
        
        result = ExtractionResult(
            source="whatsapp",
            success=True,
            messages_count=25,
            media_count=8,
            errors=[],
            execution_time=45.7,
            output_paths=output_paths
        )
        
        self.assertEqual(result.source, "whatsapp")
        self.assertTrue(result.success)
        self.assertEqual(result.messages_count, 25)
        self.assertEqual(result.media_count, 8)
        self.assertEqual(len(result.errors), 0)
        self.assertEqual(result.execution_time, 45.7)
        self.assertEqual(result.output_paths, output_paths)
    
    def test_extraction_result_failure(self):
        """Test creating failed ExtractionResult"""
        errors = [
            "Authentication failed",
            "Network timeout",
            "Invalid response format"
        ]
        
        result = ExtractionResult(
            source="email",
            success=False,
            messages_count=0,
            media_count=0,
            errors=errors,
            execution_time=12.3,
            output_paths={}
        )
        
        self.assertEqual(result.source, "email")
        self.assertFalse(result.success)
        self.assertEqual(result.messages_count, 0)
        self.assertEqual(result.media_count, 0)
        self.assertEqual(len(result.errors), 3)
        self.assertIn("Authentication failed", result.errors)
        self.assertEqual(result.execution_time, 12.3)
        self.assertEqual(result.output_paths, {})
    
    def test_extraction_result_partial_success(self):
        """Test ExtractionResult with partial success (some errors but some data)"""
        errors = ["Failed to download 2 media files"]
        output_paths = {
            "json": "/path/to/data.json",
            "csv": "/path/to/data.csv"
        }
        
        result = ExtractionResult(
            source="whatsapp",
            success=True,  # Still considered success despite some errors
            messages_count=15,
            media_count=3,  # Some media downloaded successfully
            errors=errors,
            execution_time=30.2,
            output_paths=output_paths
        )
        
        self.assertTrue(result.success)
        self.assertEqual(result.messages_count, 15)
        self.assertEqual(result.media_count, 3)
        self.assertEqual(len(result.errors), 1)
        self.assertIn("Failed to download", result.errors[0])
    
    def test_extraction_result_zero_execution_time(self):
        """Test ExtractionResult with zero execution time"""
        result = ExtractionResult(
            source="test",
            success=True,
            messages_count=0,
            media_count=0,
            errors=[],
            execution_time=0.0,
            output_paths={}
        )
        
        self.assertEqual(result.execution_time, 0.0)
    
    def test_extraction_result_different_sources(self):
        """Test ExtractionResult with different source types"""
        sources = ["whatsapp", "email", "telegram", "slack"]
        
        for source in sources:
            result = ExtractionResult(
                source=source,
                success=True,
                messages_count=10,
                media_count=2,
                errors=[],
                execution_time=15.0,
                output_paths={}
            )
            
            self.assertEqual(result.source, source)


class TestBaseExtractor(unittest.TestCase):
    """Test cases for BaseExtractor abstract base class"""
    
    def test_base_extractor_cannot_be_instantiated(self):
        """Test that BaseExtractor cannot be instantiated directly"""
        with self.assertRaises(TypeError):
            BaseExtractor({})
    
    def test_concrete_extractor_implementation(self):
        """Test concrete implementation of BaseExtractor"""
        
        class TestExtractor(BaseExtractor):
            def authenticate(self) -> bool:
                self._authenticated = True
                return True
            
            def extract_data(self, **kwargs):
                if not self._authenticated:
                    return []
                return [{"id": "1", "content": "test"}]
            
            def save_data(self, data, output_path):
                pass
        
        config = {"test_key": "test_value"}
        extractor = TestExtractor(config)
        
        self.assertEqual(extractor.config, config)
        self.assertFalse(extractor._authenticated)
        self.assertFalse(extractor.is_authenticated)
        
        # Test authentication
        result = extractor.authenticate()
        self.assertTrue(result)
        self.assertTrue(extractor._authenticated)
        self.assertTrue(extractor.is_authenticated)
        
        # Test data extraction
        data = extractor.extract_data()
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]["id"], "1")
    
    def test_concrete_extractor_authentication_failure(self):
        """Test concrete extractor with authentication failure"""
        
        class FailingExtractor(BaseExtractor):
            def authenticate(self) -> bool:
                return False  # Always fails
            
            def extract_data(self, **kwargs):
                return []
            
            def save_data(self, data, output_path):
                pass
        
        extractor = FailingExtractor({})
        
        result = extractor.authenticate()
        self.assertFalse(result)
        self.assertFalse(extractor.is_authenticated)
    
    def test_concrete_extractor_with_kwargs(self):
        """Test concrete extractor that uses kwargs in extract_data"""
        
        class KwargsExtractor(BaseExtractor):
            def authenticate(self) -> bool:
                self._authenticated = True
                return True
            
            def extract_data(self, **kwargs):
                limit = kwargs.get('limit', 10)
                filter_type = kwargs.get('filter_type', 'all')
                
                data = []
                for i in range(limit):
                    data.append({
                        "id": str(i),
                        "type": filter_type,
                        "content": f"Message {i}"
                    })
                return data
            
            def save_data(self, data, output_path):
                pass
        
        extractor = KwargsExtractor({})
        extractor.authenticate()
        
        # Test with default parameters
        data = extractor.extract_data()
        self.assertEqual(len(data), 10)
        
        # Test with custom parameters
        data = extractor.extract_data(limit=5, filter_type='important')
        self.assertEqual(len(data), 5)
        self.assertEqual(data[0]['type'], 'important')
    
    def test_base_extractor_abstract_methods(self):
        """Test that all abstract methods must be implemented"""
        
        # Missing authenticate method
        class IncompleteExtractor1(BaseExtractor):
            def extract_data(self, **kwargs):
                return []
            
            def save_data(self, data, output_path):
                pass
        
        with self.assertRaises(TypeError):
            IncompleteExtractor1({})
        
        # Missing extract_data method
        class IncompleteExtractor2(BaseExtractor):
            def authenticate(self) -> bool:
                return True
            
            def save_data(self, data, output_path):
                pass
        
        with self.assertRaises(TypeError):
            IncompleteExtractor2({})
        
        # Missing save_data method
        class IncompleteExtractor3(BaseExtractor):
            def authenticate(self) -> bool:
                return True
            
            def extract_data(self, **kwargs):
                return []
        
        with self.assertRaises(TypeError):
            IncompleteExtractor3({})


class TestModelIntegration(unittest.TestCase):
    """Integration tests for model interactions"""
    
    def test_whatsapp_message_to_dict_conversion(self):
        """Test converting WhatsAppMessage to dictionary for storage"""
        message = WhatsAppMessage(
            id="msg_123",
            timestamp=datetime(2024, 1, 15, 10, 30, 0),
            sender_phone="+1234567890",
            message_content="Hello, world!",
            message_type="text",
            media_url="https://example.com/image.jpg",
            media_filename="image.jpg",
            media_size=1024
        )
        
        # Convert to dict (simulating what storage manager would do)
        message_dict = {
            'id': message.id,
            'timestamp': message.timestamp.isoformat(),
            'sender_phone': message.sender_phone,
            'message_content': message.message_content,
            'message_type': message.message_type,
            'media_url': message.media_url,
            'media_filename': message.media_filename,
            'media_size': message.media_size,
            'extracted_at': message.extracted_at.isoformat()
        }
        
        self.assertEqual(message_dict['id'], "msg_123")
        self.assertEqual(message_dict['sender_phone'], "+1234567890")
        self.assertIn('T', message_dict['timestamp'])  # ISO format
    
    def test_email_to_dict_conversion(self):
        """Test converting Email to dictionary for storage"""
        email = Email(
            id="email_123",
            timestamp=datetime(2024, 1, 15, 10, 30, 0),
            sender_email="sender@example.com",
            recipient_emails=["recipient@example.com"],
            subject="Test Subject",
            body_text="Plain text",
            body_html="<p>HTML</p>",
            attachments=[{"filename": "test.pdf", "size": 1024}],
            is_read=True,
            folder="INBOX"
        )
        
        # Convert to dict (simulating what storage manager would do)
        email_dict = {
            'id': email.id,
            'timestamp': email.timestamp.isoformat(),
            'sender_email': email.sender_email,
            'recipient_emails': email.recipient_emails,
            'subject': email.subject,
            'body_text': email.body_text,
            'body_html': email.body_html,
            'attachments': email.attachments,
            'is_read': email.is_read,
            'folder': email.folder,
            'extracted_at': email.extracted_at.isoformat()
        }
        
        self.assertEqual(email_dict['id'], "email_123")
        self.assertEqual(email_dict['sender_email'], "sender@example.com")
        self.assertTrue(email_dict['is_read'])
        self.assertEqual(len(email_dict['attachments']), 1)
    
    def test_extraction_result_summary(self):
        """Test creating summary from multiple ExtractionResults"""
        results = [
            ExtractionResult(
                source="whatsapp",
                success=True,
                messages_count=15,
                media_count=5,
                errors=[],
                execution_time=30.5,
                output_paths={"json": "/path/whatsapp.json"}
            ),
            ExtractionResult(
                source="email",
                success=True,
                messages_count=8,
                media_count=2,
                errors=["Minor warning"],
                execution_time=20.3,
                output_paths={"json": "/path/email.json"}
            ),
            ExtractionResult(
                source="telegram",
                success=False,
                messages_count=0,
                media_count=0,
                errors=["Authentication failed", "Connection timeout"],
                execution_time=5.1,
                output_paths={}
            )
        ]
        
        # Calculate summary statistics
        total_messages = sum(r.messages_count for r in results)
        total_media = sum(r.media_count for r in results)
        total_errors = sum(len(r.errors) for r in results)
        successful_sources = sum(1 for r in results if r.success)
        total_execution_time = sum(r.execution_time for r in results)
        
        self.assertEqual(total_messages, 23)
        self.assertEqual(total_media, 7)
        self.assertEqual(total_errors, 3)
        self.assertEqual(successful_sources, 2)
        self.assertAlmostEqual(total_execution_time, 55.9, places=1)


if __name__ == '__main__':
    unittest.main()