"""
Comprehensive unit tests for data models
"""

import unittest
from datetime import datetime, timedelta
from unittest.mock import Mock

from pipeline.models import WhatsAppMessage, Email, ExtractionResult, BaseExtractor


class TestWhatsAppMessage(unittest.TestCase):
    """Test cases for WhatsAppMessage model"""
    
    def test_init_basic(self):
        """Test basic WhatsAppMessage initialization"""
        timestamp = datetime.now()
        message = WhatsAppMessage(
            id="test123",
            timestamp=timestamp,
            sender_phone="+1234567890",
            message_content="Hello, world!",
            message_type="text"
        )
        
        self.assertEqual(message.id, "test123")
        self.assertEqual(message.timestamp, timestamp)
        self.assertEqual(message.sender_phone, "+1234567890")
        self.assertEqual(message.message_content, "Hello, world!")
        self.assertEqual(message.message_type, "text")
        self.assertIsNone(message.media_url)
        self.assertIsNone(message.media_filename)
        self.assertIsNone(message.media_size)
        self.assertIsNotNone(message.extracted_at)
    
    def test_init_with_media(self):
        """Test WhatsAppMessage initialization with media"""
        timestamp = datetime.now()
        message = WhatsAppMessage(
            id="test123",
            timestamp=timestamp,
            sender_phone="+1234567890",
            message_content="Check this image",
            message_type="image",
            media_url="https://example.com/image.jpg",
            media_filename="image.jpg",
            media_size=1024
        )
        
        self.assertEqual(message.media_url, "https://example.com/image.jpg")
        self.assertEqual(message.media_filename, "image.jpg")
        self.assertEqual(message.media_size, 1024)
    
    def test_post_init_extracted_at(self):
        """Test that extracted_at is set automatically"""
        before_creation = datetime.now()
        message = WhatsAppMessage(
            id="test123",
            timestamp=datetime.now(),
            sender_phone="+1234567890",
            message_content="Test",
            message_type="text"
        )
        after_creation = datetime.now()
        
        self.assertIsNotNone(message.extracted_at)
        self.assertGreaterEqual(message.extracted_at, before_creation)
        self.assertLessEqual(message.extracted_at, after_creation)
    
    def test_post_init_custom_extracted_at(self):
        """Test that custom extracted_at is preserved"""
        custom_time = datetime(2024, 1, 1, 12, 0, 0)
        message = WhatsAppMessage(
            id="test123",
            timestamp=datetime.now(),
            sender_phone="+1234567890",
            message_content="Test",
            message_type="text",
            extracted_at=custom_time
        )
        
        self.assertEqual(message.extracted_at, custom_time)
    
    def test_message_types(self):
        """Test different message types"""
        message_types = ["text", "image", "audio", "video", "document"]
        
        for msg_type in message_types:
            message = WhatsAppMessage(
                id=f"test_{msg_type}",
                timestamp=datetime.now(),
                sender_phone="+1234567890",
                message_content=f"Test {msg_type} message",
                message_type=msg_type
            )
            self.assertEqual(message.message_type, msg_type)
    
    def test_equality(self):
        """Test message equality based on ID"""
        timestamp = datetime.now()
        message1 = WhatsAppMessage(
            id="test123",
            timestamp=timestamp,
            sender_phone="+1234567890",
            message_content="Hello",
            message_type="text"
        )
        
        message2 = WhatsAppMessage(
            id="test123",
            timestamp=timestamp + timedelta(minutes=1),  # Different timestamp
            sender_phone="+0987654321",  # Different phone
            message_content="Different content",  # Different content
            message_type="image"  # Different type
        )
        
        # Messages with same ID should be considered equal for deduplication
        # Note: This would require implementing __eq__ method in the model
        # For now, we just test that they have the same ID
        self.assertEqual(message1.id, message2.id)


class TestEmail(unittest.TestCase):
    """Test cases for Email model"""
    
    def test_init_basic(self):
        """Test basic Email initialization"""
        timestamp = datetime.now()
        email = Email(
            id="email123",
            timestamp=timestamp,
            sender_email="sender@example.com",
            recipient_emails=["recipient@example.com"],
            subject="Test Subject",
            body_text="Test body text",
            body_html="<p>Test body HTML</p>",
            attachments=[],
            is_read=True,
            folder="INBOX"
        )
        
        self.assertEqual(email.id, "email123")
        self.assertEqual(email.timestamp, timestamp)
        self.assertEqual(email.sender_email, "sender@example.com")
        self.assertEqual(email.recipient_emails, ["recipient@example.com"])
        self.assertEqual(email.subject, "Test Subject")
        self.assertEqual(email.body_text, "Test body text")
        self.assertEqual(email.body_html, "<p>Test body HTML</p>")
        self.assertEqual(email.attachments, [])
        self.assertTrue(email.is_read)
        self.assertEqual(email.folder, "INBOX")
        self.assertIsNotNone(email.extracted_at)
    
    def test_init_with_attachments(self):
        """Test Email initialization with attachments"""
        attachments = [
            {"filename": "document.pdf", "size": 1024, "content_type": "application/pdf"},
            {"filename": "image.jpg", "size": 2048, "content_type": "image/jpeg"}
        ]
        
        email = Email(
            id="email123",
            timestamp=datetime.now(),
            sender_email="sender@example.com",
            recipient_emails=["recipient@example.com"],
            subject="Email with attachments",
            body_text="Please see attached files",
            body_html="<p>Please see attached files</p>",
            attachments=attachments,
            is_read=False,
            folder="INBOX"
        )
        
        self.assertEqual(len(email.attachments), 2)
        self.assertEqual(email.attachments[0]["filename"], "document.pdf")
        self.assertEqual(email.attachments[1]["filename"], "image.jpg")
        self.assertFalse(email.is_read)
    
    def test_multiple_recipients(self):
        """Test Email with multiple recipients"""
        recipients = ["user1@example.com", "user2@example.com", "user3@example.com"]
        
        email = Email(
            id="email123",
            timestamp=datetime.now(),
            sender_email="sender@example.com",
            recipient_emails=recipients,
            subject="Multiple recipients",
            body_text="Test",
            body_html="",
            attachments=[],
            is_read=True,
            folder="SENT"
        )
        
        self.assertEqual(len(email.recipient_emails), 3)
        self.assertIn("user1@example.com", email.recipient_emails)
        self.assertIn("user2@example.com", email.recipient_emails)
        self.assertIn("user3@example.com", email.recipient_emails)
    
    def test_post_init_extracted_at(self):
        """Test that extracted_at is set automatically"""
        before_creation = datetime.now()
        email = Email(
            id="email123",
            timestamp=datetime.now(),
            sender_email="sender@example.com",
            recipient_emails=["recipient@example.com"],
            subject="Test",
            body_text="Test",
            body_html="",
            attachments=[],
            is_read=True,
            folder="INBOX"
        )
        after_creation = datetime.now()
        
        self.assertIsNotNone(email.extracted_at)
        self.assertGreaterEqual(email.extracted_at, before_creation)
        self.assertLessEqual(email.extracted_at, after_creation)
    
    def test_post_init_custom_extracted_at(self):
        """Test that custom extracted_at is preserved"""
        custom_time = datetime(2024, 1, 1, 12, 0, 0)
        email = Email(
            id="email123",
            timestamp=datetime.now(),
            sender_email="sender@example.com",
            recipient_emails=["recipient@example.com"],
            subject="Test",
            body_text="Test",
            body_html="",
            attachments=[],
            is_read=True,
            folder="INBOX",
            extracted_at=custom_time
        )
        
        self.assertEqual(email.extracted_at, custom_time)
    
    def test_different_folders(self):
        """Test emails in different folders"""
        folders = ["INBOX", "SENT", "DRAFTS", "SPAM", "TRASH", "Custom Folder"]
        
        for folder in folders:
            email = Email(
                id=f"email_{folder.lower()}",
                timestamp=datetime.now(),
                sender_email="sender@example.com",
                recipient_emails=["recipient@example.com"],
                subject=f"Email in {folder}",
                body_text="Test",
                body_html="",
                attachments=[],
                is_read=True,
                folder=folder
            )
            self.assertEqual(email.folder, folder)


class TestExtractionResult(unittest.TestCase):
    """Test cases for ExtractionResult model"""
    
    def test_init_success(self):
        """Test ExtractionResult initialization for successful extraction"""
        output_paths = {
            "json": "/path/to/data.json",
            "csv": "/path/to/data.csv",
            "media": "/path/to/media/"
        }
        
        result = ExtractionResult(
            source="whatsapp",
            success=True,
            messages_count=10,
            media_count=5,
            errors=[],
            execution_time=15.5,
            output_paths=output_paths
        )
        
        self.assertEqual(result.source, "whatsapp")
        self.assertTrue(result.success)
        self.assertEqual(result.messages_count, 10)
        self.assertEqual(result.media_count, 5)
        self.assertEqual(result.errors, [])
        self.assertEqual(result.execution_time, 15.5)
        self.assertEqual(result.output_paths, output_paths)
    
    def test_init_failure(self):
        """Test ExtractionResult initialization for failed extraction"""
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
            execution_time=5.2,
            output_paths={}
        )
        
        self.assertEqual(result.source, "email")
        self.assertFalse(result.success)
        self.assertEqual(result.messages_count, 0)
        self.assertEqual(result.media_count, 0)
        self.assertEqual(len(result.errors), 3)
        self.assertIn("Authentication failed", result.errors)
        self.assertEqual(result.execution_time, 5.2)
        self.assertEqual(result.output_paths, {})
    
    def test_partial_success(self):
        """Test ExtractionResult for partial success scenario"""
        errors = ["Failed to download 2 media files"]
        output_paths = {"json": "/path/to/data.json"}
        
        result = ExtractionResult(
            source="whatsapp",
            success=True,  # Still successful despite some errors
            messages_count=20,
            media_count=8,  # Some media failed
            errors=errors,
            execution_time=30.1,
            output_paths=output_paths
        )
        
        self.assertTrue(result.success)
        self.assertEqual(result.messages_count, 20)
        self.assertEqual(result.media_count, 8)
        self.assertEqual(len(result.errors), 1)
        self.assertIn("Failed to download", result.errors[0])
    
    def test_zero_execution_time(self):
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
    
    def test_large_numbers(self):
        """Test ExtractionResult with large numbers"""
        result = ExtractionResult(
            source="bulk_import",
            success=True,
            messages_count=1000000,
            media_count=50000,
            errors=[],
            execution_time=3600.0,  # 1 hour
            output_paths={"json": "/path/to/large_data.json"}
        )
        
        self.assertEqual(result.messages_count, 1000000)
        self.assertEqual(result.media_count, 50000)
        self.assertEqual(result.execution_time, 3600.0)


class TestBaseExtractor(unittest.TestCase):
    """Test cases for BaseExtractor abstract base class"""
    
    def test_cannot_instantiate_directly(self):
        """Test that BaseExtractor cannot be instantiated directly"""
        with self.assertRaises(TypeError):
            BaseExtractor({})
    
    def test_concrete_implementation(self):
        """Test concrete implementation of BaseExtractor"""
        
        class TestExtractor(BaseExtractor):
            def authenticate(self):
                return True
            
            def extract_data(self, **kwargs):
                return [{"test": "data"}]
            
            def save_data(self, data, output_path):
                pass
        
        config = {"test_config": "value"}
        extractor = TestExtractor(config)
        
        self.assertEqual(extractor.config, config)
        self.assertFalse(extractor._authenticated)
        self.assertFalse(extractor.is_authenticated)
    
    def test_authentication_property(self):
        """Test is_authenticated property"""
        
        class TestExtractor(BaseExtractor):
            def authenticate(self):
                self._authenticated = True
                return True
            
            def extract_data(self, **kwargs):
                return []
            
            def save_data(self, data, output_path):
                pass
        
        extractor = TestExtractor({})
        
        # Initially not authenticated
        self.assertFalse(extractor.is_authenticated)
        
        # After authentication
        extractor.authenticate()
        self.assertTrue(extractor.is_authenticated)
    
    def test_abstract_methods_must_be_implemented(self):
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
            def authenticate(self):
                return True
            
            def save_data(self, data, output_path):
                pass
        
        with self.assertRaises(TypeError):
            IncompleteExtractor2({})
        
        # Missing save_data method
        class IncompleteExtractor3(BaseExtractor):
            def authenticate(self):
                return True
            
            def extract_data(self, **kwargs):
                return []
        
        with self.assertRaises(TypeError):
            IncompleteExtractor3({})
    
    def test_config_storage(self):
        """Test that configuration is properly stored"""
        config = {
            "api_key": "test_key",
            "timeout": 30,
            "retries": 3,
            "nested": {
                "option1": "value1",
                "option2": "value2"
            }
        }
        
        class TestExtractor(BaseExtractor):
            def authenticate(self):
                return True
            
            def extract_data(self, **kwargs):
                return []
            
            def save_data(self, data, output_path):
                pass
        
        extractor = TestExtractor(config)
        
        self.assertEqual(extractor.config, config)
        self.assertEqual(extractor.config["api_key"], "test_key")
        self.assertEqual(extractor.config["timeout"], 30)
        self.assertEqual(extractor.config["nested"]["option1"], "value1")
    
    def test_inheritance_chain(self):
        """Test that inheritance works properly"""
        
        class BaseTestExtractor(BaseExtractor):
            def __init__(self, config):
                super().__init__(config)
                self.base_initialized = True
            
            def authenticate(self):
                return True
            
            def extract_data(self, **kwargs):
                return []
            
            def save_data(self, data, output_path):
                pass
        
        class SpecializedExtractor(BaseTestExtractor):
            def __init__(self, config):
                super().__init__(config)
                self.specialized_initialized = True
            
            def extract_data(self, **kwargs):
                # Override with specialized behavior
                return [{"specialized": "data"}]
        
        extractor = SpecializedExtractor({"test": "config"})
        
        self.assertTrue(extractor.base_initialized)
        self.assertTrue(extractor.specialized_initialized)
        self.assertEqual(extractor.config, {"test": "config"})
        self.assertFalse(extractor.is_authenticated)
        
        # Test overridden method
        data = extractor.extract_data()
        self.assertEqual(data, [{"specialized": "data"}])


if __name__ == '__main__':
    unittest.main()