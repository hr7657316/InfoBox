"""
Comprehensive integration and end-to-end tests for the data extraction pipeline
"""

import unittest
import tempfile
import shutil
import os
import json
import csv
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timedelta
from pathlib import Path

from pipeline.main import PipelineOrchestrator
from pipeline.models import WhatsAppMessage, Email, ExtractionResult
from pipeline.utils.config import ConfigManager
from pipeline.utils.storage import StorageManager
from pipeline.utils.logger import PipelineLogger
from pipeline.utils.error_handler import ErrorHandler
from pipeline.utils.notification_manager import NotificationManager


class TestPipelineIntegration(unittest.TestCase):
    """Integration tests for complete pipeline workflows"""
    
    def setUp(self):
        """Set up test environment"""
        self.temp_dir = tempfile.mkdtemp()
        self.config_file = os.path.join(self.temp_dir, 'test_config.yaml')
        self.data_dir = os.path.join(self.temp_dir, 'data')
        
        # Create test configuration
        config_content = f"""
whatsapp:
  accounts:
    - api_token: test_token_1
      phone_number_id: test_phone_1
    - twilio_account_sid: test_sid_2
      twilio_auth_token: test_token_2
      twilio_whatsapp_number: +1234567890

email:
  accounts:
    - email: test1@example.com
      password: test_password_1
      imap_server: imap.example.com
      imap_port: 993
      use_ssl: true
      auth_method: password
    - email: test2@gmail.com
      imap_server: imap.gmail.com
      imap_port: 993
      use_ssl: true
      auth_method: oauth2
      client_id: test_client_id
      client_secret: test_client_secret
      refresh_token: test_refresh_token

storage:
  base_path: {self.data_dir}
  create_date_folders: true
  json_format: true
  csv_format: true

logging:
  level: INFO
  file_logging: true
  console_logging: false
  log_file: {os.path.join(self.temp_dir, 'test.log')}

notifications:
  enabled: false
"""
        
        with open(self.config_file, 'w') as f:
            f.write(config_content)
    
    def tearDown(self):
        """Clean up test environment"""
        shutil.rmtree(self.temp_dir)
    
    @patch('pipeline.whatsapp.whatsapp_extractor.WhatsAppExtractor')
    @patch('pipeline.email.email_extractor.EmailExtractor')
    def test_full_pipeline_execution_success(self, mock_email_extractor, mock_whatsapp_extractor):
        """Test complete pipeline execution with successful extraction from all sources"""
        # Create mock WhatsApp messages
        whatsapp_messages = [
            WhatsAppMessage(
                id="wa_msg_1",
                timestamp=datetime(2024, 1, 15, 10, 0, 0),
                sender_phone="+1234567890",
                message_content="Hello from WhatsApp",
                message_type="text"
            ),
            WhatsAppMessage(
                id="wa_msg_2",
                timestamp=datetime(2024, 1, 15, 10, 5, 0),
                sender_phone="+1234567891",
                message_content="Image message",
                message_type="image",
                media_url="https://example.com/image.jpg",
                media_filename="image.jpg"
            )
        ]
        
        # Create mock emails
        emails = [
            Email(
                id="email_1",
                timestamp=datetime(2024, 1, 15, 9, 0, 0),
                sender_email="sender1@example.com",
                recipient_emails=["test1@example.com"],
                subject="Test Email 1",
                body_text="This is a test email",
                body_html="<p>This is a test email</p>",
                attachments=[],
                is_read=False,
                folder="INBOX"
            ),
            Email(
                id="email_2",
                timestamp=datetime(2024, 1, 15, 9, 30, 0),
                sender_email="sender2@example.com",
                recipient_emails=["test2@gmail.com"],
                subject="Test Email 2",
                body_text="Another test email",
                body_html="<p>Another test email</p>",
                attachments=[{"filename": "document.pdf", "size": 1024, "content_type": "application/pdf"}],
                is_read=True,
                folder="INBOX"
            )
        ]
        
        # Mock WhatsApp extractors
        mock_wa_extractor_1 = Mock()
        mock_wa_extractor_2 = Mock()
        mock_whatsapp_extractor.side_effect = [mock_wa_extractor_1, mock_wa_extractor_2]
        
        mock_wa_extractor_1.authenticate.return_value = True
        mock_wa_extractor_1.extract_messages.return_value = [whatsapp_messages[0]]
        mock_wa_extractor_1.download_media.return_value = None
        
        mock_wa_extractor_2.authenticate.return_value = True
        mock_wa_extractor_2.extract_messages.return_value = [whatsapp_messages[1]]
        mock_wa_extractor_2.download_media.return_value = "/path/to/downloaded/image.jpg"
        
        # Mock email extractors
        mock_email_extractor_1 = Mock()
        mock_email_extractor_2 = Mock()
        mock_email_extractor.side_effect = [mock_email_extractor_1, mock_email_extractor_2]
        
        mock_email_extractor_1.authenticate.return_value = True
        mock_email_extractor_1.extract_emails.return_value = [emails[0]]
        
        mock_email_extractor_2.authenticate.return_value = True
        mock_email_extractor_2.extract_emails.return_value = [emails[1]]
        
        # Run pipeline
        orchestrator = PipelineOrchestrator(self.config_file)
        results = orchestrator.run_extraction()
        
        # Verify results
        self.assertIn('whatsapp', results)
        self.assertIn('email', results)
        
        # Check WhatsApp results
        wa_result = results['whatsapp']
        self.assertTrue(wa_result.success)
        self.assertEqual(wa_result.messages_count, 2)
        self.assertEqual(wa_result.media_count, 1)  # One media file downloaded
        
        # Check email results
        email_result = results['email']
        self.assertTrue(email_result.success)
        self.assertEqual(email_result.messages_count, 2)
        self.assertEqual(email_result.media_count, 2)  # Counting attachments
        
        # Verify data files were created
        today = datetime.now().strftime('%Y-%m-%d')
        
        # Check WhatsApp data files
        wa_json_path = os.path.join(self.data_dir, 'whatsapp', today, 'data', 'whatsapp_messages.json')
        wa_csv_path = os.path.join(self.data_dir, 'whatsapp', today, 'data', 'whatsapp_messages.csv')
        
        self.assertTrue(os.path.exists(wa_json_path))
        self.assertTrue(os.path.exists(wa_csv_path))
        
        # Check email data files
        email_json_path = os.path.join(self.data_dir, 'email', today, 'data', 'email_messages.json')
        email_csv_path = os.path.join(self.data_dir, 'email', today, 'data', 'email_messages.csv')
        
        self.assertTrue(os.path.exists(email_json_path))
        self.assertTrue(os.path.exists(email_csv_path))
        
        # Verify JSON content
        with open(wa_json_path, 'r') as f:
            wa_data = json.load(f)
        self.assertEqual(len(wa_data), 2)
        
        with open(email_json_path, 'r') as f:
            email_data = json.load(f)
        self.assertEqual(len(email_data), 2)
    
    @patch('pipeline.whatsapp.whatsapp_extractor.WhatsAppExtractor')
    @patch('pipeline.email.email_extractor.EmailExtractor')
    def test_pipeline_with_partial_failures(self, mock_email_extractor, mock_whatsapp_extractor):
        """Test pipeline execution with some extractors failing"""
        # Mock WhatsApp extractor - first succeeds, second fails
        mock_wa_extractor_1 = Mock()
        mock_wa_extractor_2 = Mock()
        mock_whatsapp_extractor.side_effect = [mock_wa_extractor_1, mock_wa_extractor_2]
        
        mock_wa_extractor_1.authenticate.return_value = True
        mock_wa_extractor_1.extract_messages.return_value = [
            WhatsAppMessage(
                id="wa_msg_1",
                timestamp=datetime.now(),
                sender_phone="+1234567890",
                message_content="Success message",
                message_type="text"
            )
        ]
        
        mock_wa_extractor_2.authenticate.return_value = False  # Auth failure
        
        # Mock email extractor - authentication fails
        mock_email_extractor_1 = Mock()
        mock_email_extractor_2 = Mock()
        mock_email_extractor.side_effect = [mock_email_extractor_1, mock_email_extractor_2]
        
        mock_email_extractor_1.authenticate.return_value = False
        mock_email_extractor_2.authenticate.return_value = False
        
        # Run pipeline
        orchestrator = PipelineOrchestrator(self.config_file)
        results = orchestrator.run_extraction()
        
        # Verify results
        self.assertIn('whatsapp', results)
        self.assertIn('email', results)
        
        # WhatsApp should have partial success
        wa_result = results['whatsapp']
        self.assertTrue(wa_result.success)  # At least one extractor succeeded
        self.assertEqual(wa_result.messages_count, 1)
        self.assertGreater(len(wa_result.errors), 0)  # Should have errors from failed extractor
        
        # Email should fail completely
        email_result = results['email']
        self.assertFalse(email_result.success)
        self.assertEqual(email_result.messages_count, 0)
        self.assertGreater(len(email_result.errors), 0)
    
    def test_configuration_validation_integration(self):
        """Test configuration validation in real pipeline context"""
        # Create invalid configuration
        invalid_config = os.path.join(self.temp_dir, 'invalid_config.yaml')
        invalid_content = """
whatsapp:
  accounts:
    - api_token: test_token
      # Missing phone_number_id

email:
  accounts:
    - email: test@example.com
      # Missing imap_server and password

storage:
  base_path: /invalid/path/that/cannot/be/created
"""
        
        with open(invalid_config, 'w') as f:
            f.write(invalid_content)
        
        # Try to initialize pipeline
        orchestrator = PipelineOrchestrator(invalid_config)
        success = orchestrator.initialize()
        
        # Should fail due to validation errors
        self.assertFalse(success)
    
    def test_storage_integration_with_deduplication(self):
        """Test storage integration with data deduplication"""
        # Create storage manager
        storage_manager = StorageManager(self.data_dir)
        
        # Create initial data
        initial_messages = [
            WhatsAppMessage(
                id="msg_1",
                timestamp=datetime.now(),
                sender_phone="+1234567890",
                message_content="First message",
                message_type="text"
            ),
            WhatsAppMessage(
                id="msg_2",
                timestamp=datetime.now(),
                sender_phone="+1234567891",
                message_content="Second message",
                message_type="text"
            )
        ]
        
        # Save initial data
        result1 = storage_manager.save_whatsapp_data(initial_messages)
        
        # Create new data with some duplicates
        new_messages = [
            WhatsAppMessage(
                id="msg_1",  # Duplicate
                timestamp=datetime.now(),
                sender_phone="+1234567890",
                message_content="First message",
                message_type="text"
            ),
            WhatsAppMessage(
                id="msg_3",  # New
                timestamp=datetime.now(),
                sender_phone="+1234567892",
                message_content="Third message",
                message_type="text"
            )
        ]
        
        # Save new data
        result2 = storage_manager.save_whatsapp_data(new_messages)
        
        # Verify deduplication worked
        with open(result2['json'], 'r') as f:
            all_data = json.load(f)
        
        # Should have 3 unique messages (2 initial + 1 new)
        self.assertEqual(len(all_data), 3)
        
        # Verify all unique IDs are present
        ids = [msg['id'] for msg in all_data]
        self.assertIn('msg_1', ids)
        self.assertIn('msg_2', ids)
        self.assertIn('msg_3', ids)
    
    def test_error_handling_integration(self):
        """Test error handling integration across components"""
        # Create logger and error handler
        logger = PipelineLogger({'log_dir': self.temp_dir})
        logger.setup_logging()
        error_handler = ErrorHandler(logger.logger)
        
        # Test various error scenarios
        test_errors = [
            ValueError("Data processing error"),
            ConnectionError("Network error"),
            PermissionError("Storage error"),
            FileNotFoundError("Configuration error")
        ]
        
        for error in test_errors:
            error_info = error_handler.handle_error(error, {
                'component': 'test_component',
                'operation': 'test_operation'
            }, raise_on_critical=False)
            
            # Verify error was categorized and logged
            self.assertIsNotNone(error_info)
            self.assertIn(error_info, error_handler.error_history)
        
        # Get error summary
        summary = error_handler.get_error_summary()
        self.assertEqual(summary['total_errors'], 4)
        self.assertGreater(len(summary['by_category']), 0)
    
    @patch('smtplib.SMTP')
    def test_notification_integration(self, mock_smtp):
        """Test notification system integration"""
        # Setup notification config
        config = {
            'notifications': {
                'enabled': True,
                'email': {
                    'enabled': True,
                    'smtp_server': 'smtp.test.com',
                    'smtp_port': 587,
                    'username': 'test@test.com',
                    'password': 'test_password',
                    'to_emails': ['recipient@test.com'],
                    'on_success': True,
                    'on_error': True
                }
            }
        }
        
        # Mock SMTP
        mock_server = Mock()
        mock_smtp.return_value.__enter__.return_value = mock_server
        
        # Create notification manager
        notification_manager = NotificationManager(config)
        
        # Test extraction complete notification
        results = {
            'whatsapp': {
                'success': True,
                'messages_count': 10,
                'media_count': 5,
                'errors': []
            },
            'email': {
                'success': False,
                'messages_count': 0,
                'media_count': 0,
                'errors': ['Authentication failed']
            }
        }
        
        success = notification_manager.send_extraction_complete_notification(results)
        
        # Verify notification was sent
        self.assertTrue(success)
        mock_server.send_message.assert_called_once()
        
        # Test error notification
        error_info = {
            'component': 'whatsapp_extractor',
            'message': 'API rate limit exceeded',
            'severity': 'medium'
        }
        
        success = notification_manager.send_error_notification(error_info)
        self.assertTrue(success)


class TestEndToEndWorkflows(unittest.TestCase):
    """End-to-end tests for complete workflows"""
    
    def setUp(self):
        """Set up test environment"""
        self.temp_dir = tempfile.mkdtemp()
        self.config_file = os.path.join(self.temp_dir, 'e2e_config.yaml')
        self.data_dir = os.path.join(self.temp_dir, 'data')
        
        # Create comprehensive test configuration
        config_content = f"""
whatsapp:
  accounts:
    - api_token: test_business_token
      phone_number_id: test_phone_number_id

email:
  accounts:
    - email: test@example.com
      password: test_password
      imap_server: imap.example.com
      imap_port: 993
      use_ssl: true

storage:
  base_path: {self.data_dir}
  create_date_folders: true
  json_format: true
  csv_format: true
  media_folder: media

logging:
  level: DEBUG
  file_logging: true
  console_logging: true
  log_file: {os.path.join(self.temp_dir, 'e2e.log')}
  max_file_size: 1MB
  backup_count: 3

notifications:
  enabled: true
  email:
    enabled: false  # Disable for testing
  webhook:
    enabled: false
  slack:
    enabled: false
"""
        
        with open(self.config_file, 'w') as f:
            f.write(config_content)
    
    def tearDown(self):
        """Clean up test environment"""
        shutil.rmtree(self.temp_dir)
    
    @patch('pipeline.whatsapp.whatsapp_extractor.WhatsAppExtractor')
    @patch('pipeline.email.email_extractor.EmailExtractor')
    def test_complete_extraction_workflow(self, mock_email_extractor, mock_whatsapp_extractor):
        """Test complete extraction workflow from start to finish"""
        # Create realistic test data
        whatsapp_messages = self._create_test_whatsapp_messages()
        emails = self._create_test_emails()
        
        # Mock extractors with realistic behavior
        self._setup_mock_extractors(
            mock_whatsapp_extractor, 
            mock_email_extractor, 
            whatsapp_messages, 
            emails
        )
        
        # Initialize and run pipeline
        orchestrator = PipelineOrchestrator(self.config_file)
        
        # Verify initialization
        self.assertTrue(orchestrator.initialize())
        self.assertTrue(orchestrator._initialized)
        
        # Run extraction
        results = orchestrator.run_extraction()
        
        # Verify results structure
        self.assertIsInstance(results, dict)
        self.assertIn('whatsapp', results)
        self.assertIn('email', results)
        
        # Verify WhatsApp results
        wa_result = results['whatsapp']
        self.assertIsInstance(wa_result, ExtractionResult)
        self.assertTrue(wa_result.success)
        self.assertEqual(wa_result.source, 'whatsapp')
        self.assertGreater(wa_result.messages_count, 0)
        self.assertGreaterEqual(wa_result.execution_time, 0)
        
        # Verify email results
        email_result = results['email']
        self.assertIsInstance(email_result, ExtractionResult)
        self.assertTrue(email_result.success)
        self.assertEqual(email_result.source, 'email')
        self.assertGreater(email_result.messages_count, 0)
        
        # Verify file system structure
        self._verify_output_structure()
        
        # Verify data integrity
        self._verify_data_integrity(results)
        
        # Verify logging
        self._verify_logging()
    
    def test_large_dataset_handling(self):
        """Test pipeline performance with large datasets"""
        # This would be a performance test with large amounts of data
        # For now, we'll simulate it with a reasonable dataset
        
        large_dataset_size = 1000
        
        # Create large dataset
        messages = []
        for i in range(large_dataset_size):
            messages.append(WhatsAppMessage(
                id=f"msg_{i}",
                timestamp=datetime.now() - timedelta(minutes=i),
                sender_phone=f"+123456789{i % 10}",
                message_content=f"Test message {i}",
                message_type="text"
            ))
        
        # Test storage performance
        storage_manager = StorageManager(self.data_dir)
        
        start_time = datetime.now()
        result = storage_manager.save_whatsapp_data(messages)
        end_time = datetime.now()
        
        processing_time = (end_time - start_time).total_seconds()
        
        # Verify performance (should complete within reasonable time)
        self.assertLess(processing_time, 10.0)  # Should complete within 10 seconds
        
        # Verify all data was saved
        with open(result['json'], 'r') as f:
            saved_data = json.load(f)
        
        self.assertEqual(len(saved_data), large_dataset_size)
    
    def test_multi_account_scenario(self):
        """Test realistic multi-account extraction scenario"""
        # Create config with multiple accounts
        multi_config = os.path.join(self.temp_dir, 'multi_config.yaml')
        multi_content = f"""
whatsapp:
  accounts:
    - api_token: business_token_1
      phone_number_id: phone_1
    - twilio_account_sid: twilio_sid_1
      twilio_auth_token: twilio_token_1
      twilio_whatsapp_number: +1111111111
    - api_token: business_token_2
      phone_number_id: phone_2

email:
  accounts:
    - email: account1@company.com
      password: password1
      imap_server: imap.company.com
    - email: account2@gmail.com
      imap_server: imap.gmail.com
      auth_method: oauth2
      client_id: gmail_client_id
      client_secret: gmail_client_secret
      refresh_token: gmail_refresh_token
    - email: account3@outlook.com
      password: password3
      imap_server: outlook.office365.com

storage:
  base_path: {self.data_dir}

logging:
  level: INFO
  file_logging: true

notifications:
  enabled: false
"""
        
        with open(multi_config, 'w') as f:
            f.write(multi_content)
        
        # Test configuration loading
        config_manager = ConfigManager(multi_config)
        config = config_manager.load_config()
        
        # Verify multiple accounts are loaded
        whatsapp_configs = config_manager.get_whatsapp_configs()
        email_configs = config_manager.get_email_configs()
        
        self.assertEqual(len(whatsapp_configs), 3)
        self.assertEqual(len(email_configs), 3)
        
        # Verify different authentication methods
        self.assertEqual(whatsapp_configs[0].get('api_token'), 'business_token_1')
        self.assertEqual(whatsapp_configs[1].get('twilio_account_sid'), 'twilio_sid_1')
        self.assertEqual(email_configs[1].get('auth_method'), 'oauth2')
    
    def test_error_recovery_workflow(self):
        """Test error recovery and graceful degradation"""
        # Create error handler
        logger = PipelineLogger({'log_dir': self.temp_dir})
        logger.setup_logging()
        error_handler = ErrorHandler(logger.logger)
        
        # Simulate various error scenarios
        errors_to_test = [
            (ConnectionError("Network timeout"), "network_operation"),
            (ValueError("Invalid data format"), "data_processing"),
            (PermissionError("Access denied"), "file_operation"),
            (Exception("Unknown error"), "unknown_operation")
        ]
        
        for error, operation in errors_to_test:
            # Test error handling
            error_info = error_handler.handle_error(error, {
                'component': 'test_component',
                'operation': operation
            }, raise_on_critical=False)
            
            # Verify error was properly categorized
            self.assertIsNotNone(error_info.category)
            self.assertIsNotNone(error_info.severity)
        
        # Test error summary
        summary = error_handler.get_error_summary()
        self.assertEqual(summary['total_errors'], len(errors_to_test))
        
        # Test should continue processing logic
        self.assertTrue(error_handler.should_continue_processing(max_errors=10))
        self.assertFalse(error_handler.should_continue_processing(max_errors=2))
    
    def _create_test_whatsapp_messages(self):
        """Create realistic test WhatsApp messages"""
        return [
            WhatsAppMessage(
                id="wa_001",
                timestamp=datetime(2024, 1, 15, 10, 0, 0),
                sender_phone="+1234567890",
                message_content="Hello! How are you?",
                message_type="text"
            ),
            WhatsAppMessage(
                id="wa_002",
                timestamp=datetime(2024, 1, 15, 10, 5, 0),
                sender_phone="+1234567891",
                message_content="Check out this image",
                message_type="image",
                media_url="https://example.com/image1.jpg",
                media_filename="vacation_photo.jpg",
                media_size=1024000
            ),
            WhatsAppMessage(
                id="wa_003",
                timestamp=datetime(2024, 1, 15, 10, 10, 0),
                sender_phone="+1234567892",
                message_content="Voice message",
                message_type="audio",
                media_url="https://example.com/audio1.mp3",
                media_filename="voice_note.mp3",
                media_size=512000
            )
        ]
    
    def _create_test_emails(self):
        """Create realistic test emails"""
        return [
            Email(
                id="email_001",
                timestamp=datetime(2024, 1, 15, 9, 0, 0),
                sender_email="colleague@company.com",
                recipient_emails=["test@example.com"],
                subject="Project Update",
                body_text="Here's the latest update on our project...",
                body_html="<p>Here's the latest update on our project...</p>",
                attachments=[
                    {
                        "filename": "project_report.pdf",
                        "size": 2048000,
                        "content_type": "application/pdf"
                    }
                ],
                is_read=False,
                folder="INBOX"
            ),
            Email(
                id="email_002",
                timestamp=datetime(2024, 1, 15, 9, 30, 0),
                sender_email="newsletter@service.com",
                recipient_emails=["test@example.com"],
                subject="Weekly Newsletter",
                body_text="This week's highlights...",
                body_html="<html><body><h1>This week's highlights...</h1></body></html>",
                attachments=[],
                is_read=True,
                folder="INBOX"
            )
        ]
    
    def _setup_mock_extractors(self, mock_whatsapp_extractor, mock_email_extractor, 
                              whatsapp_messages, emails):
        """Setup mock extractors with realistic behavior"""
        # Mock WhatsApp extractor
        mock_wa_extractor = Mock()
        mock_whatsapp_extractor.return_value = mock_wa_extractor
        mock_wa_extractor.authenticate.return_value = True
        mock_wa_extractor.extract_messages.return_value = whatsapp_messages
        mock_wa_extractor.download_media.return_value = "/path/to/media/file"
        
        # Mock email extractor
        mock_email_ext = Mock()
        mock_email_extractor.return_value = mock_email_ext
        mock_email_ext.authenticate.return_value = True
        mock_email_ext.extract_emails.return_value = emails
    
    def _verify_output_structure(self):
        """Verify the output directory structure is correct"""
        today = datetime.now().strftime('%Y-%m-%d')
        
        # Check base structure
        self.assertTrue(os.path.exists(self.data_dir))
        
        # Check WhatsApp structure
        wa_base = os.path.join(self.data_dir, 'whatsapp', today)
        self.assertTrue(os.path.exists(wa_base))
        self.assertTrue(os.path.exists(os.path.join(wa_base, 'data')))
        self.assertTrue(os.path.exists(os.path.join(wa_base, 'media')))
        
        # Check email structure
        email_base = os.path.join(self.data_dir, 'email', today)
        self.assertTrue(os.path.exists(email_base))
        self.assertTrue(os.path.exists(os.path.join(email_base, 'data')))
        self.assertTrue(os.path.exists(os.path.join(email_base, 'media')))
    
    def _verify_data_integrity(self, results):
        """Verify data integrity in saved files"""
        today = datetime.now().strftime('%Y-%m-%d')
        
        # Verify WhatsApp data
        if 'whatsapp' in results and results['whatsapp'].success:
            wa_json = os.path.join(self.data_dir, 'whatsapp', today, 'data', 'whatsapp_messages.json')
            wa_csv = os.path.join(self.data_dir, 'whatsapp', today, 'data', 'whatsapp_messages.csv')
            
            if os.path.exists(wa_json):
                with open(wa_json, 'r') as f:
                    wa_data = json.load(f)
                self.assertIsInstance(wa_data, list)
                self.assertEqual(len(wa_data), results['whatsapp'].messages_count)
            
            if os.path.exists(wa_csv):
                with open(wa_csv, 'r') as f:
                    reader = csv.DictReader(f)
                    csv_data = list(reader)
                self.assertEqual(len(csv_data), results['whatsapp'].messages_count)
        
        # Verify email data
        if 'email' in results and results['email'].success:
            email_json = os.path.join(self.data_dir, 'email', today, 'data', 'email_messages.json')
            email_csv = os.path.join(self.data_dir, 'email', today, 'data', 'email_messages.csv')
            
            if os.path.exists(email_json):
                with open(email_json, 'r') as f:
                    email_data = json.load(f)
                self.assertIsInstance(email_data, list)
                self.assertEqual(len(email_data), results['email'].messages_count)
    
    def _verify_logging(self):
        """Verify logging functionality"""
        log_file = os.path.join(self.temp_dir, 'e2e.log')
        
        if os.path.exists(log_file):
            with open(log_file, 'r') as f:
                log_content = f.read()
            
            # Verify key log messages are present
            self.assertIn('Pipeline initialization completed successfully', log_content)
            self.assertIn('Starting extraction pipeline', log_content)
            self.assertIn('Extraction pipeline completed', log_content)


class TestPerformanceAndScalability(unittest.TestCase):
    """Performance and scalability tests"""
    
    def setUp(self):
        """Set up performance test environment"""
        self.temp_dir = tempfile.mkdtemp()
        self.data_dir = os.path.join(self.temp_dir, 'perf_data')
    
    def tearDown(self):
        """Clean up performance test environment"""
        shutil.rmtree(self.temp_dir)
    
    def test_storage_performance_large_dataset(self):
        """Test storage performance with large datasets"""
        storage_manager = StorageManager(self.data_dir)
        
        # Create large dataset
        large_dataset = []
        dataset_size = 5000
        
        for i in range(dataset_size):
            large_dataset.append(WhatsAppMessage(
                id=f"perf_msg_{i}",
                timestamp=datetime.now() - timedelta(seconds=i),
                sender_phone=f"+123456{i % 10000:04d}",
                message_content=f"Performance test message {i} with some additional content to make it more realistic",
                message_type="text"
            ))
        
        # Measure storage performance
        start_time = datetime.now()
        result = storage_manager.save_whatsapp_data(large_dataset)
        end_time = datetime.now()
        
        processing_time = (end_time - start_time).total_seconds()
        
        # Performance assertions
        self.assertLess(processing_time, 30.0)  # Should complete within 30 seconds
        
        # Verify data integrity
        with open(result['json'], 'r') as f:
            saved_data = json.load(f)
        
        self.assertEqual(len(saved_data), dataset_size)
        
        # Test CSV performance
        with open(result['csv'], 'r') as f:
            reader = csv.DictReader(f)
            csv_data = list(reader)
        
        self.assertEqual(len(csv_data), dataset_size)
    
    def test_deduplication_performance(self):
        """Test deduplication performance with large datasets"""
        storage_manager = StorageManager(self.data_dir)
        
        # Create initial dataset
        initial_size = 2000
        initial_data = []
        
        for i in range(initial_size):
            initial_data.append(WhatsAppMessage(
                id=f"dedup_msg_{i}",
                timestamp=datetime.now() - timedelta(seconds=i),
                sender_phone=f"+123456{i % 100:04d}",
                message_content=f"Deduplication test message {i}",
                message_type="text"
            ))
        
        # Save initial data
        storage_manager.save_whatsapp_data(initial_data)
        
        # Create new dataset with 50% duplicates
        new_size = 1000
        new_data = []
        
        # Add duplicates (first 500)
        for i in range(500):
            new_data.append(WhatsAppMessage(
                id=f"dedup_msg_{i}",  # Duplicate ID
                timestamp=datetime.now() - timedelta(seconds=i),
                sender_phone=f"+123456{i % 100:04d}",
                message_content=f"Deduplication test message {i}",
                message_type="text"
            ))
        
        # Add new messages (next 500)
        for i in range(500, 1000):
            new_data.append(WhatsAppMessage(
                id=f"dedup_msg_{initial_size + i}",  # New ID
                timestamp=datetime.now() - timedelta(seconds=i),
                sender_phone=f"+123456{i % 100:04d}",
                message_content=f"New deduplication test message {i}",
                message_type="text"
            ))
        
        # Measure deduplication performance
        start_time = datetime.now()
        result = storage_manager.save_whatsapp_data(new_data)
        end_time = datetime.now()
        
        processing_time = (end_time - start_time).total_seconds()
        
        # Performance assertions
        self.assertLess(processing_time, 15.0)  # Should complete within 15 seconds
        
        # Verify deduplication worked correctly
        with open(result['json'], 'r') as f:
            final_data = json.load(f)
        
        # Should have initial_size + 500 new messages (duplicates removed)
        expected_size = initial_size + 500
        self.assertEqual(len(final_data), expected_size)
    
    def test_concurrent_access_simulation(self):
        """Test concurrent access patterns (simulated)"""
        storage_manager = StorageManager(self.data_dir)
        
        # Simulate multiple extraction processes
        datasets = []
        
        # Create multiple small datasets (simulating concurrent extractors)
        for batch in range(5):
            batch_data = []
            for i in range(200):
                batch_data.append(WhatsAppMessage(
                    id=f"concurrent_msg_{batch}_{i}",
                    timestamp=datetime.now() - timedelta(seconds=i),
                    sender_phone=f"+12345{batch}{i % 100:03d}",
                    message_content=f"Concurrent test message {batch}-{i}",
                    message_type="text"
                ))
            datasets.append(batch_data)
        
        # Process datasets sequentially (simulating concurrent access)
        results = []
        total_start_time = datetime.now()
        
        for i, dataset in enumerate(datasets):
            start_time = datetime.now()
            result = storage_manager.save_whatsapp_data(dataset)
            end_time = datetime.now()
            
            processing_time = (end_time - start_time).total_seconds()
            results.append({
                'batch': i,
                'processing_time': processing_time,
                'result': result
            })
        
        total_end_time = datetime.now()
        total_time = (total_end_time - total_start_time).total_seconds()
        
        # Performance assertions
        self.assertLess(total_time, 20.0)  # Total processing should be under 20 seconds
        
        # Verify all batches were processed
        self.assertEqual(len(results), 5)
        
        # Verify final data integrity
        final_result = results[-1]['result']
        with open(final_result['json'], 'r') as f:
            final_data = json.load(f)
        
        # Should have all messages from all batches
        expected_total = sum(len(dataset) for dataset in datasets)
        self.assertEqual(len(final_data), expected_total)


if __name__ == '__main__':
    unittest.main()