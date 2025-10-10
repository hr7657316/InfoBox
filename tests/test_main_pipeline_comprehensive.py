"""
Comprehensive unit tests for the main pipeline orchestrator
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
        
        # Create a minimal config file
        config_content = """
whatsapp:
  accounts:
    - api_token: test_token
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
  file_logging: true

scheduler:
  enabled: false

notifications:
  enabled: false
"""
        with open(self.config_file, 'w') as f:
            f.write(config_content)
    
    def tearDown(self):
        """Clean up test fixtures"""
        import shutil
        shutil.rmtree(self.temp_dir)
    
    @patch('pipeline.main.ConfigManager')
    @patch('pipeline.main.PipelineLogger')
    @patch('pipeline.main.StorageManager')
    @patch('pipeline.main.ErrorHandler')
    @patch('pipeline.main.NotificationManager')
    def test_init_with_config_file(self, mock_notification, mock_error, mock_storage, mock_logger, mock_config):
        """Test PipelineOrchestrator initialization with config file"""
        mock_config_instance = Mock()
        mock_config.return_value = mock_config_instance
        mock_config_instance.load_config.return_value = {'test': 'config'}
        mock_config_instance.validate_config.return_value = []
        
        orchestrator = PipelineOrchestrator(self.config_file)
        
        self.assertEqual(orchestrator.config_file, self.config_file)
        mock_config.assert_called_once_with(self.config_file)
        mock_config_instance.load_config.assert_called_once()
        mock_config_instance.validate_config.assert_called_once()
    
    @patch('pipeline.main.ConfigManager')
    def test_init_with_invalid_config(self, mock_config):
        """Test initialization with invalid configuration"""
        mock_config_instance = Mock()
        mock_config.return_value = mock_config_instance
        mock_config_instance.load_config.return_value = {'test': 'config'}
        mock_config_instance.validate_config.return_value = ['Config error 1', 'Config error 2']
        
        with self.assertRaises(ValueError) as context:
            PipelineOrchestrator(self.config_file)
        
        self.assertIn('Configuration validation failed', str(context.exception))
        self.assertIn('Config error 1', str(context.exception))
        self.assertIn('Config error 2', str(context.exception))
    
    @patch('pipeline.main.ConfigManager')
    @patch('pipeline.main.PipelineLogger')
    @patch('pipeline.main.StorageManager')
    @patch('pipeline.main.ErrorHandler')
    @patch('pipeline.main.NotificationManager')
    def test_setup_components(self, mock_notification, mock_error, mock_storage, mock_logger, mock_config):
        """Test component setup during initialization"""
        mock_config_instance = Mock()
        mock_config.return_value = mock_config_instance
        mock_config_instance.load_config.return_value = {
            'storage': {'base_path': './data'},
            'logging': {'level': 'INFO'},
            'notifications': {'enabled': True}
        }
        mock_config_instance.validate_config.return_value = []
        mock_config_instance.get_storage_config.return_value = {'base_path': './data'}
        mock_config_instance.get_logging_config.return_value = {'level': 'INFO'}
        
        orchestrator = PipelineOrchestrator(self.config_file)
        
        # Verify components were created
        mock_logger.assert_called_once()
        mock_storage.assert_called_once_with('./data')
        mock_error.assert_called_once()
        mock_notification.assert_called_once()
    
    @patch('pipeline.main.ConfigManager')
    @patch('pipeline.main.PipelineLogger')
    @patch('pipeline.main.StorageManager')
    @patch('pipeline.main.ErrorHandler')
    @patch('pipeline.main.NotificationManager')
    @patch('pipeline.main.WhatsAppExtractor')
    @patch('pipeline.main.EmailExtractor')
    def test_run_extraction_success(self, mock_email_extractor, mock_whatsapp_extractor, 
                                   mock_notification, mock_error, mock_storage, mock_logger, mock_config):
        """Test successful extraction run"""
        # Setup mocks
        mock_config_instance = Mock()
        mock_config.return_value = mock_config_instance
        mock_config_instance.load_config.return_value = {}
        mock_config_instance.validate_config.return_value = []
        mock_config_instance.get_whatsapp_configs.return_value = [{'api_token': 'test'}]
        mock_config_instance.get_email_configs.return_value = [{'email': 'test@example.com'}]
        mock_config_instance.get_storage_config.return_value = {'base_path': './data'}
        mock_config_instance.get_logging_config.return_value = {'level': 'INFO'}
        
        # Mock extractors
        mock_whatsapp_instance = Mock()
        mock_whatsapp_extractor.return_value = mock_whatsapp_instance
        mock_whatsapp_instance.authenticate.return_value = True
        mock_whatsapp_instance.extract_messages.return_value = [Mock(), Mock()]  # 2 messages
        
        mock_email_instance = Mock()
        mock_email_extractor.return_value = mock_email_instance
        mock_email_instance.authenticate.return_value = True
        mock_email_instance.extract_emails.return_value = [Mock(), Mock(), Mock()]  # 3 emails
        
        # Mock storage
        mock_storage_instance = Mock()
        mock_storage.return_value = mock_storage_instance
        mock_storage_instance.save_whatsapp_data.return_value = {
            'json': '/path/to/whatsapp.json',
            'csv': '/path/to/whatsapp.csv'
        }
        mock_storage_instance.save_email_data.return_value = {
            'json': '/path/to/email.json',
            'csv': '/path/to/email.csv'
        }
        
        # Mock notification manager
        mock_notification_instance = Mock()
        mock_notification.return_value = mock_notification_instance
        mock_notification_instance.send_extraction_complete_notification.return_value = True
        
        orchestrator = PipelineOrchestrator(self.config_file)
        
        # Run extraction
        results = orchestrator.run_extraction()
        
        # Verify results
        self.assertIn('whatsapp', results)
        self.assertIn('email', results)
        
        whatsapp_result = results['whatsapp']
        self.assertTrue(whatsapp_result['success'])
        self.assertEqual(whatsapp_result['messages_count'], 2)
        
        email_result = results['email']
        self.assertTrue(email_result['success'])
        self.assertEqual(email_result['messages_count'], 3)
        
        # Verify notification was sent
        mock_notification_instance.send_extraction_complete_notification.assert_called_once_with(results)
    
    @patch('pipeline.main.ConfigManager')
    @patch('pipeline.main.PipelineLogger')
    @patch('pipeline.main.StorageManager')
    @patch('pipeline.main.ErrorHandler')
    @patch('pipeline.main.NotificationManager')
    @patch('pipeline.main.WhatsAppExtractor')
    def test_run_extraction_whatsapp_auth_failure(self, mock_whatsapp_extractor, mock_notification, 
                                                  mock_error, mock_storage, mock_logger, mock_config):
        """Test extraction run with WhatsApp authentication failure"""
        # Setup mocks
        mock_config_instance = Mock()
        mock_config.return_value = mock_config_instance
        mock_config_instance.load_config.return_value = {}
        mock_config_instance.validate_config.return_value = []
        mock_config_instance.get_whatsapp_configs.return_value = [{'api_token': 'invalid'}]
        mock_config_instance.get_email_configs.return_value = []
        mock_config_instance.get_storage_config.return_value = {'base_path': './data'}
        mock_config_instance.get_logging_config.return_value = {'level': 'INFO'}
        
        # Mock WhatsApp extractor with auth failure
        mock_whatsapp_instance = Mock()
        mock_whatsapp_extractor.return_value = mock_whatsapp_instance
        mock_whatsapp_instance.authenticate.return_value = False
        
        # Mock notification manager
        mock_notification_instance = Mock()
        mock_notification.return_value = mock_notification_instance
        
        orchestrator = PipelineOrchestrator(self.config_file)
        
        # Run extraction
        results = orchestrator.run_extraction()
        
        # Verify WhatsApp extraction failed
        self.assertIn('whatsapp', results)
        whatsapp_result = results['whatsapp']
        self.assertFalse(whatsapp_result['success'])
        self.assertEqual(whatsapp_result['messages_count'], 0)
        self.assertIn('Authentication failed', whatsapp_result['errors'])
    
    @patch('pipeline.main.ConfigManager')
    @patch('pipeline.main.PipelineLogger')
    @patch('pipeline.main.StorageManager')
    @patch('pipeline.main.ErrorHandler')
    @patch('pipeline.main.NotificationManager')
    @patch('pipeline.main.WhatsAppExtractor')
    def test_run_extraction_whatsapp_exception(self, mock_whatsapp_extractor, mock_notification, 
                                              mock_error, mock_storage, mock_logger, mock_config):
        """Test extraction run with WhatsApp extraction exception"""
        # Setup mocks
        mock_config_instance = Mock()
        mock_config.return_value = mock_config_instance
        mock_config_instance.load_config.return_value = {}
        mock_config_instance.validate_config.return_value = []
        mock_config_instance.get_whatsapp_configs.return_value = [{'api_token': 'test'}]
        mock_config_instance.get_email_configs.return_value = []
        mock_config_instance.get_storage_config.return_value = {'base_path': './data'}
        mock_config_instance.get_logging_config.return_value = {'level': 'INFO'}
        
        # Mock WhatsApp extractor with exception during extraction
        mock_whatsapp_instance = Mock()
        mock_whatsapp_extractor.return_value = mock_whatsapp_instance
        mock_whatsapp_instance.authenticate.return_value = True
        mock_whatsapp_instance.extract_messages.side_effect = Exception("API Error")
        
        # Mock error handler
        mock_error_instance = Mock()
        mock_error.return_value = mock_error_instance
        
        # Mock notification manager
        mock_notification_instance = Mock()
        mock_notification.return_value = mock_notification_instance
        
        orchestrator = PipelineOrchestrator(self.config_file)
        
        # Run extraction
        results = orchestrator.run_extraction()
        
        # Verify WhatsApp extraction failed
        self.assertIn('whatsapp', results)
        whatsapp_result = results['whatsapp']
        self.assertFalse(whatsapp_result['success'])
        self.assertEqual(whatsapp_result['messages_count'], 0)
        self.assertTrue(len(whatsapp_result['errors']) > 0)
        
        # Verify error was handled
        mock_error_instance.handle_error.assert_called()
    
    @patch('pipeline.main.ConfigManager')
    @patch('pipeline.main.PipelineLogger')
    @patch('pipeline.main.StorageManager')
    @patch('pipeline.main.ErrorHandler')
    @patch('pipeline.main.NotificationManager')
    def test_run_extraction_no_sources_configured(self, mock_notification, mock_error, 
                                                  mock_storage, mock_logger, mock_config):
        """Test extraction run with no sources configured"""
        # Setup mocks
        mock_config_instance = Mock()
        mock_config.return_value = mock_config_instance
        mock_config_instance.load_config.return_value = {}
        mock_config_instance.validate_config.return_value = []
        mock_config_instance.get_whatsapp_configs.return_value = []
        mock_config_instance.get_email_configs.return_value = []
        mock_config_instance.get_storage_config.return_value = {'base_path': './data'}
        mock_config_instance.get_logging_config.return_value = {'level': 'INFO'}
        
        # Mock notification manager
        mock_notification_instance = Mock()
        mock_notification.return_value = mock_notification_instance
        
        orchestrator = PipelineOrchestrator(self.config_file)
        
        # Run extraction
        results = orchestrator.run_extraction()
        
        # Should return empty results
        self.assertEqual(len(results), 0)
    
    @patch('pipeline.main.ConfigManager')
    @patch('pipeline.main.PipelineLogger')
    @patch('pipeline.main.StorageManager')
    @patch('pipeline.main.ErrorHandler')
    @patch('pipeline.main.NotificationManager')
    @patch('pipeline.main.WhatsAppExtractor')
    @patch('pipeline.main.EmailExtractor')
    def test_extract_whatsapp_data_multiple_accounts(self, mock_email_extractor, mock_whatsapp_extractor,
                                                    mock_notification, mock_error, mock_storage, 
                                                    mock_logger, mock_config):
        """Test WhatsApp extraction with multiple accounts"""
        # Setup mocks
        mock_config_instance = Mock()
        mock_config.return_value = mock_config_instance
        mock_config_instance.load_config.return_value = {}
        mock_config_instance.validate_config.return_value = []
        mock_config_instance.get_whatsapp_configs.return_value = [
            {'api_token': 'token1', 'phone_number_id': 'phone1'},
            {'api_token': 'token2', 'phone_number_id': 'phone2'}
        ]
        mock_config_instance.get_email_configs.return_value = []
        mock_config_instance.get_storage_config.return_value = {'base_path': './data'}
        mock_config_instance.get_logging_config.return_value = {'level': 'INFO'}
        
        # Mock WhatsApp extractors
        mock_whatsapp_instance1 = Mock()
        mock_whatsapp_instance2 = Mock()
        mock_whatsapp_extractor.side_effect = [mock_whatsapp_instance1, mock_whatsapp_instance2]
        
        mock_whatsapp_instance1.authenticate.return_value = True
        mock_whatsapp_instance1.extract_messages.return_value = [Mock(), Mock()]  # 2 messages
        
        mock_whatsapp_instance2.authenticate.return_value = True
        mock_whatsapp_instance2.extract_messages.return_value = [Mock()]  # 1 message
        
        # Mock storage
        mock_storage_instance = Mock()
        mock_storage.return_value = mock_storage_instance
        mock_storage_instance.save_whatsapp_data.return_value = {
            'json': '/path/to/whatsapp.json',
            'csv': '/path/to/whatsapp.csv'
        }
        
        orchestrator = PipelineOrchestrator(self.config_file)
        
        # Run extraction
        results = orchestrator.run_extraction()
        
        # Verify WhatsApp extraction combined results from both accounts
        self.assertIn('whatsapp', results)
        whatsapp_result = results['whatsapp']
        self.assertTrue(whatsapp_result['success'])
        self.assertEqual(whatsapp_result['messages_count'], 3)  # 2 + 1 messages
        
        # Verify both extractors were called
        self.assertEqual(mock_whatsapp_extractor.call_count, 2)
    
    @patch('pipeline.main.ConfigManager')
    @patch('pipeline.main.PipelineLogger')
    @patch('pipeline.main.StorageManager')
    @patch('pipeline.main.ErrorHandler')
    @patch('pipeline.main.NotificationManager')
    @patch('pipeline.main.EmailExtractor')
    def test_extract_email_data_multiple_accounts(self, mock_email_extractor, mock_notification, 
                                                  mock_error, mock_storage, mock_logger, mock_config):
        """Test email extraction with multiple accounts"""
        # Setup mocks
        mock_config_instance = Mock()
        mock_config.return_value = mock_config_instance
        mock_config_instance.load_config.return_value = {}
        mock_config_instance.validate_config.return_value = []
        mock_config_instance.get_whatsapp_configs.return_value = []
        mock_config_instance.get_email_configs.return_value = [
            {'email': 'test1@example.com', 'password': 'pass1'},
            {'email': 'test2@example.com', 'password': 'pass2'}
        ]
        mock_config_instance.get_storage_config.return_value = {'base_path': './data'}
        mock_config_instance.get_logging_config.return_value = {'level': 'INFO'}
        
        # Mock email extractors
        mock_email_instance1 = Mock()
        mock_email_instance2 = Mock()
        mock_email_extractor.side_effect = [mock_email_instance1, mock_email_instance2]
        
        mock_email_instance1.authenticate.return_value = True
        mock_email_instance1.extract_emails.return_value = [Mock(), Mock(), Mock()]  # 3 emails
        
        mock_email_instance2.authenticate.return_value = True
        mock_email_instance2.extract_emails.return_value = [Mock(), Mock()]  # 2 emails
        
        # Mock storage
        mock_storage_instance = Mock()
        mock_storage.return_value = mock_storage_instance
        mock_storage_instance.save_email_data.return_value = {
            'json': '/path/to/email.json',
            'csv': '/path/to/email.csv'
        }
        
        orchestrator = PipelineOrchestrator(self.config_file)
        
        # Run extraction
        results = orchestrator.run_extraction()
        
        # Verify email extraction combined results from both accounts
        self.assertIn('email', results)
        email_result = results['email']
        self.assertTrue(email_result['success'])
        self.assertEqual(email_result['messages_count'], 5)  # 3 + 2 emails
        
        # Verify both extractors were called
        self.assertEqual(mock_email_extractor.call_count, 2)
    
    @patch('pipeline.main.ConfigManager')
    @patch('pipeline.main.PipelineLogger')
    @patch('pipeline.main.StorageManager')
    @patch('pipeline.main.ErrorHandler')
    @patch('pipeline.main.NotificationManager')
    def test_get_extraction_summary(self, mock_notification, mock_error, mock_storage, 
                                   mock_logger, mock_config):
        """Test extraction summary generation"""
        # Setup mocks
        mock_config_instance = Mock()
        mock_config.return_value = mock_config_instance
        mock_config_instance.load_config.return_value = {}
        mock_config_instance.validate_config.return_value = []
        mock_config_instance.get_whatsapp_configs.return_value = []
        mock_config_instance.get_email_configs.return_value = []
        mock_config_instance.get_storage_config.return_value = {'base_path': './data'}
        mock_config_instance.get_logging_config.return_value = {'level': 'INFO'}
        
        orchestrator = PipelineOrchestrator(self.config_file)
        
        # Create test results
        results = {
            'whatsapp': {
                'success': True,
                'messages_count': 10,
                'media_count': 5,
                'errors': [],
                'execution_time': 15.5,
                'output_paths': {'json': '/path/to/whatsapp.json'}
            },
            'email': {
                'success': False,
                'messages_count': 0,
                'media_count': 0,
                'errors': ['Authentication failed'],
                'execution_time': 2.1,
                'output_paths': {}
            }
        }
        
        summary = orchestrator._get_extraction_summary(results)
        
        # Verify summary content
        self.assertEqual(summary['total_sources'], 2)
        self.assertEqual(summary['successful_sources'], 1)
        self.assertEqual(summary['failed_sources'], 1)
        self.assertEqual(summary['total_messages'], 10)
        self.assertEqual(summary['total_media'], 5)
        self.assertEqual(summary['total_errors'], 1)
        self.assertAlmostEqual(summary['total_execution_time'], 17.6, places=1)
        self.assertEqual(summary['success_rate'], 0.5)
    
    @patch('pipeline.main.ConfigManager')
    @patch('pipeline.main.PipelineLogger')
    @patch('pipeline.main.StorageManager')
    @patch('pipeline.main.ErrorHandler')
    @patch('pipeline.main.NotificationManager')
    def test_cleanup_resources(self, mock_notification, mock_error, mock_storage, 
                              mock_logger, mock_config):
        """Test resource cleanup"""
        # Setup mocks
        mock_config_instance = Mock()
        mock_config.return_value = mock_config_instance
        mock_config_instance.load_config.return_value = {}
        mock_config_instance.validate_config.return_value = []
        mock_config_instance.get_whatsapp_configs.return_value = []
        mock_config_instance.get_email_configs.return_value = []
        mock_config_instance.get_storage_config.return_value = {'base_path': './data'}
        mock_config_instance.get_logging_config.return_value = {'level': 'INFO'}
        
        orchestrator = PipelineOrchestrator(self.config_file)
        
        # Add some mock extractors to cleanup
        mock_extractor1 = Mock()
        mock_extractor2 = Mock()
        orchestrator.active_extractors = [mock_extractor1, mock_extractor2]
        
        # Call cleanup
        orchestrator._cleanup_resources()
        
        # Verify extractors were closed
        mock_extractor1.close.assert_called_once()
        mock_extractor2.close.assert_called_once()
        
        # Verify extractors list was cleared
        self.assertEqual(len(orchestrator.active_extractors), 0)
    
    @patch('pipeline.main.ConfigManager')
    @patch('pipeline.main.PipelineLogger')
    @patch('pipeline.main.StorageManager')
    @patch('pipeline.main.ErrorHandler')
    @patch('pipeline.main.NotificationManager')
    def test_context_manager_usage(self, mock_notification, mock_error, mock_storage, 
                                  mock_logger, mock_config):
        """Test PipelineOrchestrator as context manager"""
        # Setup mocks
        mock_config_instance = Mock()
        mock_config.return_value = mock_config_instance
        mock_config_instance.load_config.return_value = {}
        mock_config_instance.validate_config.return_value = []
        mock_config_instance.get_whatsapp_configs.return_value = []
        mock_config_instance.get_email_configs.return_value = []
        mock_config_instance.get_storage_config.return_value = {'base_path': './data'}
        mock_config_instance.get_logging_config.return_value = {'level': 'INFO'}
        
        # Use as context manager
        with PipelineOrchestrator(self.config_file) as orchestrator:
            # Add mock extractor
            mock_extractor = Mock()
            orchestrator.active_extractors.append(mock_extractor)
        
        # Verify cleanup was called
        mock_extractor.close.assert_called_once()
    
    @patch('pipeline.main.ConfigManager')
    @patch('pipeline.main.PipelineLogger')
    @patch('pipeline.main.StorageManager')
    @patch('pipeline.main.ErrorHandler')
    @patch('pipeline.main.NotificationManager')
    @patch('pipeline.main.WhatsAppExtractor')
    def test_media_download_integration(self, mock_whatsapp_extractor, mock_notification, 
                                       mock_error, mock_storage, mock_logger, mock_config):
        """Test media download integration during extraction"""
        # Setup mocks
        mock_config_instance = Mock()
        mock_config.return_value = mock_config_instance
        mock_config_instance.load_config.return_value = {}
        mock_config_instance.validate_config.return_value = []
        mock_config_instance.get_whatsapp_configs.return_value = [{'api_token': 'test'}]
        mock_config_instance.get_email_configs.return_value = []
        mock_config_instance.get_storage_config.return_value = {'base_path': './data'}
        mock_config_instance.get_logging_config.return_value = {'level': 'INFO'}
        
        # Mock WhatsApp extractor with media messages
        mock_whatsapp_instance = Mock()
        mock_whatsapp_extractor.return_value = mock_whatsapp_instance
        mock_whatsapp_instance.authenticate.return_value = True
        
        # Create mock messages with media
        mock_message1 = Mock()
        mock_message1.media_url = 'https://example.com/image1.jpg'
        mock_message1.media_filename = 'image1.jpg'
        
        mock_message2 = Mock()
        mock_message2.media_url = None
        mock_message2.media_filename = None
        
        mock_whatsapp_instance.extract_messages.return_value = [mock_message1, mock_message2]
        mock_whatsapp_instance.download_media.return_value = '/path/to/downloaded/image1.jpg'
        
        # Mock storage
        mock_storage_instance = Mock()
        mock_storage.return_value = mock_storage_instance
        mock_storage_instance.get_media_directory.return_value = '/path/to/media'
        mock_storage_instance.save_whatsapp_data.return_value = {
            'json': '/path/to/whatsapp.json',
            'csv': '/path/to/whatsapp.csv'
        }
        
        orchestrator = PipelineOrchestrator(self.config_file)
        
        # Run extraction
        results = orchestrator.run_extraction()
        
        # Verify media download was attempted
        mock_whatsapp_instance.download_media.assert_called_once_with(
            'https://example.com/image1.jpg',
            'image1.jpg',
            '/path/to/media'
        )
        
        # Verify results include media count
        whatsapp_result = results['whatsapp']
        self.assertEqual(whatsapp_result['media_count'], 1)


class TestPipelineOrchestratorScheduling(unittest.TestCase):
    """Test cases for scheduling functionality"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.temp_dir = tempfile.mkdtemp()
        self.config_file = os.path.join(self.temp_dir, 'test_config.yaml')
        
        # Create config with scheduling enabled
        config_content = """
scheduler:
  enabled: true
  schedule_type: interval
  interval_hours: 2

storage:
  base_path: ./test_data

logging:
  level: INFO

notifications:
  enabled: false
"""
        with open(self.config_file, 'w') as f:
            f.write(config_content)
    
    def tearDown(self):
        """Clean up test fixtures"""
        import shutil
        shutil.rmtree(self.temp_dir)
    
    @patch('pipeline.main.ConfigManager')
    @patch('pipeline.main.PipelineLogger')
    @patch('pipeline.main.StorageManager')
    @patch('pipeline.main.ErrorHandler')
    @patch('pipeline.main.NotificationManager')
    @patch('pipeline.main.schedule')
    def test_schedule_extraction_interval(self, mock_schedule, mock_notification, mock_error, 
                                         mock_storage, mock_logger, mock_config):
        """Test scheduling extraction with interval"""
        # Setup mocks
        mock_config_instance = Mock()
        mock_config.return_value = mock_config_instance
        mock_config_instance.load_config.return_value = {}
        mock_config_instance.validate_config.return_value = []
        mock_config_instance.get_whatsapp_configs.return_value = []
        mock_config_instance.get_email_configs.return_value = []
        mock_config_instance.get_storage_config.return_value = {'base_path': './data'}
        mock_config_instance.get_logging_config.return_value = {'level': 'INFO'}
        mock_config_instance.get_scheduler_config.return_value = {
            'enabled': True,
            'schedule_type': 'interval',
            'interval_hours': 2
        }
        
        orchestrator = PipelineOrchestrator(self.config_file)
        
        # Schedule extraction
        orchestrator.schedule_extraction()
        
        # Verify schedule was configured
        mock_schedule.every.assert_called_once()
        mock_schedule.every.return_value.hours.assert_called_once_with(2)
    
    @patch('pipeline.main.ConfigManager')
    @patch('pipeline.main.PipelineLogger')
    @patch('pipeline.main.StorageManager')
    @patch('pipeline.main.ErrorHandler')
    @patch('pipeline.main.NotificationManager')
    @patch('pipeline.main.schedule')
    def test_schedule_extraction_daily(self, mock_schedule, mock_notification, mock_error, 
                                      mock_storage, mock_logger, mock_config):
        """Test scheduling extraction daily"""
        # Setup mocks
        mock_config_instance = Mock()
        mock_config.return_value = mock_config_instance
        mock_config_instance.load_config.return_value = {}
        mock_config_instance.validate_config.return_value = []
        mock_config_instance.get_whatsapp_configs.return_value = []
        mock_config_instance.get_email_configs.return_value = []
        mock_config_instance.get_storage_config.return_value = {'base_path': './data'}
        mock_config_instance.get_logging_config.return_value = {'level': 'INFO'}
        mock_config_instance.get_scheduler_config.return_value = {
            'enabled': True,
            'schedule_type': 'daily',
            'daily_time': '02:00'
        }
        
        orchestrator = PipelineOrchestrator(self.config_file)
        
        # Schedule extraction
        orchestrator.schedule_extraction()
        
        # Verify daily schedule was configured
        mock_schedule.every.assert_called_once()
        mock_schedule.every.return_value.day.assert_called_once()
        mock_schedule.every.return_value.day.return_value.at.assert_called_once_with('02:00')
    
    @patch('pipeline.main.ConfigManager')
    @patch('pipeline.main.PipelineLogger')
    @patch('pipeline.main.StorageManager')
    @patch('pipeline.main.ErrorHandler')
    @patch('pipeline.main.NotificationManager')
    def test_schedule_extraction_disabled(self, mock_notification, mock_error, mock_storage, 
                                         mock_logger, mock_config):
        """Test scheduling when disabled"""
        # Setup mocks
        mock_config_instance = Mock()
        mock_config.return_value = mock_config_instance
        mock_config_instance.load_config.return_value = {}
        mock_config_instance.validate_config.return_value = []
        mock_config_instance.get_whatsapp_configs.return_value = []
        mock_config_instance.get_email_configs.return_value = []
        mock_config_instance.get_storage_config.return_value = {'base_path': './data'}
        mock_config_instance.get_logging_config.return_value = {'level': 'INFO'}
        mock_config_instance.get_scheduler_config.return_value = {
            'enabled': False
        }
        
        orchestrator = PipelineOrchestrator(self.config_file)
        
        # Schedule extraction (should do nothing)
        result = orchestrator.schedule_extraction()
        
        # Should return False when scheduling is disabled
        self.assertFalse(result)


if __name__ == '__main__':
    unittest.main()