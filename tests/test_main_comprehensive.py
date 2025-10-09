"""
Comprehensive unit tests for the main pipeline orchestrator
"""

import unittest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime
import tempfile
import shutil

from pipeline.main import PipelineOrchestrator
from pipeline.models import ExtractionResult, WhatsAppMessage, Email
from pipeline.utils.error_handler import ErrorHandler, ErrorCategory, ErrorSeverity


class TestPipelineOrchestratorComprehensive(unittest.TestCase):
    """Comprehensive test cases for PipelineOrchestrator"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.temp_dir = tempfile.mkdtemp()
        self.config_path = f"{self.temp_dir}/test_config.yaml"
        
        # Create a test config file
        test_config = """
whatsapp:
  api_token: test_token
  phone_number_id: test_phone_id

email:
  accounts:
    - email: test@example.com
      password: test_password
      imap_server: imap.example.com

storage:
  base_path: {temp_dir}/data

logging:
  log_dir: {temp_dir}/logs
  log_level: DEBUG
""".format(temp_dir=self.temp_dir)
        
        with open(self.config_path, 'w') as f:
            f.write(test_config)
        
        self.orchestrator = PipelineOrchestrator(self.config_path)
    
    def tearDown(self):
        """Clean up test fixtures"""
        shutil.rmtree(self.temp_dir)
    
    def test_init_default_config(self):
        """Test orchestrator initialization with default config"""
        orchestrator = PipelineOrchestrator()
        self.assertEqual(orchestrator.config_path, "config.yaml")
        self.assertIsNotNone(orchestrator.config_manager)
        self.assertIsNone(orchestrator.logger)
        self.assertFalse(orchestrator._initialized)
    
    def test_init_custom_config(self):
        """Test orchestrator initialization with custom config"""
        self.assertEqual(self.orchestrator.config_path, self.config_path)
        self.assertIsNotNone(self.orchestrator.config_manager)
    
    @patch('pipeline.main.PipelineLogger')
    @patch('pipeline.main.ErrorHandler')
    @patch('pipeline.main.StorageManager')
    def test_initialize_success(self, mock_storage, mock_error_handler, mock_logger):
        """Test successful initialization"""
        # Mock logger setup
        mock_logger_instance = Mock()
        mock_logger.return_value = mock_logger_instance
        mock_logger_instance.logger = Mock()
        
        # Mock error handler
        mock_error_handler_instance = Mock()
        mock_error_handler.return_value = mock_error_handler_instance
        
        # Mock storage manager
        mock_storage_instance = Mock()
        mock_storage.return_value = mock_storage_instance
        
        # Mock config validation
        with patch.object(self.orchestrator, '_validate_configuration', return_value=[]):
            with patch.object(self.orchestrator, '_setup_extractors'):
                result = self.orchestrator.initialize()
        
        self.assertTrue(result)
        self.assertTrue(self.orchestrator._initialized)
        self.assertIsNotNone(self.orchestrator.logger)
        self.assertIsNotNone(self.orchestrator.error_handler)
        self.assertIsNotNone(self.orchestrator.storage_manager)
    
    @patch('pipeline.main.PipelineLogger')
    def test_initialize_validation_failure(self, mock_logger):
        """Test initialization with validation errors"""
        # Mock logger setup
        mock_logger_instance = Mock()
        mock_logger.return_value = mock_logger_instance
        mock_logger_instance.logger = Mock()
        
        # Mock validation to return errors
        with patch.object(self.orchestrator, '_validate_configuration', 
                         return_value=["Test validation error"]):
            result = self.orchestrator.initialize()
        
        self.assertFalse(result)
        self.assertFalse(self.orchestrator._initialized)
    
    def test_initialize_exception_handling(self):
        """Test initialization with exception"""
        # Mock config manager to raise exception
        with patch.object(self.orchestrator.config_manager, 'load_config', 
                         side_effect=Exception("Config load failed")):
            result = self.orchestrator.initialize()
        
        self.assertFalse(result)
        self.assertFalse(self.orchestrator._initialized)
    
    def test_validate_configuration_valid(self):
        """Test configuration validation with valid config"""
        # Mock config manager validation
        with patch.object(self.orchestrator.config_manager, 'validate_config', return_value=[]):
            with patch('os.makedirs'):
                errors = self.orchestrator._validate_configuration()
        
        self.assertEqual(errors, [])
    
    def test_validate_configuration_no_sources(self):
        """Test configuration validation with no data sources"""
        # Mock config with no sources
        with patch.object(self.orchestrator.config_manager, 'load_config', 
                         return_value={'storage': {'base_path': '/tmp'}}):
            with patch.object(self.orchestrator.config_manager, 'validate_config', return_value=[]):
                with patch('os.makedirs'):
                    errors = self.orchestrator._validate_configuration()
        
        self.assertIn("At least one data source", errors[0])
    
    def test_validate_configuration_storage_error(self):
        """Test configuration validation with storage directory error"""
        with patch.object(self.orchestrator.config_manager, 'validate_config', return_value=[]):
            with patch.object(self.orchestrator.config_manager, 'load_config', 
                             return_value={'whatsapp': {'api_token': 'test'}, 'storage': {'base_path': '/invalid/path'}}):
                with patch('os.makedirs', side_effect=PermissionError("Permission denied")):
                    errors = self.orchestrator._validate_configuration()
        
        self.assertTrue(any("Cannot create storage directory" in error for error in errors))
    
    @patch('pipeline.main.WhatsAppExtractor')
    @patch('pipeline.main.EmailExtractor')
    def test_setup_extractors_success(self, mock_email_extractor, mock_whatsapp_extractor):
        """Test successful extractor setup"""
        # Mock logger
        self.orchestrator.logger = Mock()
        self.orchestrator.error_handler = Mock()
        
        # Mock extractors
        mock_whatsapp_instance = Mock()
        mock_whatsapp_extractor.return_value = mock_whatsapp_instance
        
        mock_email_instance = Mock()
        mock_email_extractor.return_value = mock_email_instance
        
        self.orchestrator._setup_extractors()
        
        self.assertEqual(self.orchestrator.whatsapp_extractor, mock_whatsapp_instance)
        self.assertEqual(len(self.orchestrator.email_extractors), 1)
        self.assertEqual(self.orchestrator.email_extractors[0], mock_email_instance)
    
    @patch('pipeline.main.WhatsAppExtractor')
    def test_setup_extractors_whatsapp_failure(self, mock_whatsapp_extractor):
        """Test extractor setup with WhatsApp failure"""
        # Mock logger and error handler
        self.orchestrator.logger = Mock()
        self.orchestrator.error_handler = Mock()
        
        # Mock WhatsApp extractor to raise exception
        mock_whatsapp_extractor.side_effect = Exception("WhatsApp setup failed")
        
        self.orchestrator._setup_extractors()
        
        self.assertIsNone(self.orchestrator.whatsapp_extractor)
        self.orchestrator.error_handler.handle_error.assert_called()
    
    def test_run_extraction_not_initialized(self):
        """Test run_extraction when not initialized"""
        with patch.object(self.orchestrator, 'initialize', return_value=False):
            results = self.orchestrator.run_extraction()
        
        self.assertEqual(results, {})
    
    @patch('pipeline.main.WhatsAppExtractor')
    def test_run_extraction_whatsapp_success(self, mock_whatsapp_extractor):
        """Test successful WhatsApp extraction"""
        # Setup mocks
        self.orchestrator._initialized = True
        self.orchestrator.logger = Mock()
        self.orchestrator.error_handler = Mock()
        self.orchestrator.error_handler.get_error_summary.return_value = {'total_errors': 0}
        
        # Mock WhatsApp extractor
        mock_extractor = Mock()
        mock_extractor.authenticate.return_value = True
        mock_extractor.extract_messages.return_value = [
            WhatsAppMessage(
                id="test1", timestamp=datetime.now(), sender_phone="+1234567890",
                message_content="Test message", message_type="text"
            )
        ]
        mock_extractor.download_media.return_value = "/path/to/media"
        self.orchestrator.whatsapp_extractor = mock_extractor
        
        # Mock storage manager
        self.orchestrator.storage_manager = Mock()
        self.orchestrator.storage_manager.get_media_directory.return_value = "/media/dir"
        self.orchestrator.storage_manager.save_whatsapp_data.return_value = {"json": "/path/to/data.json"}
        
        results = self.orchestrator.run_extraction()
        
        self.assertIn('whatsapp', results)
        self.assertTrue(results['whatsapp'].success)
        self.assertEqual(results['whatsapp'].messages_count, 1)
    
    def test_run_extraction_whatsapp_auth_failure(self):
        """Test WhatsApp extraction with authentication failure"""
        # Setup mocks
        self.orchestrator._initialized = True
        self.orchestrator.logger = Mock()
        self.orchestrator.error_handler = Mock()
        self.orchestrator.error_handler.get_error_summary.return_value = {'total_errors': 0}
        
        # Mock WhatsApp extractor with auth failure
        mock_extractor = Mock()
        mock_extractor.authenticate.return_value = False
        self.orchestrator.whatsapp_extractor = mock_extractor
        
        # Mock storage manager
        self.orchestrator.storage_manager = Mock()
        
        results = self.orchestrator.run_extraction()
        
        self.assertIn('whatsapp', results)
        self.assertFalse(results['whatsapp'].success)
        self.assertEqual(results['whatsapp'].messages_count, 0)
    
    def test_run_extraction_whatsapp_exception(self):
        """Test WhatsApp extraction with exception"""
        # Setup mocks
        self.orchestrator._initialized = True
        self.orchestrator.logger = Mock()
        self.orchestrator.error_handler = Mock()
        self.orchestrator.error_handler.get_error_summary.return_value = {'total_errors': 0}
        
        # Mock WhatsApp extractor to raise exception
        mock_extractor = Mock()
        mock_extractor.authenticate.side_effect = Exception("Connection failed")
        self.orchestrator.whatsapp_extractor = mock_extractor
        
        results = self.orchestrator.run_extraction()
        
        self.assertIn('whatsapp', results)
        self.assertFalse(results['whatsapp'].success)
        self.assertIn("Connection failed", results['whatsapp'].errors)
    
    def test_run_extraction_email_success(self):
        """Test successful email extraction"""
        # Setup mocks
        self.orchestrator._initialized = True
        self.orchestrator.logger = Mock()
        self.orchestrator.error_handler = Mock()
        self.orchestrator.error_handler.get_error_summary.return_value = {'total_errors': 0}
        
        # Mock email extractor
        mock_extractor = Mock()
        mock_extractor.authenticate.return_value = True
        mock_extractor.extract_emails.return_value = [
            Email(
                id="email1", timestamp=datetime.now(), sender_email="test@example.com",
                recipient_emails=["recipient@example.com"], subject="Test", body_text="Test body",
                body_html="", attachments=[], is_read=True, folder="INBOX"
            )
        ]
        self.orchestrator.email_extractors = [mock_extractor]
        
        # Mock storage manager
        self.orchestrator.storage_manager = Mock()
        self.orchestrator.storage_manager.save_email_data.return_value = {"json": "/path/to/emails.json"}
        
        results = self.orchestrator.run_extraction()
        
        self.assertIn('email', results)
        self.assertTrue(results['email'].success)
        self.assertEqual(results['email'].messages_count, 1)
    
    def test_run_extraction_email_auth_failure(self):
        """Test email extraction with authentication failure"""
        # Setup mocks
        self.orchestrator._initialized = True
        self.orchestrator.logger = Mock()
        self.orchestrator.error_handler = Mock()
        self.orchestrator.error_handler.get_error_summary.return_value = {'total_errors': 0}
        
        # Mock email extractor with auth failure
        mock_extractor = Mock()
        mock_extractor.authenticate.return_value = False
        self.orchestrator.email_extractors = [mock_extractor]
        
        # Mock storage manager
        self.orchestrator.storage_manager = Mock()
        
        results = self.orchestrator.run_extraction()
        
        self.assertIn('email', results)
        # Should not be successful when authentication fails and no emails extracted
        self.assertFalse(results['email'].success)
        self.assertEqual(results['email'].messages_count, 0)
        self.assertTrue(len(results['email'].errors) > 0)
        self.assertIn("authentication failed", results['email'].errors[0].lower())
    
    def test_run_extraction_media_download_failure(self):
        """Test extraction with media download failures"""
        # Setup mocks
        self.orchestrator._initialized = True
        self.orchestrator.logger = Mock()
        self.orchestrator.error_handler = Mock()
        self.orchestrator.error_handler.get_error_summary.return_value = {'total_errors': 0}
        
        # Mock WhatsApp extractor with media
        mock_extractor = Mock()
        mock_extractor.authenticate.return_value = True
        
        # Create message with media
        message_with_media = WhatsAppMessage(
            id="test1", timestamp=datetime.now(), sender_phone="+1234567890",
            message_content="Test message", message_type="image",
            media_url="http://example.com/image.jpg", media_filename="image.jpg"
        )
        mock_extractor.extract_messages.return_value = [message_with_media]
        
        # Mock media download to fail
        mock_extractor.download_media.side_effect = Exception("Download failed")
        
        self.orchestrator.whatsapp_extractor = mock_extractor
        
        # Mock storage manager
        self.orchestrator.storage_manager = Mock()
        self.orchestrator.storage_manager.get_media_directory.return_value = "/media/dir"
        self.orchestrator.storage_manager.save_whatsapp_data.return_value = {"json": "/path/to/data.json"}
        
        results = self.orchestrator.run_extraction()
        
        self.assertIn('whatsapp', results)
        self.assertTrue(results['whatsapp'].success)  # Should still succeed
        self.assertEqual(results['whatsapp'].messages_count, 1)
        self.assertEqual(results['whatsapp'].media_count, 0)  # No media downloaded
        self.assertTrue(len(results['whatsapp'].errors) > 0)  # Should have error
    
    def test_run_extraction_multiple_email_extractors(self):
        """Test extraction with multiple email extractors"""
        # Setup mocks
        self.orchestrator._initialized = True
        self.orchestrator.logger = Mock()
        self.orchestrator.error_handler = Mock()
        self.orchestrator.error_handler.get_error_summary.return_value = {'total_errors': 0}
        
        # Mock multiple email extractors
        mock_extractor1 = Mock()
        mock_extractor1.authenticate.return_value = True
        mock_extractor1.extract_emails.return_value = [
            Email(id="email1", timestamp=datetime.now(), sender_email="test1@example.com",
                  recipient_emails=[], subject="Test1", body_text="", body_html="",
                  attachments=[], is_read=True, folder="INBOX")
        ]
        
        mock_extractor2 = Mock()
        mock_extractor2.authenticate.return_value = True
        mock_extractor2.extract_emails.return_value = [
            Email(id="email2", timestamp=datetime.now(), sender_email="test2@example.com",
                  recipient_emails=[], subject="Test2", body_text="", body_html="",
                  attachments=[], is_read=True, folder="INBOX")
        ]
        
        self.orchestrator.email_extractors = [mock_extractor1, mock_extractor2]
        
        # Mock storage manager
        self.orchestrator.storage_manager = Mock()
        self.orchestrator.storage_manager.save_email_data.return_value = {"json": "/path/to/emails.json"}
        
        results = self.orchestrator.run_extraction()
        
        self.assertIn('email', results)
        self.assertTrue(results['email'].success)
        self.assertEqual(results['email'].messages_count, 2)  # Combined from both extractors
    
    def test_run_extraction_partial_email_failure(self):
        """Test extraction with one email extractor failing"""
        # Setup mocks
        self.orchestrator._initialized = True
        self.orchestrator.logger = Mock()
        self.orchestrator.error_handler = Mock()
        self.orchestrator.error_handler.get_error_summary.return_value = {'total_errors': 0}
        
        # Mock email extractors - one succeeds, one fails
        mock_extractor1 = Mock()
        mock_extractor1.authenticate.return_value = True
        mock_extractor1.extract_emails.return_value = [
            Email(id="email1", timestamp=datetime.now(), sender_email="test1@example.com",
                  recipient_emails=[], subject="Test1", body_text="", body_html="",
                  attachments=[], is_read=True, folder="INBOX")
        ]
        
        mock_extractor2 = Mock()
        mock_extractor2.authenticate.side_effect = Exception("Extractor 2 failed")
        
        self.orchestrator.email_extractors = [mock_extractor1, mock_extractor2]
        
        # Mock storage manager
        self.orchestrator.storage_manager = Mock()
        self.orchestrator.storage_manager.save_email_data.return_value = {"json": "/path/to/emails.json"}
        
        results = self.orchestrator.run_extraction()
        
        self.assertIn('email', results)
        self.assertTrue(results['email'].success)  # Should succeed with partial data
        self.assertEqual(results['email'].messages_count, 1)  # Only from successful extractor
        self.assertTrue(len(results['email'].errors) > 0)  # Should have error from failed extractor
    
    def test_schedule_extraction_not_implemented(self):
        """Test that schedule_extraction raises NotImplementedError"""
        with self.assertRaises(NotImplementedError):
            self.orchestrator.schedule_extraction({})
    
    def test_send_notifications_not_implemented(self):
        """Test that send_notifications raises NotImplementedError"""
        with self.assertRaises(NotImplementedError):
            self.orchestrator.send_notifications({})
    
    def test_extract_from_whatsapp_no_messages(self):
        """Test WhatsApp extraction with no messages"""
        # Setup mocks
        self.orchestrator.logger = Mock()
        self.orchestrator.error_handler = Mock()
        
        # Mock WhatsApp extractor with no messages
        mock_extractor = Mock()
        mock_extractor.authenticate.return_value = True
        mock_extractor.extract_messages.return_value = []
        self.orchestrator.whatsapp_extractor = mock_extractor
        
        # Mock storage manager
        self.orchestrator.storage_manager = Mock()
        self.orchestrator.storage_manager.get_media_directory.return_value = "/media/dir"
        
        result = self.orchestrator._extract_from_whatsapp()
        
        self.assertTrue(result.success)
        self.assertEqual(result.messages_count, 0)
        self.assertEqual(result.media_count, 0)
        self.assertEqual(result.source, 'whatsapp')
    
    def test_extract_from_email_no_emails(self):
        """Test email extraction with no emails"""
        # Setup mocks
        self.orchestrator.logger = Mock()
        self.orchestrator.error_handler = Mock()
        
        # Mock email extractor with no emails
        mock_extractor = Mock()
        mock_extractor.authenticate.return_value = True
        mock_extractor.extract_emails.return_value = []
        self.orchestrator.email_extractors = [mock_extractor]
        
        # Mock storage manager
        self.orchestrator.storage_manager = Mock()
        
        result = self.orchestrator._extract_from_email()
        
        self.assertTrue(result.success)
        self.assertEqual(result.messages_count, 0)
        self.assertEqual(result.media_count, 0)
        self.assertEqual(result.source, 'email')


if __name__ == '__main__':
    unittest.main()