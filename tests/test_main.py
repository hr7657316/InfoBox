"""
Unit tests for main pipeline orchestrator
"""

import unittest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime
import tempfile
import os

from pipeline.main import PipelineOrchestrator
from pipeline.models import ExtractionResult


class TestPipelineOrchestrator(unittest.TestCase):
    """Test cases for PipelineOrchestrator class"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.temp_dir = tempfile.mkdtemp()
        self.config_file = os.path.join(self.temp_dir, 'test_config.yaml')
        
        # Create a basic config file
        config_content = """
whatsapp:
  api_token: test_token
  phone_number_id: test_phone_id

email:
  accounts:
    - email: test@example.com
      password: test_password
      imap_server: imap.example.com

storage:
  base_path: ./test_data

logging:
  level: INFO
"""
        with open(self.config_file, 'w') as f:
            f.write(config_content)
        
        self.orchestrator = PipelineOrchestrator(self.config_file)
    
    def tearDown(self):
        """Clean up test fixtures"""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_init(self):
        """Test PipelineOrchestrator initialization"""
        self.assertEqual(self.orchestrator.config_path, self.config_file)
        self.assertIsNotNone(self.orchestrator.config_manager)
        self.assertIsNone(self.orchestrator.logger)
        self.assertIsNone(self.orchestrator.error_handler)
        self.assertIsNone(self.orchestrator.storage_manager)
        self.assertEqual(self.orchestrator.whatsapp_extractors, [])
        self.assertEqual(self.orchestrator.email_extractors, [])
        self.assertFalse(self.orchestrator._initialized)
    
    def test_init_with_default_config(self):
        """Test initialization with default config path"""
        orchestrator = PipelineOrchestrator()
        self.assertEqual(orchestrator.config_path, "config.yaml")
    
    @patch('pipeline.main.PipelineLogger')
    @patch('pipeline.main.ErrorHandler')
    @patch('pipeline.main.StorageManager')
    def test_initialize_success(self, mock_storage, mock_error_handler, mock_logger):
        """Test successful initialization"""
        # Mock the components
        mock_logger_instance = Mock()
        mock_logger.return_value = mock_logger_instance
        
        mock_error_handler_instance = Mock()
        mock_error_handler.return_value = mock_error_handler_instance
        
        mock_storage_instance = Mock()
        mock_storage.return_value = mock_storage_instance
        
        # Mock validation to pass
        with patch.object(self.orchestrator, '_validate_configuration', return_value=[]):
            with patch.object(self.orchestrator, '_setup_extractors'):
                result = self.orchestrator.initialize()
        
        self.assertTrue(result)
        self.assertTrue(self.orchestrator._initialized)
        self.assertIsNotNone(self.orchestrator.logger)
        self.assertIsNotNone(self.orchestrator.error_handler)
        self.assertIsNotNone(self.orchestrator.storage_manager)
        
        # Verify setup calls
        mock_logger_instance.setup_logging.assert_called_once()
    
    @patch('pipeline.main.PipelineLogger')
    def test_initialize_validation_failure(self, mock_logger):
        """Test initialization with validation errors"""
        mock_logger_instance = Mock()
        mock_logger.return_value = mock_logger_instance
        
        # Mock validation to fail
        validation_errors = ["Missing API token", "Invalid storage path"]
        with patch.object(self.orchestrator, '_validate_configuration', return_value=validation_errors):
            result = self.orchestrator.initialize()
        
        self.assertFalse(result)
        self.assertFalse(self.orchestrator._initialized)
    
    @patch('pipeline.main.PipelineLogger')
    def test_initialize_exception_handling(self, mock_logger):
        """Test initialization with exception"""
        # Mock logger to raise exception
        mock_logger.side_effect = Exception("Logger initialization failed")
        
        result = self.orchestrator.initialize()
        
        self.assertFalse(result)
        self.assertFalse(self.orchestrator._initialized)
    
    @patch('pipeline.main.WhatsAppExtractor')
    @patch('pipeline.main.EmailExtractor')
    def test_setup_extractors_success(self, mock_email_extractor, mock_whatsapp_extractor):
        """Test successful extractor setup"""
        # Initialize required components first
        self.orchestrator.logger = Mock()
        self.orchestrator.error_handler = Mock()
        
        # Mock config manager methods
        self.orchestrator.config_manager = Mock()
        self.orchestrator.config_manager.get_whatsapp_configs.return_value = [{'api_token': 'test_token'}]
        self.orchestrator.config_manager.get_email_configs.return_value = [{'email': 'test@example.com'}]
        
        # Mock extractor instances
        mock_whatsapp_instance = Mock()
        mock_whatsapp_extractor.return_value = mock_whatsapp_instance
        
        mock_email_instance = Mock()
        mock_email_extractor.return_value = mock_email_instance
        
        self.orchestrator._setup_extractors()
        
        self.assertEqual(len(self.orchestrator.whatsapp_extractors), 1)
        self.assertEqual(self.orchestrator.whatsapp_extractors[0], mock_whatsapp_instance)
        self.assertEqual(len(self.orchestrator.email_extractors), 1)
        self.assertEqual(self.orchestrator.email_extractors[0], mock_email_instance)
    
    @patch('pipeline.main.WhatsAppExtractor')
    def test_setup_extractors_whatsapp_failure(self, mock_whatsapp_extractor):
        """Test extractor setup with WhatsApp failure"""
        # Initialize required components first
        self.orchestrator.logger = Mock()
        self.orchestrator.error_handler = Mock()
        
        # Mock config manager methods
        self.orchestrator.config_manager = Mock()
        self.orchestrator.config_manager.get_whatsapp_configs.return_value = [{'api_token': 'test_token'}]
        self.orchestrator.config_manager.get_email_configs.return_value = []
        
        # Mock WhatsApp extractor to raise exception
        mock_whatsapp_extractor.side_effect = Exception("WhatsApp setup failed")
        
        self.orchestrator._setup_extractors()
        
        self.assertEqual(self.orchestrator.whatsapp_extractors, [])
        self.orchestrator.error_handler.handle_error.assert_called()
    
    def test_validate_configuration_valid(self):
        """Test configuration validation with valid config"""
        # Mock config manager validation
        with patch.object(self.orchestrator.config_manager, 'validate_config', return_value=[]):
            with patch('os.makedirs'):  # Mock directory creation
                errors = self.orchestrator._validate_configuration()
        
        self.assertEqual(errors, [])
    
    def test_validate_configuration_config_errors(self):
        """Test configuration validation with config manager errors"""
        config_errors = ["Missing API token", "Invalid email configuration"]
        
        with patch.object(self.orchestrator.config_manager, 'validate_config', return_value=config_errors):
            errors = self.orchestrator._validate_configuration()
        
        self.assertEqual(errors, config_errors)
    
    def test_validate_configuration_no_data_sources(self):
        """Test configuration validation with no data sources"""
        # Create config without data sources
        empty_config = {}
        
        with patch.object(self.orchestrator.config_manager, 'validate_config', return_value=[]):
            with patch.object(self.orchestrator.config_manager, 'load_config', return_value=empty_config):
                errors = self.orchestrator._validate_configuration()
        
        self.assertTrue(any("at least one data source" in error.lower() for error in errors))
    
    def test_validate_configuration_storage_error(self):
        """Test configuration validation with storage directory error"""
        with patch.object(self.orchestrator.config_manager, 'validate_config', return_value=[]):
            with patch('os.makedirs', side_effect=PermissionError("Permission denied")):
                errors = self.orchestrator._validate_configuration()
        
        self.assertTrue(any("cannot create storage directory" in error.lower() for error in errors))
    
    def test_run_extraction_not_initialized(self):
        """Test run_extraction when not initialized"""
        with patch.object(self.orchestrator, 'initialize', return_value=False):
            results = self.orchestrator.run_extraction()
        
        self.assertEqual(results, {})
    
    @patch('pipeline.main.datetime')
    def test_run_extraction_success(self, mock_datetime):
        """Test successful extraction run"""
        # Mock datetime for consistent timing
        start_time = datetime(2024, 1, 1, 12, 0, 0)
        end_time = datetime(2024, 1, 1, 12, 1, 0)
        mock_datetime.now.side_effect = [start_time, end_time, end_time]
        
        # Setup mocks
        self.orchestrator._initialized = True
        self.orchestrator.logger = Mock()
        self.orchestrator.error_handler = Mock()
        self.orchestrator.error_handler.get_error_summary.return_value = {'total_errors': 0}
        
        # Mock extractors
        self.orchestrator.whatsapp_extractors = [Mock()]
        self.orchestrator.email_extractors = [Mock()]
        
        # Mock extraction methods
        whatsapp_result = ExtractionResult(
            source='whatsapp', success=True, messages_count=10, media_count=5,
            errors=[], execution_time=30.0, output_paths={}
        )
        email_result = ExtractionResult(
            source='email', success=True, messages_count=20, media_count=3,
            errors=[], execution_time=25.0, output_paths={}
        )
        
        with patch.object(self.orchestrator, '_extract_from_whatsapp', return_value=whatsapp_result):
            with patch.object(self.orchestrator, '_extract_from_email', return_value=email_result):
                results = self.orchestrator.run_extraction()
        
        self.assertEqual(len(results), 2)
        self.assertIn('whatsapp', results)
        self.assertIn('email', results)
        self.assertTrue(results['whatsapp'].success)
        self.assertTrue(results['email'].success)
    
    def test_run_extraction_whatsapp_failure(self):
        """Test extraction run with WhatsApp failure"""
        self.orchestrator._initialized = True
        self.orchestrator.logger = Mock()
        self.orchestrator.error_handler = Mock()
        self.orchestrator.error_handler.get_error_summary.return_value = {'total_errors': 1}
        
        # Mock WhatsApp extractor to exist but fail
        self.orchestrator.whatsapp_extractors = [Mock()]
        self.orchestrator.email_extractors = []
        
        # Mock extraction method to raise exception
        with patch.object(self.orchestrator, '_extract_from_whatsapp', side_effect=Exception("WhatsApp failed")):
            results = self.orchestrator.run_extraction()
        
        self.assertEqual(len(results), 1)
        self.assertIn('whatsapp', results)
        self.assertFalse(results['whatsapp'].success)
        self.assertIn("WhatsApp failed", results['whatsapp'].errors)
    
    def test_extract_from_whatsapp_success(self):
        """Test successful WhatsApp extraction"""
        # Setup mocks
        self.orchestrator.error_handler = Mock()
        self.orchestrator.storage_manager = Mock()
        self.orchestrator.storage_manager.get_media_directory.return_value = '/tmp/media'
        self.orchestrator.storage_manager.save_whatsapp_data.return_value = {'json': '/tmp/data.json'}
        
        mock_extractor = Mock()
        mock_extractor.authenticate.return_value = True
        
        # Mock messages with and without media
        from pipeline.models import WhatsAppMessage
        messages = [
            WhatsAppMessage(
                id="1", timestamp=datetime.now(), sender_phone="+1234567890",
                message_content="Text message", message_type="text"
            ),
            WhatsAppMessage(
                id="2", timestamp=datetime.now(), sender_phone="+1234567890",
                message_content="Image message", message_type="image",
                media_url="https://example.com/image.jpg", media_filename="image.jpg"
            )
        ]
        mock_extractor.extract_messages.return_value = messages
        mock_extractor.download_media.return_value = "/tmp/media/image.jpg"
        
        self.orchestrator.whatsapp_extractors = [mock_extractor]
        
        result = self.orchestrator._extract_from_whatsapp()
        
        self.assertTrue(result.success)
        self.assertEqual(result.source, 'whatsapp')
        self.assertEqual(result.messages_count, 2)
        self.assertEqual(result.media_count, 1)
        self.assertEqual(len(result.errors), 0)
    
    def test_extract_from_whatsapp_auth_failure(self):
        """Test WhatsApp extraction with authentication failure"""
        self.orchestrator.error_handler = Mock()
        
        mock_extractor = Mock()
        mock_extractor.authenticate.return_value = False
        self.orchestrator.whatsapp_extractors = [mock_extractor]
        
        result = self.orchestrator._extract_from_whatsapp()
        
        # With multi-account support, if all accounts fail auth and no messages are extracted, 
        # the result should be unsuccessful
        self.assertFalse(result.success)  # Should be False when auth fails and no messages
        self.assertEqual(result.source, 'whatsapp')
        self.assertEqual(result.messages_count, 0)
        self.assertIn("WhatsApp authentication failed for account 1", result.errors)
    
    def test_extract_from_whatsapp_media_download_failure(self):
        """Test WhatsApp extraction with media download failure"""
        # Setup mocks
        self.orchestrator.error_handler = Mock()
        self.orchestrator.storage_manager = Mock()
        self.orchestrator.storage_manager.get_media_directory.return_value = '/tmp/media'
        self.orchestrator.storage_manager.save_whatsapp_data.return_value = {'json': '/tmp/data.json'}
        
        mock_extractor = Mock()
        mock_extractor.authenticate.return_value = True
        
        # Mock message with media
        from pipeline.models import WhatsAppMessage
        message = WhatsAppMessage(
            id="1", timestamp=datetime.now(), sender_phone="+1234567890",
            message_content="Image message", message_type="image",
            media_url="https://example.com/image.jpg", media_filename="image.jpg"
        )
        mock_extractor.extract_messages.return_value = [message]
        mock_extractor.download_media.side_effect = Exception("Download failed")
        
        self.orchestrator.whatsapp_extractors = [mock_extractor]
        
        result = self.orchestrator._extract_from_whatsapp()
        
        # Should still be successful overall, but with errors
        self.assertTrue(result.success)
        self.assertEqual(result.messages_count, 1)
        self.assertEqual(result.media_count, 0)
        self.assertEqual(len(result.errors), 1)
        self.assertIn("Failed to download media", result.errors[0])
    
    def test_extract_from_email_success(self):
        """Test successful email extraction"""
        # Setup mocks
        self.orchestrator.error_handler = Mock()
        self.orchestrator.storage_manager = Mock()
        self.orchestrator.storage_manager.save_email_data.return_value = {'json': '/tmp/emails.json'}
        
        mock_extractor = Mock()
        mock_extractor.authenticate.return_value = True
        
        # Mock emails with attachments
        from pipeline.models import Email
        emails = [
            Email(
                id="1", timestamp=datetime.now(), sender_email="sender@example.com",
                recipient_emails=["recipient@example.com"], subject="Test 1",
                body_text="Text", body_html="<p>HTML</p>", attachments=[],
                is_read=False, folder="INBOX"
            ),
            Email(
                id="2", timestamp=datetime.now(), sender_email="sender2@example.com",
                recipient_emails=["recipient@example.com"], subject="Test 2",
                body_text="Text", body_html="<p>HTML</p>",
                attachments=[{"filename": "doc.pdf", "size": 1024}],
                is_read=True, folder="INBOX"
            )
        ]
        mock_extractor.extract_emails.return_value = emails
        
        self.orchestrator.email_extractors = [mock_extractor]
        
        result = self.orchestrator._extract_from_email()
        
        self.assertTrue(result.success)
        self.assertEqual(result.source, 'email')
        self.assertEqual(result.messages_count, 2)
        self.assertEqual(result.media_count, 1)  # One attachment
        self.assertEqual(len(result.errors), 0)
    
    def test_extract_from_email_auth_failure(self):
        """Test email extraction with authentication failure"""
        self.orchestrator.error_handler = Mock()
        
        mock_extractor = Mock()
        mock_extractor.authenticate.return_value = False
        self.orchestrator.email_extractors = [mock_extractor]
        
        result = self.orchestrator._extract_from_email()
        
        # Should still return a result, but with errors
        self.assertFalse(result.success)
        self.assertEqual(result.source, 'email')
        self.assertEqual(result.messages_count, 0)
        self.assertIn("authentication failed", result.errors[0].lower())
    
    def test_extract_from_email_extractor_failure(self):
        """Test email extraction with extractor failure"""
        self.orchestrator.error_handler = Mock()
        
        mock_extractor = Mock()
        mock_extractor.authenticate.side_effect = Exception("Extractor failed")
        self.orchestrator.email_extractors = [mock_extractor]
        
        result = self.orchestrator._extract_from_email()
        
        self.assertFalse(result.success)
        self.assertEqual(result.source, 'email')
        self.assertEqual(result.messages_count, 0)
        self.assertIn("Extractor failed", result.errors[0])
    
    def test_schedule_extraction_not_implemented(self):
        """Test that schedule_extraction raises NotImplementedError"""
        with self.assertRaises(NotImplementedError):
            self.orchestrator.schedule_extraction({})
    
    def test_send_notifications_without_initialization(self):
        """Test that send_notifications handles uninitialized state gracefully"""
        # Should not raise an exception when notification manager is not initialized
        try:
            self.orchestrator.send_notifications({})
        except Exception as e:
            self.fail(f"send_notifications raised an unexpected exception: {e}")
    
    def test_send_notifications_with_results(self):
        """Test sending notifications with extraction results"""
        # Initialize the orchestrator first
        self.orchestrator.initialize()
        
        # Create mock extraction results
        from pipeline.models import ExtractionResult
        mock_results = {
            'whatsapp': ExtractionResult(
                source='whatsapp',
                success=True,
                messages_count=10,
                media_count=5,
                errors=[],
                execution_time=15.5,
                output_paths={'json': '/path/to/whatsapp.json'}
            ),
            'email': ExtractionResult(
                source='email',
                success=True,
                messages_count=25,
                media_count=3,
                errors=[],
                execution_time=22.3,
                output_paths={'json': '/path/to/email.json'}
            )
        }
        
        # Should not raise an exception
        try:
            self.orchestrator.send_notifications(mock_results)
        except Exception as e:
            self.fail(f"send_notifications raised an unexpected exception: {e}")


if __name__ == '__main__':
    unittest.main()