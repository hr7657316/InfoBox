"""
Unit tests for data models
"""

import unittest
from datetime import datetime
from pipeline.models import WhatsAppMessage, Email, ExtractionResult, BaseExtractor


class TestWhatsAppMessage(unittest.TestCase):
    """Test cases for WhatsAppMessage data model"""
    
    def test_init_with_all_fields(self):
        """Test WhatsAppMessage initialization with all fields"""
        timestamp = datetime(2024, 1, 1, 12, 0, 0)
        extracted_at = datetime(2024, 1, 1, 12, 5, 0)
        
        message = WhatsAppMessage(
            id="msg_123",
            timestamp=timestamp,
            sender_phone="+1234567890",
            message_content="Hello, world!",
            message_type="text",
            media_url="https://example.com/media.jpg",
            media_filename="image.jpg",
            media_size=1024,
            extracted_at=extracted_at
        )
        
        self.assertEqual(message.id, "msg_123")
        self.assertEqual(message.timestamp, timestamp)
        self.assertEqual(message.sender_phone, "+1234567890")
        self.assertEqual(message.message_content, "Hello, world!")
        self.assertEqual(message.message_type, "text")
        self.assertEqual(message.media_url, "https://example.com/media.jpg")
        self.assertEqual(message.media_filename, "image.jpg")
        self.assertEqual(message.media_size, 1024)
        self.assertEqual(message.extracted_at, extracted_at)
    
    def test_init_with_required_fields_only(self):
        """Test WhatsAppMessage initialization with required fields only"""
        timestamp = datetime(2024, 1, 1, 12, 0, 0)
        
        message = WhatsAppMessage(
            id="msg_456",
            timestamp=timestamp,
            sender_phone="+1234567890",
            message_content="Test message",
            message_type="text"
        )
        
        self.assertEqual(message.id, "msg_456")
        self.assertEqual(message.timestamp, timestamp)
        self.assertEqual(message.sender_phone, "+1234567890")
        self.assertEqual(message.message_content, "Test message")
        self.assertEqual(message.message_type, "text")
        self.assertIsNone(message.media_url)
        self.assertIsNone(message.media_filename)
        self.assertIsNone(message.media_size)
        self.assertIsNotNone(message.extracted_at)  # Should be auto-set
    
    def test_post_init_sets_extracted_at(self):
        """Test that __post_init__ sets extracted_at if not provided"""
        before_creation = datetime.now()
        
        message = WhatsAppMessage(
            id="msg_789",
            timestamp=datetime(2024, 1, 1, 12, 0, 0),
            sender_phone="+1234567890",
            message_content="Test",
            message_type="text"
        )
        
        after_creation = datetime.now()
        
        self.assertIsNotNone(message.extracted_at)
        self.assertGreaterEqual(message.extracted_at, before_creation)
        self.assertLessEqual(message.extracted_at, after_creation)
    
    def test_post_init_preserves_extracted_at(self):
        """Test that __post_init__ preserves extracted_at if provided"""
        custom_extracted_at = datetime(2024, 1, 1, 10, 0, 0)
        
        message = WhatsAppMessage(
            id="msg_custom",
            timestamp=datetime(2024, 1, 1, 12, 0, 0),
            sender_phone="+1234567890",
            message_content="Test",
            message_type="text",
            extracted_at=custom_extracted_at
        )
        
        self.assertEqual(message.extracted_at, custom_extracted_at)


class TestEmail(unittest.TestCase):
    """Test cases for Email data model"""
    
    def test_init_with_all_fields(self):
        """Test Email initialization with all fields"""
        timestamp = datetime(2024, 1, 1, 12, 0, 0)
        extracted_at = datetime(2024, 1, 1, 12, 5, 0)
        recipient_emails = ["user1@example.com", "user2@example.com"]
        attachments = [
            {"filename": "doc.pdf", "size": 1024, "content_type": "application/pdf"},
            {"filename": "image.jpg", "size": 2048, "content_type": "image/jpeg"}
        ]
        
        email = Email(
            id="email_123",
            timestamp=timestamp,
            sender_email="sender@example.com",
            recipient_emails=recipient_emails,
            subject="Test Subject",
            body_text="Plain text body",
            body_html="<p>HTML body</p>",
            attachments=attachments,
            is_read=True,
            folder="INBOX",
            extracted_at=extracted_at
        )
        
        self.assertEqual(email.id, "email_123")
        self.assertEqual(email.timestamp, timestamp)
        self.assertEqual(email.sender_email, "sender@example.com")
        self.assertEqual(email.recipient_emails, recipient_emails)
        self.assertEqual(email.subject, "Test Subject")
        self.assertEqual(email.body_text, "Plain text body")
        self.assertEqual(email.body_html, "<p>HTML body</p>")
        self.assertEqual(email.attachments, attachments)
        self.assertTrue(email.is_read)
        self.assertEqual(email.folder, "INBOX")
        self.assertEqual(email.extracted_at, extracted_at)
    
    def test_init_with_required_fields_only(self):
        """Test Email initialization with required fields only"""
        timestamp = datetime(2024, 1, 1, 12, 0, 0)
        
        email = Email(
            id="email_456",
            timestamp=timestamp,
            sender_email="sender@example.com",
            recipient_emails=["recipient@example.com"],
            subject="Test Subject",
            body_text="Plain text",
            body_html="<p>HTML</p>",
            attachments=[],
            is_read=False,
            folder="INBOX"
        )
        
        self.assertEqual(email.id, "email_456")
        self.assertEqual(email.timestamp, timestamp)
        self.assertEqual(email.sender_email, "sender@example.com")
        self.assertEqual(email.recipient_emails, ["recipient@example.com"])
        self.assertEqual(email.subject, "Test Subject")
        self.assertEqual(email.body_text, "Plain text")
        self.assertEqual(email.body_html, "<p>HTML</p>")
        self.assertEqual(email.attachments, [])
        self.assertFalse(email.is_read)
        self.assertEqual(email.folder, "INBOX")
        self.assertIsNotNone(email.extracted_at)  # Should be auto-set
    
    def test_post_init_sets_extracted_at(self):
        """Test that __post_init__ sets extracted_at if not provided"""
        before_creation = datetime.now()
        
        email = Email(
            id="email_789",
            timestamp=datetime(2024, 1, 1, 12, 0, 0),
            sender_email="sender@example.com",
            recipient_emails=["recipient@example.com"],
            subject="Test",
            body_text="Text",
            body_html="<p>HTML</p>",
            attachments=[],
            is_read=False,
            folder="INBOX"
        )
        
        after_creation = datetime.now()
        
        self.assertIsNotNone(email.extracted_at)
        self.assertGreaterEqual(email.extracted_at, before_creation)
        self.assertLessEqual(email.extracted_at, after_creation)
    
    def test_post_init_preserves_extracted_at(self):
        """Test that __post_init__ preserves extracted_at if provided"""
        custom_extracted_at = datetime(2024, 1, 1, 10, 0, 0)
        
        email = Email(
            id="email_custom",
            timestamp=datetime(2024, 1, 1, 12, 0, 0),
            sender_email="sender@example.com",
            recipient_emails=["recipient@example.com"],
            subject="Test",
            body_text="Text",
            body_html="<p>HTML</p>",
            attachments=[],
            is_read=False,
            folder="INBOX",
            extracted_at=custom_extracted_at
        )
        
        self.assertEqual(email.extracted_at, custom_extracted_at)


class TestExtractionResult(unittest.TestCase):
    """Test cases for ExtractionResult data model"""
    
    def test_init_successful_result(self):
        """Test ExtractionResult initialization for successful extraction"""
        output_paths = {
            "json": "/data/whatsapp/2024-01-01/messages.json",
            "csv": "/data/whatsapp/2024-01-01/messages.csv",
            "media": "/data/whatsapp/2024-01-01/media"
        }
        
        result = ExtractionResult(
            source="whatsapp",
            success=True,
            messages_count=25,
            media_count=10,
            errors=[],
            execution_time=45.5,
            output_paths=output_paths
        )
        
        self.assertEqual(result.source, "whatsapp")
        self.assertTrue(result.success)
        self.assertEqual(result.messages_count, 25)
        self.assertEqual(result.media_count, 10)
        self.assertEqual(result.errors, [])
        self.assertEqual(result.execution_time, 45.5)
        self.assertEqual(result.output_paths, output_paths)
    
    def test_init_failed_result(self):
        """Test ExtractionResult initialization for failed extraction"""
        errors = ["Authentication failed", "Network timeout"]
        
        result = ExtractionResult(
            source="email",
            success=False,
            messages_count=0,
            media_count=0,
            errors=errors,
            execution_time=10.2,
            output_paths={}
        )
        
        self.assertEqual(result.source, "email")
        self.assertFalse(result.success)
        self.assertEqual(result.messages_count, 0)
        self.assertEqual(result.media_count, 0)
        self.assertEqual(result.errors, errors)
        self.assertEqual(result.execution_time, 10.2)
        self.assertEqual(result.output_paths, {})
    
    def test_init_partial_success_result(self):
        """Test ExtractionResult initialization for partial success"""
        errors = ["Failed to download 2 media files"]
        output_paths = {"json": "/data/email/2024-01-01/messages.json"}
        
        result = ExtractionResult(
            source="email",
            success=True,  # Still successful despite some errors
            messages_count=50,
            media_count=8,  # Some media failed
            errors=errors,
            execution_time=120.0,
            output_paths=output_paths
        )
        
        self.assertEqual(result.source, "email")
        self.assertTrue(result.success)
        self.assertEqual(result.messages_count, 50)
        self.assertEqual(result.media_count, 8)
        self.assertEqual(result.errors, errors)
        self.assertEqual(result.execution_time, 120.0)
        self.assertEqual(result.output_paths, output_paths)


class TestBaseExtractor(unittest.TestCase):
    """Test cases for BaseExtractor abstract base class"""
    
    def setUp(self):
        """Set up test fixtures"""
        # Create a concrete implementation for testing
        class TestExtractor(BaseExtractor):
            def authenticate(self):
                return True
            
            def extract_data(self, **kwargs):
                return [{"id": "1", "content": "test"}]
            
            def save_data(self, data, output_path):
                pass
        
        self.TestExtractor = TestExtractor
    
    def test_init(self):
        """Test BaseExtractor initialization"""
        config = {"api_key": "test_key", "timeout": 30}
        extractor = self.TestExtractor(config)
        
        self.assertEqual(extractor.config, config)
        self.assertFalse(extractor._authenticated)
    
    def test_is_authenticated_property(self):
        """Test is_authenticated property"""
        config = {"api_key": "test_key"}
        extractor = self.TestExtractor(config)
        
        # Initially not authenticated
        self.assertFalse(extractor.is_authenticated)
        
        # Set authenticated state
        extractor._authenticated = True
        self.assertTrue(extractor.is_authenticated)
        
        # Reset authenticated state
        extractor._authenticated = False
        self.assertFalse(extractor.is_authenticated)
    
    def test_abstract_methods_implemented(self):
        """Test that concrete implementation provides all abstract methods"""
        config = {"api_key": "test_key"}
        extractor = self.TestExtractor(config)
        
        # Should be able to call all abstract methods
        self.assertTrue(extractor.authenticate())
        self.assertEqual(extractor.extract_data(), [{"id": "1", "content": "test"}])
        extractor.save_data([], "/tmp/test")  # Should not raise
    
    def test_cannot_instantiate_abstract_class(self):
        """Test that BaseExtractor cannot be instantiated directly"""
        with self.assertRaises(TypeError):
            BaseExtractor({"config": "test"})
    
    def test_missing_abstract_method_raises_error(self):
        """Test that missing abstract method implementation raises TypeError"""
        # Create incomplete implementation
        class IncompleteExtractor(BaseExtractor):
            def authenticate(self):
                return True
            # Missing extract_data and save_data methods
        
        with self.assertRaises(TypeError):
            IncompleteExtractor({"config": "test"})


if __name__ == '__main__':
    unittest.main()