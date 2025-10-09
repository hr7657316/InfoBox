"""
Unit tests for notification functionality
"""

import unittest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime
import json
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# Mock notification classes since they're not implemented yet
class MockNotificationManager:
    """Mock notification manager for testing"""
    
    def __init__(self, config):
        self.config = config
        self.sent_notifications = []
    
    def send_email(self, subject, body, recipients):
        notification = {
            'type': 'email',
            'subject': subject,
            'body': body,
            'recipients': recipients,
            'timestamp': datetime.now(),
            'status': 'sent'
        }
        self.sent_notifications.append(notification)
        return True
    
    def send_webhook(self, url, payload):
        notification = {
            'type': 'webhook',
            'url': url,
            'payload': payload,
            'timestamp': datetime.now(),
            'status': 'sent'
        }
        self.sent_notifications.append(notification)
        return True
    
    def send_slack(self, channel, message):
        notification = {
            'type': 'slack',
            'channel': channel,
            'message': message,
            'timestamp': datetime.now(),
            'status': 'sent'
        }
        self.sent_notifications.append(notification)
        return True
    
    def get_sent_notifications(self):
        return self.sent_notifications


class TestNotificationConfiguration(unittest.TestCase):
    """Test cases for notification configuration"""
    
    def setUp(self):
        self.config = {
            'email': {
                'enabled': True,
                'smtp_server': 'smtp.gmail.com',
                'smtp_port': 587,
                'username': 'test@example.com',
                'password': 'password',
                'recipients': ['admin@example.com']
            },
            'webhook': {
                'enabled': True,
                'url': 'https://hooks.example.com/webhook',
                'headers': {'Content-Type': 'application/json'}
            },
            'slack': {
                'enabled': False,
                'webhook_url': 'https://hooks.slack.com/webhook',
                'channel': '#alerts'
            }
        }
    
    def test_notification_config_validation_valid(self):
        """Test valid notification configuration"""
        manager = MockNotificationManager(self.config)
        self.assertTrue(manager.config['email']['enabled'])
        self.assertEqual(manager.config['email']['smtp_server'], 'smtp.gmail.com')
    
    def test_notification_config_email_settings(self):
        """Test email notification settings"""
        email_config = self.config['email']
        
        self.assertTrue(email_config['enabled'])
        self.assertEqual(email_config['smtp_server'], 'smtp.gmail.com')
        self.assertEqual(email_config['smtp_port'], 587)
        self.assertIn('admin@example.com', email_config['recipients'])
    
    def test_notification_config_webhook_settings(self):
        """Test webhook notification settings"""
        webhook_config = self.config['webhook']
        
        self.assertTrue(webhook_config['enabled'])
        self.assertEqual(webhook_config['url'], 'https://hooks.example.com/webhook')
        self.assertIn('Content-Type', webhook_config['headers'])
    
    def test_notification_config_slack_settings(self):
        """Test Slack notification settings"""
        slack_config = self.config['slack']
        
        self.assertFalse(slack_config['enabled'])  # Disabled in test config
        self.assertEqual(slack_config['channel'], '#alerts')


class TestEmailNotifications(unittest.TestCase):
    """Test cases for email notifications"""
    
    def setUp(self):
        self.config = {
            'email': {
                'enabled': True,
                'smtp_server': 'smtp.gmail.com',
                'smtp_port': 587,
                'username': 'test@example.com',
                'password': 'password',
                'recipients': ['admin@example.com', 'user@example.com']
            }
        }
        self.manager = MockNotificationManager(self.config)
    
    def test_send_email_success(self):
        """Test successful email sending"""
        subject = "Pipeline Extraction Complete"
        body = "The data extraction pipeline has completed successfully."
        recipients = ['admin@example.com']
        
        result = self.manager.send_email(subject, body, recipients)
        
        self.assertTrue(result)
        notifications = self.manager.get_sent_notifications()
        self.assertEqual(len(notifications), 1)
        
        notification = notifications[0]
        self.assertEqual(notification['type'], 'email')
        self.assertEqual(notification['subject'], subject)
        self.assertEqual(notification['body'], body)
        self.assertEqual(notification['recipients'], recipients)
    
    def test_send_email_multiple_recipients(self):
        """Test sending email to multiple recipients"""
        subject = "Pipeline Alert"
        body = "Multiple errors detected in pipeline."
        recipients = ['admin@example.com', 'user@example.com', 'ops@example.com']
        
        result = self.manager.send_email(subject, body, recipients)
        
        self.assertTrue(result)
        notifications = self.manager.get_sent_notifications()
        self.assertEqual(len(notifications), 1)
        self.assertEqual(notifications[0]['recipients'], recipients)
    
    def test_send_email_html_content(self):
        """Test sending HTML email content"""
        subject = "Pipeline Report"
        html_body = """
        <html>
            <body>
                <h2>Extraction Report</h2>
                <p>WhatsApp: <strong>50 messages</strong></p>
                <p>Email: <strong>25 messages</strong></p>
            </body>
        </html>
        """
        recipients = ['admin@example.com']
        
        result = self.manager.send_email(subject, html_body, recipients)
        
        self.assertTrue(result)
        notifications = self.manager.get_sent_notifications()
        self.assertIn('<html>', notifications[0]['body'])
        self.assertIn('<strong>50 messages</strong>', notifications[0]['body'])
    
    def test_send_email_with_extraction_results(self):
        """Test sending email with extraction results"""
        extraction_results = {
            'whatsapp': {
                'success': True,
                'messages_count': 45,
                'media_count': 12,
                'execution_time': 23.5
            },
            'email': {
                'success': True,
                'messages_count': 78,
                'media_count': 5,
                'execution_time': 15.2
            }
        }
        
        subject = "Daily Extraction Report"
        body = f"Extraction completed:\nWhatsApp: {extraction_results['whatsapp']['messages_count']} messages\nEmail: {extraction_results['email']['messages_count']} messages"
        
        result = self.manager.send_email(subject, body, ['admin@example.com'])
        
        self.assertTrue(result)
        notifications = self.manager.get_sent_notifications()
        self.assertIn('45 messages', notifications[0]['body'])
        self.assertIn('78 messages', notifications[0]['body'])


class TestWebhookNotifications(unittest.TestCase):
    """Test cases for webhook notifications"""
    
    def setUp(self):
        self.config = {
            'webhook': {
                'enabled': True,
                'url': 'https://hooks.example.com/webhook',
                'headers': {'Content-Type': 'application/json'}
            }
        }
        self.manager = MockNotificationManager(self.config)
    
    def test_send_webhook_success(self):
        """Test successful webhook sending"""
        url = 'https://hooks.example.com/webhook'
        payload = {
            'event': 'extraction_complete',
            'timestamp': datetime.now().isoformat(),
            'results': {
                'whatsapp': {'messages': 50},
                'email': {'messages': 25}
            }
        }
        
        result = self.manager.send_webhook(url, payload)
        
        self.assertTrue(result)
        notifications = self.manager.get_sent_notifications()
        self.assertEqual(len(notifications), 1)
        
        notification = notifications[0]
        self.assertEqual(notification['type'], 'webhook')
        self.assertEqual(notification['url'], url)
        self.assertEqual(notification['payload'], payload)
    
    def test_send_webhook_error_notification(self):
        """Test sending webhook for error notifications"""
        url = 'https://hooks.example.com/webhook'
        payload = {
            'event': 'extraction_error',
            'timestamp': datetime.now().isoformat(),
            'error': {
                'component': 'whatsapp_extractor',
                'message': 'Authentication failed',
                'severity': 'high'
            }
        }
        
        result = self.manager.send_webhook(url, payload)
        
        self.assertTrue(result)
        notifications = self.manager.get_sent_notifications()
        notification = notifications[0]
        
        self.assertEqual(notification['payload']['event'], 'extraction_error')
        self.assertIn('Authentication failed', notification['payload']['error']['message'])
    
    def test_send_webhook_with_custom_headers(self):
        """Test sending webhook with custom headers"""
        url = 'https://api.example.com/notifications'
        payload = {'message': 'Pipeline status update'}
        
        # In a real implementation, headers would be used in the HTTP request
        result = self.manager.send_webhook(url, payload)
        
        self.assertTrue(result)
        notifications = self.manager.get_sent_notifications()
        self.assertEqual(notifications[0]['url'], url)


class TestSlackNotifications(unittest.TestCase):
    """Test cases for Slack notifications"""
    
    def setUp(self):
        self.config = {
            'slack': {
                'enabled': True,
                'webhook_url': 'https://hooks.slack.com/webhook',
                'channel': '#pipeline-alerts'
            }
        }
        self.manager = MockNotificationManager(self.config)
    
    def test_send_slack_message(self):
        """Test sending Slack message"""
        channel = '#pipeline-alerts'
        message = 'Pipeline extraction completed successfully! 🎉'
        
        result = self.manager.send_slack(channel, message)
        
        self.assertTrue(result)
        notifications = self.manager.get_sent_notifications()
        self.assertEqual(len(notifications), 1)
        
        notification = notifications[0]
        self.assertEqual(notification['type'], 'slack')
        self.assertEqual(notification['channel'], channel)
        self.assertEqual(notification['message'], message)
    
    def test_send_slack_error_alert(self):
        """Test sending Slack error alert"""
        channel = '#pipeline-alerts'
        message = '🚨 Pipeline Error: WhatsApp authentication failed'
        
        result = self.manager.send_slack(channel, message)
        
        self.assertTrue(result)
        notifications = self.manager.get_sent_notifications()
        notification = notifications[0]
        
        self.assertIn('🚨', notification['message'])
        self.assertIn('authentication failed', notification['message'])
    
    def test_send_slack_formatted_message(self):
        """Test sending formatted Slack message"""
        channel = '#pipeline-alerts'
        message = """
        *Pipeline Extraction Report*
        
        📱 WhatsApp: 45 messages, 12 media files
        📧 Email: 78 messages, 5 attachments
        ⏱️ Total time: 38.7 seconds
        
        Status: ✅ Success
        """
        
        result = self.manager.send_slack(channel, message)
        
        self.assertTrue(result)
        notifications = self.manager.get_sent_notifications()
        notification = notifications[0]
        
        self.assertIn('*Pipeline Extraction Report*', notification['message'])
        self.assertIn('45 messages', notification['message'])
        self.assertIn('✅ Success', notification['message'])


class TestNotificationTemplates(unittest.TestCase):
    """Test cases for notification templates"""
    
    def setUp(self):
        self.config = {}
        self.manager = MockNotificationManager(self.config)
    
    def test_success_notification_template(self):
        """Test success notification template"""
        results = {
            'whatsapp': {'success': True, 'messages_count': 50, 'media_count': 12},
            'email': {'success': True, 'messages_count': 25, 'media_count': 3}
        }
        
        # Template for success notification
        subject = "✅ Pipeline Extraction Successful"
        body = self._format_success_template(results)
        
        result = self.manager.send_email(subject, body, ['admin@example.com'])
        
        self.assertTrue(result)
        notifications = self.manager.get_sent_notifications()
        notification = notifications[0]
        
        self.assertIn('✅', notification['subject'])
        self.assertIn('50', notification['body'])  # WhatsApp message count
        self.assertIn('25', notification['body'])  # Email message count
    
    def test_error_notification_template(self):
        """Test error notification template"""
        errors = [
            {'component': 'whatsapp', 'message': 'Authentication failed', 'severity': 'high'},
            {'component': 'email', 'message': 'Connection timeout', 'severity': 'medium'}
        ]
        
        # Template for error notification
        subject = "🚨 Pipeline Extraction Errors"
        body = self._format_error_template(errors)
        
        result = self.manager.send_email(subject, body, ['admin@example.com'])
        
        self.assertTrue(result)
        notifications = self.manager.get_sent_notifications()
        notification = notifications[0]
        
        self.assertIn('🚨', notification['subject'])
        self.assertIn('Authentication failed', notification['body'])
        self.assertIn('Connection timeout', notification['body'])
    
    def test_summary_notification_template(self):
        """Test summary notification template"""
        summary = {
            'total_messages': 125,
            'total_media': 18,
            'execution_time': 45.3,
            'sources': ['whatsapp', 'email'],
            'errors': 2
        }
        
        subject = "📊 Daily Pipeline Summary"
        body = self._format_summary_template(summary)
        
        result = self.manager.send_email(subject, body, ['admin@example.com'])
        
        self.assertTrue(result)
        notifications = self.manager.get_sent_notifications()
        notification = notifications[0]
        
        self.assertIn('📊', notification['subject'])
        self.assertIn('125', notification['body'])  # Total messages
        self.assertIn('45.3', notification['body'])  # Execution time
    
    def _format_success_template(self, results):
        """Format success notification template"""
        lines = ["Pipeline extraction completed successfully!", ""]
        
        for source, result in results.items():
            if result['success']:
                lines.append(f"✅ {source.title()}: {result['messages_count']} messages, {result['media_count']} media files")
            else:
                lines.append(f"❌ {source.title()}: Failed")
        
        return "\n".join(lines)
    
    def _format_error_template(self, errors):
        """Format error notification template"""
        lines = ["Pipeline extraction encountered errors:", ""]
        
        for error in errors:
            severity_icon = "🚨" if error['severity'] == 'high' else "⚠️"
            lines.append(f"{severity_icon} {error['component']}: {error['message']}")
        
        return "\n".join(lines)
    
    def _format_summary_template(self, summary):
        """Format summary notification template"""
        lines = [
            "Daily Pipeline Summary",
            "=" * 20,
            f"Total Messages: {summary['total_messages']}",
            f"Total Media: {summary['total_media']}",
            f"Execution Time: {summary['execution_time']}s",
            f"Sources: {', '.join(summary['sources'])}",
            f"Errors: {summary['errors']}"
        ]
        
        return "\n".join(lines)


class TestNotificationErrorHandling(unittest.TestCase):
    """Test cases for notification error handling"""
    
    def setUp(self):
        self.config = {}
        self.manager = MockNotificationManager(self.config)
    
    def test_email_send_failure_handling(self):
        """Test handling of email send failures"""
        # Mock a failing email send
        original_send_email = self.manager.send_email
        
        def failing_send_email(subject, body, recipients):
            notification = {
                'type': 'email',
                'subject': subject,
                'body': body,
                'recipients': recipients,
                'timestamp': datetime.now(),
                'status': 'failed',
                'error': 'SMTP connection failed'
            }
            self.manager.sent_notifications.append(notification)
            return False
        
        self.manager.send_email = failing_send_email
        
        result = self.manager.send_email("Test", "Body", ["test@example.com"])
        
        self.assertFalse(result)
        notifications = self.manager.get_sent_notifications()
        self.assertEqual(notifications[0]['status'], 'failed')
        self.assertIn('SMTP connection failed', notifications[0]['error'])
    
    def test_webhook_send_failure_handling(self):
        """Test handling of webhook send failures"""
        # Mock a failing webhook send
        original_send_webhook = self.manager.send_webhook
        
        def failing_send_webhook(url, payload):
            notification = {
                'type': 'webhook',
                'url': url,
                'payload': payload,
                'timestamp': datetime.now(),
                'status': 'failed',
                'error': 'HTTP 500 Internal Server Error'
            }
            self.manager.sent_notifications.append(notification)
            return False
        
        self.manager.send_webhook = failing_send_webhook
        
        result = self.manager.send_webhook("https://example.com", {"test": "data"})
        
        self.assertFalse(result)
        notifications = self.manager.get_sent_notifications()
        self.assertEqual(notifications[0]['status'], 'failed')
        self.assertIn('HTTP 500', notifications[0]['error'])
    
    def test_notification_retry_logic(self):
        """Test notification retry logic"""
        attempt_count = 0
        
        def retry_send_email(subject, body, recipients):
            nonlocal attempt_count
            attempt_count += 1
            
            if attempt_count <= 2:  # Fail first 2 attempts
                notification = {
                    'type': 'email',
                    'subject': subject,
                    'body': body,
                    'recipients': recipients,
                    'timestamp': datetime.now(),
                    'status': 'failed',
                    'attempt': attempt_count
                }
                self.manager.sent_notifications.append(notification)
                return False
            else:  # Succeed on 3rd attempt
                notification = {
                    'type': 'email',
                    'subject': subject,
                    'body': body,
                    'recipients': recipients,
                    'timestamp': datetime.now(),
                    'status': 'sent',
                    'attempt': attempt_count
                }
                self.manager.sent_notifications.append(notification)
                return True
        
        self.manager.send_email = retry_send_email
        
        # Simulate retry logic
        max_retries = 3
        success = False
        
        for attempt in range(max_retries):
            success = self.manager.send_email("Test", "Body", ["test@example.com"])
            if success:
                break
        
        self.assertTrue(success)
        notifications = self.manager.get_sent_notifications()
        self.assertEqual(len(notifications), 3)  # 2 failures + 1 success
        self.assertEqual(notifications[-1]['status'], 'sent')
        self.assertEqual(notifications[-1]['attempt'], 3)


class TestNotificationIntegration(unittest.TestCase):
    """Test cases for notification integration with pipeline"""
    
    def setUp(self):
        self.config = {
            'email': {'enabled': True, 'recipients': ['admin@example.com']},
            'webhook': {'enabled': True, 'url': 'https://hooks.example.com/webhook'},
            'slack': {'enabled': True, 'channel': '#alerts'}
        }
        self.manager = MockNotificationManager(self.config)
    
    def test_send_extraction_complete_notifications(self):
        """Test sending notifications when extraction completes"""
        results = {
            'whatsapp': {'success': True, 'messages_count': 50, 'media_count': 12},
            'email': {'success': True, 'messages_count': 25, 'media_count': 3}
        }
        
        # Send all types of notifications
        self.manager.send_email("Extraction Complete", "Success", ["admin@example.com"])
        self.manager.send_webhook("https://hooks.example.com/webhook", {"event": "complete", "results": results})
        self.manager.send_slack("#alerts", "Extraction completed successfully!")
        
        notifications = self.manager.get_sent_notifications()
        self.assertEqual(len(notifications), 3)
        
        # Verify all notification types were sent
        notification_types = [n['type'] for n in notifications]
        self.assertIn('email', notification_types)
        self.assertIn('webhook', notification_types)
        self.assertIn('slack', notification_types)
    
    def test_send_error_notifications(self):
        """Test sending notifications when errors occur"""
        error_info = {
            'component': 'whatsapp_extractor',
            'message': 'Authentication failed',
            'severity': 'high',
            'timestamp': datetime.now().isoformat()
        }
        
        # Send error notifications
        self.manager.send_email("Pipeline Error", f"Error in {error_info['component']}: {error_info['message']}", ["admin@example.com"])
        self.manager.send_slack("#alerts", f"🚨 Error: {error_info['message']}")
        
        notifications = self.manager.get_sent_notifications()
        self.assertEqual(len(notifications), 2)
        
        # Verify error information is included
        email_notification = next(n for n in notifications if n['type'] == 'email')
        slack_notification = next(n for n in notifications if n['type'] == 'slack')
        
        self.assertIn('Authentication failed', email_notification['body'])
        self.assertIn('🚨', slack_notification['message'])


if __name__ == '__main__':
    unittest.main()