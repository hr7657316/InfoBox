"""
Notification management for the extraction pipeline

Handles sending notifications via email, webhook, and Slack for extraction results and errors.
"""

import smtplib
import json
import requests
from typing import Dict, List, Any, Optional
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
import logging
from .config import ConfigManager


class NotificationManager:
    """Manage notifications for pipeline events"""
    
    def __init__(self, config: Dict[str, Any], logger: Optional[logging.Logger] = None):
        self.config = config
        self.logger = logger or logging.getLogger(__name__)
        self.notification_config = config.get('notifications', {})
        
    def send_extraction_complete_notification(self, results: Dict[str, Any]) -> bool:
        """
        Send notification when extraction completes
        
        Args:
            results: Dictionary of extraction results
            
        Returns:
            bool: True if at least one notification was sent successfully
        """
        if not self.notification_config.get('enabled', False):
            return True
            
        success_count = 0
        total_attempts = 0
        
        # Prepare notification content
        subject, body = self._format_extraction_complete_message(results)
        
        # Send email notification
        if self._should_send_email_notification(results):
            total_attempts += 1
            if self._send_email_notification(subject, body):
                success_count += 1
        
        # Send webhook notification
        if self._should_send_webhook_notification():
            total_attempts += 1
            webhook_payload = self._format_webhook_payload('extraction_complete', results)
            if self._send_webhook_notification(webhook_payload):
                success_count += 1
        
        # Send Slack notification
        if self._should_send_slack_notification():
            total_attempts += 1
            slack_message = self._format_slack_message(results)
            if self._send_slack_notification(slack_message):
                success_count += 1
        
        # Return True if at least one notification was sent or no notifications were configured
        return total_attempts == 0 or success_count > 0
    
    def send_error_notification(self, error_info: Dict[str, Any]) -> bool:
        """
        Send notification when errors occur
        
        Args:
            error_info: Dictionary containing error details
            
        Returns:
            bool: True if at least one notification was sent successfully
        """
        if not self.notification_config.get('enabled', False):
            return True
            
        success_count = 0
        total_attempts = 0
        
        # Prepare notification content
        subject, body = self._format_error_message(error_info)
        
        # Send email notification for errors
        email_config = self.notification_config.get('email', {})
        if email_config.get('enabled', False) and email_config.get('on_error', True):
            total_attempts += 1
            if self._send_email_notification(subject, body):
                success_count += 1
        
        # Send webhook notification for errors
        if self._should_send_webhook_notification():
            total_attempts += 1
            webhook_payload = self._format_webhook_payload('extraction_error', error_info)
            if self._send_webhook_notification(webhook_payload):
                success_count += 1
        
        # Send Slack notification for errors
        if self._should_send_slack_notification():
            total_attempts += 1
            slack_message = f"🚨 Pipeline Error: {error_info.get('message', 'Unknown error')}"
            if self._send_slack_notification(slack_message):
                success_count += 1
        
        return total_attempts == 0 or success_count > 0
    
    def _should_send_email_notification(self, results: Dict[str, Any]) -> bool:
        """Check if email notification should be sent based on results"""
        email_config = self.notification_config.get('email', {})
        if not email_config.get('enabled', False):
            return False
            
        # Check if any extraction was successful
        has_success = any(result.get('success', False) for result in results.values())
        has_errors = any(result.get('errors', []) for result in results.values())
        
        # Send on success if configured
        if has_success and email_config.get('on_success', True):
            return True
            
        # Send on error if configured
        if has_errors and email_config.get('on_error', True):
            return True
            
        return False
    
    def _should_send_webhook_notification(self) -> bool:
        """Check if webhook notification should be sent"""
        webhook_config = self.notification_config.get('webhook', {})
        return webhook_config.get('enabled', False) and webhook_config.get('url')
    
    def _should_send_slack_notification(self) -> bool:
        """Check if Slack notification should be sent"""
        slack_config = self.notification_config.get('slack', {})
        return slack_config.get('enabled', False) and slack_config.get('webhook_url')
    
    def _send_email_notification(self, subject: str, body: str) -> bool:
        """
        Send email notification
        
        Args:
            subject: Email subject
            body: Email body
            
        Returns:
            bool: True if email was sent successfully
        """
        try:
            email_config = self.notification_config.get('email', {})
            
            # Get email configuration
            smtp_server = email_config.get('smtp_server', 'smtp.gmail.com')
            smtp_port = email_config.get('smtp_port', 587)
            username = email_config.get('username', '')
            password = email_config.get('password', '')
            from_email = email_config.get('from_email', username)
            to_emails = email_config.get('to_emails', [])
            
            if not username or not password or not to_emails:
                self.logger.warning("Email notification configuration incomplete")
                return False
            
            # Create message
            msg = MIMEMultipart()
            msg['From'] = from_email
            msg['To'] = ', '.join(to_emails)
            msg['Subject'] = subject
            
            # Add body
            msg.attach(MIMEText(body, 'plain'))
            
            # Send email
            with smtplib.SMTP(smtp_server, smtp_port) as server:
                server.starttls()
                server.login(username, password)
                server.send_message(msg)
            
            self.logger.info(f"Email notification sent to {len(to_emails)} recipients")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to send email notification: {str(e)}")
            return False
    
    def _send_webhook_notification(self, payload: Dict[str, Any]) -> bool:
        """
        Send webhook notification
        
        Args:
            payload: Webhook payload
            
        Returns:
            bool: True if webhook was sent successfully
        """
        try:
            webhook_config = self.notification_config.get('webhook', {})
            url = webhook_config.get('url')
            headers = webhook_config.get('headers', {'Content-Type': 'application/json'})
            timeout = webhook_config.get('timeout', 30)
            
            if not url:
                return False
            
            response = requests.post(
                url,
                json=payload,
                headers=headers,
                timeout=timeout
            )
            response.raise_for_status()
            
            self.logger.info(f"Webhook notification sent to {url}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to send webhook notification: {str(e)}")
            return False
    
    def _send_slack_notification(self, message: str) -> bool:
        """
        Send Slack notification
        
        Args:
            message: Slack message
            
        Returns:
            bool: True if Slack message was sent successfully
        """
        try:
            slack_config = self.notification_config.get('slack', {})
            webhook_url = slack_config.get('webhook_url')
            channel = slack_config.get('channel', '#general')
            username = slack_config.get('username', 'Pipeline Bot')
            
            if not webhook_url:
                return False
            
            payload = {
                'text': message,
                'channel': channel,
                'username': username
            }
            
            response = requests.post(webhook_url, json=payload, timeout=30)
            response.raise_for_status()
            
            self.logger.info(f"Slack notification sent to {channel}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to send Slack notification: {str(e)}")
            return False
    
    def _format_extraction_complete_message(self, results: Dict[str, Any]) -> tuple[str, str]:
        """Format extraction complete notification message"""
        # Count successful and failed extractions
        successful_sources = []
        failed_sources = []
        total_messages = 0
        total_media = 0
        
        for source, result in results.items():
            if result.get('success', False):
                successful_sources.append(source)
                total_messages += result.get('messages_count', 0)
                total_media += result.get('media_count', 0)
            else:
                failed_sources.append(source)
        
        # Create subject
        if failed_sources:
            subject = f"⚠️ Pipeline Extraction Completed with Errors"
        else:
            subject = f"✅ Pipeline Extraction Completed Successfully"
        
        # Create body
        lines = ["Pipeline Extraction Summary", "=" * 30, ""]
        
        if successful_sources:
            lines.append("✅ Successful Extractions:")
            for source in successful_sources:
                result = results[source]
                lines.append(f"  • {source.title()}: {result.get('messages_count', 0)} messages, {result.get('media_count', 0)} media files")
            lines.append("")
        
        if failed_sources:
            lines.append("❌ Failed Extractions:")
            for source in failed_sources:
                result = results[source]
                errors = result.get('errors', [])
                error_summary = errors[0] if errors else "Unknown error"
                lines.append(f"  • {source.title()}: {error_summary}")
            lines.append("")
        
        lines.extend([
            f"Total Messages: {total_messages}",
            f"Total Media Files: {total_media}",
            f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        ])
        
        body = "\n".join(lines)
        return subject, body
    
    def _format_error_message(self, error_info: Dict[str, Any]) -> tuple[str, str]:
        """Format error notification message"""
        component = error_info.get('component', 'Unknown')
        message = error_info.get('message', 'Unknown error')
        severity = error_info.get('severity', 'medium')
        
        # Create subject
        severity_icon = "🚨" if severity == 'high' else "⚠️"
        subject = f"{severity_icon} Pipeline Error in {component}"
        
        # Create body
        lines = [
            "Pipeline Error Report",
            "=" * 20,
            "",
            f"Component: {component}",
            f"Error: {message}",
            f"Severity: {severity.title()}",
            f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        ]
        
        # Add additional context if available
        if 'context' in error_info:
            lines.extend(["", "Additional Context:"])
            for key, value in error_info['context'].items():
                lines.append(f"  {key}: {value}")
        
        body = "\n".join(lines)
        return subject, body
    
    def _format_webhook_payload(self, event_type: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Format webhook payload"""
        return {
            'event': event_type,
            'timestamp': datetime.now().isoformat(),
            'data': data,
            'source': 'data-extraction-pipeline'
        }
    
    def _format_slack_message(self, results: Dict[str, Any]) -> str:
        """Format Slack message for extraction results"""
        successful_sources = []
        failed_sources = []
        total_messages = 0
        total_media = 0
        
        for source, result in results.items():
            if result.get('success', False):
                successful_sources.append(source)
                total_messages += result.get('messages_count', 0)
                total_media += result.get('media_count', 0)
            else:
                failed_sources.append(source)
        
        if failed_sources:
            status_icon = "⚠️"
            status_text = "Completed with Errors"
        else:
            status_icon = "✅"
            status_text = "Completed Successfully"
        
        lines = [
            f"{status_icon} *Pipeline Extraction {status_text}*",
            ""
        ]
        
        if successful_sources:
            for source in successful_sources:
                result = results[source]
                emoji = "📱" if source == 'whatsapp' else "📧"
                lines.append(f"{emoji} {source.title()}: {result.get('messages_count', 0)} messages, {result.get('media_count', 0)} media")
        
        if failed_sources:
            lines.append("")
            for source in failed_sources:
                lines.append(f"❌ {source.title()}: Failed")
        
        lines.extend([
            "",
            f"📊 Total: {total_messages} messages, {total_media} media files"
        ])
        
        return "\n".join(lines)