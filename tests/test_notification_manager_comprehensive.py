"""
Comprehensive unit tests for NotificationManager
"""

import unittest
from unittest.mock import Mock, patch, MagicMock
import smtplib
import requests
from datetime import datetime

from pipeline.utils.notification_manager import NotificationManager


class TestNotificationManager(unittest.TestCase):
    """Test cases for NotificationManager class"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.config = {
            'notifications': {
                'enabled': True,
                'email': {
                    'enabled': True,
                    'smtp_server': 'smtp.gmail.com',
                    'smtp_port': 587,
                    'username': 'test@example.com',
                    'password': 'test_password',
                    'from_email': 'test@example.com',
                    'to_emails': ['recipient1@example.com', 'recipient2@example.com'],
                    'on_success': True,
                    'on_error': True
                },
                'webhook': {
                    'enabled': True,
                    'url': 'https://webhook.example.com/notify',
                    'headers': {'Content-Type': 'application/json'},
                    'timeout': 30
                },
                'slack': {
                    'enabled': True,
                    'webhook_url': 'https://hooks.slack.com/services/test',
                    'channel': '#pipeline',
                    'username': 'Pipeline Bot'
                }
            }
        }
        self.logger = Mock()
        self.notification_manager = NotificationManager(self.config, self.logger)
    
    def test_init_with_config(self):
        """Test NotificationManager initialization with config"""
        self.assertEqual(self.notification_manager.config, self.config)
        self.assertEqual(self.notification_manager.logger, self.logger)
        self.assertEqual(
            self.notification_manager.notification_config, 
            self.config['notifications']
        )
    
    def test_init_without_notifications_config(self):
        """Test initialization without notifications config"""
        config_without_notifications = {}
        manager = NotificationManager(config_without_notifications)
        
        self.assertEqual(manager.notification_config, {})
    
    def test_should_send_email_notification_success(self):
        """Test email notification decision for successful extraction"""
        results = {
            'whatsapp': {'success': True, 'messages_count': 10, 'errors': []},
            'email': {'success': True, 'messages_count': 5, 'errors': []}
        }
        
        should_send = self.notification_manager._should_send_email_notification(results)
        self.assertTrue(should_send)
    
    def test_should_send_email_notification_error(self):
        """Test email notification decision for extraction with errors"""
        results = {
            'whatsapp': {'success': False, 'messages_count': 0, 'errors': ['Auth failed']},
            'email': {'success': True, 'messages_count': 5, 'errors': []}
        }
        
        should_send = self.notification_manager._should_send_email_notification(results)
        self.assertTrue(should_send)
    
    def test_should_send_email_notification_disabled(self):
        """Test email notification when disabled"""
        self.config['notifications']['email']['enabled'] = False
        
        results = {
            'whatsapp': {'success': True, 'messages_count': 10, 'errors': []}
        }
        
        should_send = self.notification_manager._should_send_email_notification(results)
        self.assertFalse(should_send)
    
    def test_should_send_email_notification_success_disabled(self):
        """Test email notification when success notifications are disabled"""
        self.config['notifications']['email']['on_success'] = False
        
        results = {
            'whatsapp': {'success': True, 'messages_count': 10, 'errors': []}
        }
        
        should_send = self.notification_manager._should_send_email_notification(results)
        self.assertFalse(should_send)
    
    def test_should_send_webhook_notification(self):
        """Test webhook notification decision"""
        self.assertTrue(self.notification_manager._should_send_webhook_notification())
        
        # Test when disabled
        self.config['notifications']['webhook']['enabled'] = False
        self.assertFalse(self.notification_manager._should_send_webhook_notification())
        
        # Test when no URL
        self.config['notifications']['webhook']['enabled'] = True
        self.config['notifications']['webhook']['url'] = ''
        self.assertFalse(self.notification_manager._should_send_webhook_notification())
    
    def test_should_send_slack_notification(self):
        """Test Slack notification decision"""
        self.assertTrue(self.notification_manager._should_send_slack_notification())
        
        # Test when disabled
        self.config['notifications']['slack']['enabled'] = False
        self.assertFalse(self.notification_manager._should_send_slack_notification())
        
        # Test when no webhook URL
        self.config['notifications']['slack']['enabled'] = True
        self.config['notifications']['slack']['webhook_url'] = ''
        self.assertFalse(self.notification_manager._should_send_slack_notification())
    
    @patch('smtplib.SMTP')
    def test_send_email_notification_success(self, mock_smtp_class):
        """Test successful email notification sending"""
        mock_server = Mock()
        mock_smtp_class.return_value.__enter__.return_value = mock_server
        
        result = self.notification_manager._send_email_notification(
            "Test Subject", 
            "Test Body"
        )
        
        self.assertTrue(result)
        mock_smtp_class.assert_called_once_with('smtp.gmail.com', 587)
        mock_server.starttls.assert_called_once()
        mock_server.login.assert_called_once_with('test@example.com', 'test_password')
        mock_server.send_message.assert_called_once()
        self.logger.info.assert_called()
    
    @patch('smtplib.SMTP')
    def test_send_email_notification_failure(self, mock_smtp_class):
        """Test email notification sending failure"""
        mock_smtp_class.side_effect = smtplib.SMTPException("SMTP Error")
        
        result = self.notification_manager._send_email_notification(
            "Test Subject", 
            "Test Body"
        )
        
        self.assertFalse(result)
        self.logger.error.assert_called()
    
    def test_send_email_notification_incomplete_config(self):
        """Test email notification with incomplete configuration"""
        # Remove required config
        del self.config['notifications']['email']['username']
        
        result = self.notification_manager._send_email_notification(
            "Test Subject", 
            "Test Body"
        )
        
        self.assertFalse(result)
        self.logger.warning.assert_called()
    
    @patch('requests.post')
    def test_send_webhook_notification_success(self, mock_post):
        """Test successful webhook notification sending"""
        mock_response = Mock()
        mock_response.raise_for_status.return_value = None
        mock_post.return_value = mock_response
        
        payload = {'test': 'data'}
        result = self.notification_manager._send_webhook_notification(payload)
        
        self.assertTrue(result)
        mock_post.assert_called_once_with(
            'https://webhook.example.com/notify',
            json=payload,
            headers={'Content-Type': 'application/json'},
            timeout=30
        )
        self.logger.info.assert_called()
    
    @patch('requests.post')
    def test_send_webhook_notification_failure(self, mock_post):
        """Test webhook notification sending failure"""
        mock_post.side_effect = requests.exceptions.RequestException("Request failed")
        
        payload = {'test': 'data'}
        result = self.notification_manager._send_webhook_notification(payload)
        
        self.assertFalse(result)
        self.logger.error.assert_called()
    
    def test_send_webhook_notification_no_url(self):
        """Test webhook notification with no URL configured"""
        self.config['notifications']['webhook']['url'] = ''
        
        payload = {'test': 'data'}
        result = self.notification_manager._send_webhook_notification(payload)
        
        self.assertFalse(result)
    
    @patch('requests.post')
    def test_send_slack_notification_success(self, mock_post):
        """Test successful Slack notification sending"""
        mock_response = Mock()
        mock_response.raise_for_status.return_value = None
        mock_post.return_value = mock_response
        
        result = self.notification_manager._send_slack_notification("Test message")
        
        self.assertTrue(result)
        
        expected_payload = {
            'text': 'Test message',
            'channel': '#pipeline',
            'username': 'Pipeline Bot'
        }
        
        mock_post.assert_called_once_with(
            'https://hooks.slack.com/services/test',
            json=expected_payload,
            timeout=30
        )
        self.logger.info.assert_called()
    
    @patch('requests.post')
    def test_send_slack_notification_failure(self, mock_post):
        """Test Slack notification sending failure"""
        mock_post.side_effect = requests.exceptions.RequestException("Request failed")
        
        result = self.notification_manager._send_slack_notification("Test message")
        
        self.assertFalse(result)
        self.logger.error.assert_called()
    
    def test_send_slack_notification_no_webhook_url(self):
        """Test Slack notification with no webhook URL configured"""
        self.config['notifications']['slack']['webhook_url'] = ''
        
        result = self.notification_manager._send_slack_notification("Test message")
        
        self.assertFalse(result)
    
    def test_format_extraction_complete_message_success(self):
        """Test formatting extraction complete message for successful extraction"""
        results = {
            'whatsapp': {
                'success': True,
                'messages_count': 15,
                'media_count': 5,
                'errors': []
            },
            'email': {
                'success': True,
                'messages_count': 8,
                'media_count': 2,
                'errors': []
            }
        }
        
        subject, body = self.notification_manager._format_extraction_complete_message(results)
        
        self.assertIn("✅", subject)
        self.assertIn("Successfully", subject)
        self.assertIn("✅ Successful Extractions:", body)
        self.assertIn("Whatsapp: 15 messages, 5 media files", body)
        self.assertIn("Email: 8 messages, 2 media files", body)
        self.assertIn("Total Messages: 23", body)
        self.assertIn("Total Media Files: 7", body)
    
    def test_format_extraction_complete_message_with_errors(self):
        """Test formatting extraction complete message with errors"""
        results = {
            'whatsapp': {
                'success': True,
                'messages_count': 10,
                'media_count': 3,
                'errors': []
            },
            'email': {
                'success': False,
                'messages_count': 0,
                'media_count': 0,
                'errors': ['Authentication failed']
            }
        }
        
        subject, body = self.notification_manager._format_extraction_complete_message(results)
        
        self.assertIn("⚠️", subject)
        self.assertIn("Errors", subject)
        self.assertIn("✅ Successful Extractions:", body)
        self.assertIn("❌ Failed Extractions:", body)
        self.assertIn("Email: Authentication failed", body)
    
    def test_format_error_message(self):
        """Test formatting error notification message"""
        error_info = {
            'component': 'whatsapp_extractor',
            'message': 'API authentication failed',
            'severity': 'high',
            'context': {
                'api_endpoint': 'https://graph.facebook.com',
                'status_code': 401
            }
        }
        
        subject, body = self.notification_manager._format_error_message(error_info)
        
        self.assertIn("🚨", subject)
        self.assertIn("whatsapp_extractor", subject)
        self.assertIn("Component: whatsapp_extractor", body)
        self.assertIn("Error: API authentication failed", body)
        self.assertIn("Severity: High", body)
        self.assertIn("Additional Context:", body)
        self.assertIn("api_endpoint: https://graph.facebook.com", body)
        self.assertIn("status_code: 401", body)
    
    def test_format_error_message_medium_severity(self):
        """Test formatting error message with medium severity"""
        error_info = {
            'component': 'email_extractor',
            'message': 'Connection timeout',
            'severity': 'medium'
        }
        
        subject, body = self.notification_manager._format_error_message(error_info)
        
        self.assertIn("⚠️", subject)
        self.assertIn("email_extractor", subject)
    
    def test_format_webhook_payload(self):
        """Test formatting webhook payload"""
        data = {'test': 'data', 'count': 5}
        
        payload = self.notification_manager._format_webhook_payload('test_event', data)
        
        self.assertEqual(payload['event'], 'test_event')
        self.assertEqual(payload['data'], data)
        self.assertEqual(payload['source'], 'data-extraction-pipeline')
        self.assertIn('timestamp', payload)
    
    def test_format_slack_message_success(self):
        """Test formatting Slack message for successful extraction"""
        results = {
            'whatsapp': {
                'success': True,
                'messages_count': 12,
                'media_count': 4,
                'errors': []
            },
            'email': {
                'success': True,
                'messages_count': 6,
                'media_count': 1,
                'errors': []
            }
        }
        
        message = self.notification_manager._format_slack_message(results)
        
        self.assertIn("✅", message)
        self.assertIn("Completed Successfully", message)
        self.assertIn("📱 Whatsapp: 12 messages, 4 media", message)
        self.assertIn("📧 Email: 6 messages, 1 media", message)
        self.assertIn("📊 Total: 18 messages, 5 media files", message)
    
    def test_format_slack_message_with_errors(self):
        """Test formatting Slack message with errors"""
        results = {
            'whatsapp': {
                'success': False,
                'messages_count': 0,
                'media_count': 0,
                'errors': ['Rate limit exceeded']
            },
            'email': {
                'success': True,
                'messages_count': 8,
                'media_count': 2,
                'errors': []
            }
        }
        
        message = self.notification_manager._format_slack_message(results)
        
        self.assertIn("⚠️", message)
        self.assertIn("Completed with Errors", message)
        self.assertIn("❌ Whatsapp: Failed", message)
        self.assertIn("📧 Email: 8 messages, 2 media", message)
    
    @patch.object(NotificationManager, '_send_email_notification')
    @patch.object(NotificationManager, '_send_webhook_notification')
    @patch.object(NotificationManager, '_send_slack_notification')
    def test_send_extraction_complete_notification_all_enabled(self, mock_slack, mock_webhook, mock_email):
        """Test sending extraction complete notification with all methods enabled"""
        mock_email.return_value = True
        mock_webhook.return_value = True
        mock_slack.return_value = True
        
        results = {
            'whatsapp': {'success': True, 'messages_count': 10, 'errors': []}
        }
        
        result = self.notification_manager.send_extraction_complete_notification(results)
        
        self.assertTrue(result)
        mock_email.assert_called_once()
        mock_webhook.assert_called_once()
        mock_slack.assert_called_once()
    
    @patch.object(NotificationManager, '_send_email_notification')
    def test_send_extraction_complete_notification_partial_failure(self, mock_email):
        """Test extraction complete notification with partial sending failure"""
        mock_email.return_value = False  # Email fails
        
        # Disable other notification methods
        self.config['notifications']['webhook']['enabled'] = False
        self.config['notifications']['slack']['enabled'] = False
        
        results = {
            'whatsapp': {'success': True, 'messages_count': 10, 'errors': []}
        }
        
        result = self.notification_manager.send_extraction_complete_notification(results)
        
        self.assertFalse(result)  # Should return False if all attempted notifications fail
    
    def test_send_extraction_complete_notification_disabled(self):
        """Test extraction complete notification when notifications are disabled"""
        self.config['notifications']['enabled'] = False
        
        results = {
            'whatsapp': {'success': True, 'messages_count': 10, 'errors': []}
        }
        
        result = self.notification_manager.send_extraction_complete_notification(results)
        
        self.assertTrue(result)  # Should return True when notifications are disabled
    
    @patch.object(NotificationManager, '_send_email_notification')
    @patch.object(NotificationManager, '_send_webhook_notification')
    @patch.object(NotificationManager, '_send_slack_notification')
    def test_send_error_notification(self, mock_slack, mock_webhook, mock_email):
        """Test sending error notification"""
        mock_email.return_value = True
        mock_webhook.return_value = True
        mock_slack.return_value = True
        
        error_info = {
            'component': 'test_component',
            'message': 'Test error occurred',
            'severity': 'high'
        }
        
        result = self.notification_manager.send_error_notification(error_info)
        
        self.assertTrue(result)
        mock_email.assert_called_once()
        mock_webhook.assert_called_once()
        mock_slack.assert_called_once()
    
    def test_send_error_notification_disabled(self):
        """Test error notification when notifications are disabled"""
        self.config['notifications']['enabled'] = False
        
        error_info = {
            'component': 'test_component',
            'message': 'Test error occurred'
        }
        
        result = self.notification_manager.send_error_notification(error_info)
        
        self.assertTrue(result)  # Should return True when notifications are disabled
    
    @patch.object(NotificationManager, '_send_email_notification')
    def test_send_error_notification_email_on_error_disabled(self, mock_email):
        """Test error notification when email on_error is disabled"""
        self.config['notifications']['email']['on_error'] = False
        self.config['notifications']['webhook']['enabled'] = False
        self.config['notifications']['slack']['enabled'] = False
        
        error_info = {
            'component': 'test_component',
            'message': 'Test error occurred'
        }
        
        result = self.notification_manager.send_error_notification(error_info)
        
        self.assertTrue(result)  # Should return True when no notifications are configured
        mock_email.assert_not_called()


class TestNotificationManagerIntegration(unittest.TestCase):
    """Integration tests for NotificationManager"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.minimal_config = {
            'notifications': {
                'enabled': True,
                'email': {
                    'enabled': False
                },
                'webhook': {
                    'enabled': False
                },
                'slack': {
                    'enabled': False
                }
            }
        }
        self.notification_manager = NotificationManager(self.minimal_config)
    
    def test_no_notifications_configured(self):
        """Test behavior when no notification methods are configured"""
        results = {
            'whatsapp': {'success': True, 'messages_count': 10, 'errors': []}
        }
        
        # Should return True even when no notifications are sent
        result = self.notification_manager.send_extraction_complete_notification(results)
        self.assertTrue(result)
    
    def test_notifications_globally_disabled(self):
        """Test behavior when notifications are globally disabled"""
        self.minimal_config['notifications']['enabled'] = False
        
        results = {
            'whatsapp': {'success': True, 'messages_count': 10, 'errors': []}
        }
        
        result = self.notification_manager.send_extraction_complete_notification(results)
        self.assertTrue(result)
    
    @patch('smtplib.SMTP')
    @patch('requests.post')
    def test_mixed_notification_success_failure(self, mock_post, mock_smtp):
        """Test mixed success and failure of different notification methods"""
        # Enable all notification methods
        self.minimal_config['notifications']['email'] = {
            'enabled': True,
            'smtp_server': 'smtp.test.com',
            'smtp_port': 587,
            'username': 'test@test.com',
            'password': 'password',
            'to_emails': ['recipient@test.com'],
            'on_success': True
        }
        self.minimal_config['notifications']['webhook'] = {
            'enabled': True,
            'url': 'https://webhook.test.com'
        }
        self.minimal_config['notifications']['slack'] = {
            'enabled': True,
            'webhook_url': 'https://slack.test.com'
        }
        
        # Email succeeds
        mock_server = Mock()
        mock_smtp.return_value.__enter__.return_value = mock_server
        
        # Webhook fails
        mock_post.side_effect = [
            requests.exceptions.RequestException("Webhook failed"),  # First call (webhook)
            Mock()  # Second call (Slack) succeeds
        ]
        
        results = {
            'whatsapp': {'success': True, 'messages_count': 10, 'errors': []}
        }
        
        result = self.notification_manager.send_extraction_complete_notification(results)
        
        # Should return True because at least one notification succeeded
        self.assertTrue(result)


if __name__ == '__main__':
    unittest.main()