"""
Email data extractor

Extracts emails and attachments from IMAP-compatible mail servers.
"""

import os
import time
import uuid
import imaplib
import email
import email.header
import email.utils
from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime
import logging
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import ssl
import socket
from urllib.parse import urlparse
import base64
import json

# OAuth2 imports
try:
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import InstalledAppFlow
    GOOGLE_AUTH_AVAILABLE = True
except ImportError:
    GOOGLE_AUTH_AVAILABLE = False

from ..models import BaseExtractor, Email, ExtractionResult
from ..utils.error_handler import (
    ErrorHandler, ErrorCategory, with_error_handling, graceful_degradation
)


class ConnectionPool:
    """IMAP connection pool for managing multiple email accounts"""
    
    def __init__(self, max_connections: int = 5):
        self.max_connections = max_connections
        self.connections = {}
        self.connection_count = {}
        self.logger = logging.getLogger(__name__)
    
    def get_connection(self, account_id: str, config: Dict[str, Any]) -> Optional[imaplib.IMAP4_SSL]:
        """
        Get or create IMAP connection for an account
        
        Args:
            account_id: Unique identifier for the account
            config: Account configuration
            
        Returns:
            IMAP connection or None if failed
        """
        if account_id in self.connections:
            connection = self.connections[account_id]
            try:
                # Test connection with NOOP
                connection.noop()
                return connection
            except (imaplib.IMAP4.error, socket.error):
                # Connection is dead, remove it
                self.logger.warning(f"Removing dead connection for account {account_id}")
                del self.connections[account_id]
                if account_id in self.connection_count:
                    del self.connection_count[account_id]
        
        # Create new connection
        return self._create_connection(account_id, config)
    
    def _create_connection(self, account_id: str, config: Dict[str, Any]) -> Optional[imaplib.IMAP4_SSL]:
        """Create new IMAP connection"""
        try:
            imap_server = config.get('imap_server')
            imap_port = config.get('imap_port', 993)
            use_ssl = config.get('use_ssl', True)
            
            if use_ssl:
                connection = imaplib.IMAP4_SSL(imap_server, imap_port)
            else:
                connection = imaplib.IMAP4(imap_server, imap_port)
            
            self.connections[account_id] = connection
            self.connection_count[account_id] = 1
            
            self.logger.info(f"Created IMAP connection for account {account_id}")
            return connection
            
        except Exception as e:
            self.logger.error(f"Failed to create IMAP connection for account {account_id}: {e}")
            return None
    
    def close_connection(self, account_id: str):
        """Close connection for an account"""
        if account_id in self.connections:
            try:
                self.connections[account_id].close()
                self.connections[account_id].logout()
            except:
                pass  # Ignore errors during cleanup
            
            del self.connections[account_id]
            if account_id in self.connection_count:
                del self.connection_count[account_id]
            
            self.logger.info(f"Closed IMAP connection for account {account_id}")
    
    def close_all(self):
        """Close all connections"""
        for account_id in list(self.connections.keys()):
            self.close_connection(account_id)


class EmailExtractor(BaseExtractor):
    """Email message and attachment extractor"""
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.logger = logging.getLogger(__name__)
        
        # Initialize error handler
        self.error_handler = ErrorHandler(self.logger)
        
        # Initialize connection pool
        self.connection_pool = ConnectionPool(max_connections=config.get('max_connections', 5))
        
        # Configuration
        self.timeout = config.get('timeout', 30)
        self.max_retries = config.get('max_retries', 3)
        self.batch_size = config.get('batch_size', 100)
        
        # Account configurations
        self.accounts = config.get('accounts', [])
        if not self.accounts:
            self.logger.warning("No email accounts configured")
        
        # OAuth2 configuration
        self.oauth2_scopes = ['https://www.googleapis.com/auth/gmail.readonly']
        
        # Track authentication status per account
        self.authenticated_accounts = set()
    
    def authenticate(self) -> bool:
        """
        Authenticate with all configured email accounts
        
        Returns:
            bool: True if at least one account authenticated successfully
        """
        if not self.accounts:
            self.logger.error("No email accounts configured")
            return False
        
        success_count = 0
        context = {'component': 'email_extractor', 'operation': 'authentication'}
        
        for i, account_config in enumerate(self.accounts):
            account_id = f"account_{i}"
            email_address = account_config.get('email', f'account_{i}')
            account_context = {**context, 'account_id': account_id, 'email': email_address}
            
            try:
                if self.error_handler.with_retry(
                    self._authenticate_account,
                    account_id, account_config,
                    category=ErrorCategory.AUTHENTICATION,
                    context=account_context
                ):
                    self.authenticated_accounts.add(account_id)
                    success_count += 1
                    self.logger.info(f"Successfully authenticated account: {email_address}")
                else:
                    self.logger.error(f"Failed to authenticate account: {email_address}")
            except Exception as e:
                self.error_handler.handle_error(e, account_context, raise_on_critical=False)
        
        if success_count > 0:
            self._authenticated = True
            self.logger.info(f"Authenticated {success_count}/{len(self.accounts)} email accounts")
            return True
        else:
            self.logger.error("Failed to authenticate any email accounts")
            return False
    
    def _authenticate_account(self, account_id: str, config: Dict[str, Any]) -> bool:
        """
        Authenticate a single email account
        
        Args:
            account_id: Unique identifier for the account
            config: Account configuration
            
        Returns:
            bool: True if authentication successful
        """
        auth_method = config.get('auth_method', 'password')
        
        if auth_method == 'oauth2':
            return self._authenticate_oauth2(account_id, config)
        elif auth_method == 'password':
            return self._authenticate_password(account_id, config)
        else:
            self.logger.error(f"Unknown authentication method: {auth_method}")
            return False
    
    def _authenticate_password(self, account_id: str, config: Dict[str, Any]) -> bool:
        """Authenticate using username/password or app-specific password"""
        try:
            connection = self.connection_pool.get_connection(account_id, config)
            if not connection:
                return False
            
            email_address = config.get('email')
            password = config.get('password')
            
            if not email_address or not password:
                self.logger.error(f"Email address and password required for account {account_id}")
                return False
            
            # Attempt login
            connection.login(email_address, password)
            self.logger.info(f"Password authentication successful for {email_address}")
            return True
            
        except imaplib.IMAP4.error as e:
            self.logger.error(f"IMAP authentication failed for account {account_id}: {e}")
            return False
        except Exception as e:
            self.logger.error(f"Authentication error for account {account_id}: {e}")
            return False
    
    def _authenticate_oauth2(self, account_id: str, config: Dict[str, Any]) -> bool:
        """Authenticate using OAuth2 (primarily for Gmail)"""
        if not GOOGLE_AUTH_AVAILABLE:
            self.logger.error("Google Auth libraries not available. Install google-auth-oauthlib and google-auth-httplib2")
            return False
        
        try:
            client_id = config.get('client_id')
            client_secret = config.get('client_secret')
            refresh_token = config.get('refresh_token')
            
            if not all([client_id, client_secret, refresh_token]):
                self.logger.error(f"OAuth2 requires client_id, client_secret, and refresh_token for account {account_id}")
                return False
            
            # Create credentials from refresh token
            creds = Credentials(
                token=None,
                refresh_token=refresh_token,
                token_uri="https://oauth2.googleapis.com/token",
                client_id=client_id,
                client_secret=client_secret,
                scopes=self.oauth2_scopes
            )
            
            # Refresh the token
            creds.refresh(Request())
            
            if not creds.valid:
                self.logger.error(f"Failed to refresh OAuth2 token for account {account_id}")
                return False
            
            # Get IMAP connection
            connection = self.connection_pool.get_connection(account_id, config)
            if not connection:
                return False
            
            # Authenticate with OAuth2
            email_address = config.get('email')
            auth_string = self._generate_oauth2_string(email_address, creds.token)
            
            connection.authenticate('XOAUTH2', lambda x: auth_string)
            self.logger.info(f"OAuth2 authentication successful for {email_address}")
            return True
            
        except Exception as e:
            self.logger.error(f"OAuth2 authentication failed for account {account_id}: {e}")
            return False
    
    def _generate_oauth2_string(self, email_address: str, access_token: str) -> str:
        """Generate OAuth2 authentication string for IMAP"""
        auth_string = f'user={email_address}\x01auth=Bearer {access_token}\x01\x01'
        return base64.b64encode(auth_string.encode()).decode()
    
    def connect(self) -> bool:
        """
        Connect to all configured email accounts
        
        Returns:
            bool: True if at least one connection successful
        """
        return self.authenticate()
    
    def extract_emails(self, filters: Dict[str, Any] = None) -> List[Email]:
        """
        Extract emails from all authenticated accounts
        
        Args:
            filters: Optional filters for email extraction
                - date_range: Tuple of (start_date, end_date)
                - unread_only: bool
                - folder: str (default: 'INBOX')
                - limit: int (max emails per account)
                - subject: str (subject contains text)
                - from_email: str (from specific sender)
                - to_email: str (to specific recipient)
                - body_text: str (body contains text)
                - has_attachments: bool (emails with attachments)
                - min_size: int (minimum email size in bytes)
                - max_size: int (maximum email size in bytes)
                
        Returns:
            List of Email objects
        """
        if not self._authenticated:
            self.logger.error("Not authenticated. Call authenticate() first.")
            return []
        
        all_emails = []
        filters = filters or {}
        
        for i, account_config in enumerate(self.accounts):
            account_id = f"account_{i}"
            
            if account_id not in self.authenticated_accounts:
                self.logger.warning(f"Skipping unauthenticated account {account_id}")
                continue
            
            try:
                account_emails = self._extract_emails_from_account(account_id, account_config, filters)
                all_emails.extend(account_emails)
                self.logger.info(f"Extracted {len(account_emails)} emails from account {account_config.get('email', account_id)}")
            except Exception as e:
                self.logger.error(f"Failed to extract emails from account {account_id}: {e}")
                continue
        
        # Apply post-fetch filters
        filtered_emails = self._apply_post_fetch_filters(all_emails, filters)
        
        self.logger.info(f"Total emails extracted: {len(filtered_emails)}")
        return filtered_emails
    
    def _apply_post_fetch_filters(self, emails: List[Email], filters: Dict[str, Any]) -> List[Email]:
        """Apply filters that couldn't be applied at the IMAP level"""
        filtered_emails = emails
        
        # Filter by attachment presence
        if filters.get('has_attachments') is not None:
            has_attachments = filters['has_attachments']
            if has_attachments:
                filtered_emails = [email for email in filtered_emails if email.attachments]
            else:
                filtered_emails = [email for email in filtered_emails if not email.attachments]
        
        # Additional text-based filtering for more precise matching
        body_text_filter = filters.get('body_text_exact')
        if body_text_filter:
            filtered_emails = [
                email for email in filtered_emails 
                if body_text_filter.lower() in email.body_text.lower() or 
                   body_text_filter.lower() in email.body_html.lower()
            ]
        
        return filtered_emails
    
    def _extract_emails_from_account(self, account_id: str, config: Dict[str, Any], filters: Dict[str, Any]) -> List[Email]:
        """Extract emails from a single account"""
        connection = self.connection_pool.get_connection(account_id, config)
        if not connection:
            self.logger.error(f"No connection available for account {account_id}")
            return []
        
        emails = []
        folder = filters.get('folder', 'INBOX')
        
        try:
            # Select folder
            status, messages = connection.select(folder)
            if status != 'OK':
                self.logger.error(f"Failed to select folder {folder} for account {account_id}")
                return []
            
            # Build search criteria
            search_criteria = self._build_search_criteria(filters)
            
            # Search for emails
            status, message_ids = connection.search(None, search_criteria)
            if status != 'OK':
                self.logger.error(f"Email search failed for account {account_id}")
                return []
            
            # Get message IDs
            message_id_list = message_ids[0].split()
            if not message_id_list:
                self.logger.info(f"No emails found matching criteria for account {account_id}")
                return []
            
            # Apply limit if specified
            limit = filters.get('limit')
            if limit and len(message_id_list) > limit:
                message_id_list = message_id_list[-limit:]  # Get most recent emails
            
            self.logger.info(f"Found {len(message_id_list)} emails to process for account {account_id}")
            
            # Process emails in batches
            for i in range(0, len(message_id_list), self.batch_size):
                batch = message_id_list[i:i + self.batch_size]
                batch_emails = self._process_email_batch(connection, batch, folder, config.get('email', account_id))
                emails.extend(batch_emails)
                
                # Add small delay between batches
                if i + self.batch_size < len(message_id_list):
                    time.sleep(0.1)
            
            return emails
            
        except Exception as e:
            self.logger.error(f"Error extracting emails from account {account_id}: {e}")
            return []
    
    def _build_search_criteria(self, filters: Dict[str, Any]) -> str:
        """Build IMAP search criteria from filters"""
        criteria_parts = []
        
        # Date range filter
        date_range = filters.get('date_range')
        if date_range and len(date_range) == 2:
            start_date, end_date = date_range
            if start_date:
                criteria_parts.append(f'SINCE "{start_date.strftime("%d-%b-%Y")}"')
            if end_date:
                criteria_parts.append(f'BEFORE "{end_date.strftime("%d-%b-%Y")}"')
        
        # Unread only filter
        if filters.get('unread_only'):
            criteria_parts.append('UNSEEN')
        else:
            # Include both read and unread by default
            pass
        
        # Subject filter
        subject = filters.get('subject')
        if subject:
            criteria_parts.append(f'SUBJECT "{subject}"')
        
        # From filter
        from_email = filters.get('from_email')
        if from_email:
            criteria_parts.append(f'FROM "{from_email}"')
        
        # To filter
        to_email = filters.get('to_email')
        if to_email:
            criteria_parts.append(f'TO "{to_email}"')
        
        # Body text filter
        body_text = filters.get('body_text')
        if body_text:
            criteria_parts.append(f'BODY "{body_text}"')
        
        # Size filters
        min_size = filters.get('min_size')
        if min_size:
            criteria_parts.append(f'LARGER {min_size}')
        
        max_size = filters.get('max_size')
        if max_size:
            criteria_parts.append(f'SMALLER {max_size}')
        
        # Has attachments filter
        if filters.get('has_attachments'):
            # This is a workaround as IMAP doesn't have direct attachment search
            # We'll filter after fetching
            pass
        
        # Default to ALL if no criteria
        if not criteria_parts:
            return 'ALL'
        
        return ' '.join(criteria_parts)
    
    def _process_email_batch(self, connection: imaplib.IMAP4_SSL, message_ids: List[bytes], 
                           folder: str, account_email: str) -> List[Email]:
        """Process a batch of email messages"""
        emails = []
        
        for msg_id in message_ids:
            try:
                email_obj = self._fetch_and_parse_email(connection, msg_id, folder, account_email)
                if email_obj:
                    emails.append(email_obj)
            except Exception as e:
                self.logger.warning(f"Failed to process email {msg_id.decode()}: {e}")
                continue
        
        return emails
    
    def _fetch_and_parse_email(self, connection: imaplib.IMAP4_SSL, msg_id: bytes, 
                              folder: str, account_email: str) -> Optional[Email]:
        """Fetch and parse a single email message"""
        try:
            # Fetch email data with flags to determine read status
            status, msg_data = connection.fetch(msg_id, '(RFC822 FLAGS)')
            if status != 'OK' or not msg_data:
                return None
            
            # Parse flags to determine read status
            is_read = True  # Default to read
            flags_data = None
            raw_email = None
            
            for item in msg_data:
                if isinstance(item, tuple) and len(item) == 2:
                    if b'FLAGS' in item[0]:
                        flags_data = item[0]
                    elif b'RFC822' in item[0]:
                        raw_email = item[1]
            
            # Determine read status from flags
            if flags_data:
                flags_str = flags_data.decode('utf-8', errors='ignore')
                is_read = '\\Seen' in flags_str
            
            if not raw_email:
                self.logger.warning(f"No RFC822 data found for message {msg_id.decode()}")
                return None
            
            # Parse email message
            email_message = email.message_from_bytes(raw_email)
            
            # Extract basic information
            message_id = self._decode_header(email_message.get('Message-ID', ''))
            if not message_id:
                message_id = f"{account_email}_{msg_id.decode()}_{int(time.time())}"
            
            # Clean up message ID (remove angle brackets)
            message_id = message_id.strip('<>')
            
            # Parse date
            date_str = email_message.get('Date', '')
            timestamp = self._parse_email_date(date_str)
            
            # Extract sender and recipients
            sender_email = self._decode_header(email_message.get('From', ''))
            sender_email = self._extract_email_address(sender_email)
            
            to_header = self._decode_header(email_message.get('To', ''))
            cc_header = self._decode_header(email_message.get('Cc', ''))
            recipient_emails = self._extract_recipient_emails(to_header, cc_header)
            
            # Extract subject
            subject = self._decode_header(email_message.get('Subject', ''))
            
            # Extract body content
            body_text, body_html = self._extract_email_body(email_message)
            
            # Extract attachments info
            attachments = self._extract_attachment_info(email_message)
            
            return Email(
                id=message_id,
                timestamp=timestamp,
                sender_email=sender_email,
                recipient_emails=recipient_emails,
                subject=subject,
                body_text=body_text,
                body_html=body_html,
                attachments=attachments,
                is_read=is_read,
                folder=folder
            )
            
        except Exception as e:
            self.logger.error(f"Failed to parse email {msg_id.decode()}: {e}")
            return None
    
    def _decode_header(self, header_value: str) -> str:
        """Decode email header value"""
        if not header_value:
            return ''
        
        try:
            decoded_parts = email.header.decode_header(header_value)
            decoded_string = ''
            
            for part, encoding in decoded_parts:
                if isinstance(part, bytes):
                    if encoding:
                        decoded_string += part.decode(encoding)
                    else:
                        decoded_string += part.decode('utf-8', errors='ignore')
                else:
                    decoded_string += part
            
            return decoded_string.strip()
        except Exception as e:
            self.logger.warning(f"Failed to decode header '{header_value}': {e}")
            return header_value
    
    def _parse_email_date(self, date_str: str) -> datetime:
        """Parse email date string to datetime object"""
        if not date_str:
            return datetime.now()
        
        try:
            # Parse using email.utils which handles RFC 2822 format
            time_tuple = email.utils.parsedate_tz(date_str)
            if time_tuple:
                timestamp = email.utils.mktime_tz(time_tuple)
                return datetime.fromtimestamp(timestamp)
        except Exception as e:
            self.logger.warning(f"Failed to parse date '{date_str}': {e}")
        
        return datetime.now()
    
    def _extract_email_address(self, from_header: str) -> str:
        """Extract email address from From header"""
        if not from_header:
            return ''
        
        try:
            # Use email.utils to parse the address
            name, addr = email.utils.parseaddr(from_header)
            return addr if addr else from_header
        except Exception:
            return from_header
    
    def _extract_recipient_emails(self, to_header: str, cc_header: str) -> List[str]:
        """Extract recipient email addresses from To and Cc headers"""
        recipients = []
        
        for header in [to_header, cc_header]:
            if header:
                try:
                    addresses = email.utils.getaddresses([header])
                    for name, addr in addresses:
                        if addr:
                            recipients.append(addr)
                except Exception as e:
                    self.logger.warning(f"Failed to parse recipients from '{header}': {e}")
        
        return recipients
    
    def _extract_email_body(self, email_message: email.message.Message) -> Tuple[str, str]:
        """Extract plain text and HTML body from email message"""
        body_text = ''
        body_html = ''
        
        try:
            if email_message.is_multipart():
                for part in email_message.walk():
                    content_type = part.get_content_type()
                    content_disposition = str(part.get('Content-Disposition', ''))
                    
                    # Skip attachments
                    if 'attachment' in content_disposition:
                        continue
                    
                    if content_type == 'text/plain' and not body_text:
                        body_text = self._decode_email_content(part)
                    elif content_type == 'text/html' and not body_html:
                        body_html = self._decode_email_content(part)
            else:
                # Single part message
                content_type = email_message.get_content_type()
                if content_type == 'text/plain':
                    body_text = self._decode_email_content(email_message)
                elif content_type == 'text/html':
                    body_html = self._decode_email_content(email_message)
        
        except Exception as e:
            self.logger.warning(f"Failed to extract email body: {e}")
        
        return body_text, body_html
    
    def _decode_email_content(self, part: email.message.Message) -> str:
        """Decode email content part"""
        try:
            payload = part.get_payload(decode=True)
            if payload is None:
                return ''
            
            # Get charset
            charset = part.get_content_charset()
            if charset is None:
                charset = 'utf-8'
            
            # Decode content
            if isinstance(payload, bytes):
                return payload.decode(charset, errors='ignore')
            else:
                return str(payload)
        
        except Exception as e:
            self.logger.warning(f"Failed to decode email content: {e}")
            return ''
    
    def _extract_attachment_info(self, email_message: email.message.Message) -> List[Dict[str, Any]]:
        """Extract detailed attachment information from email message"""
        attachments = []
        
        try:
            attachment_count = 0
            
            for part in email_message.walk():
                content_disposition = str(part.get('Content-Disposition', ''))
                
                # Check for both attachments and inline content (like images)
                if 'attachment' in content_disposition or 'inline' in content_disposition:
                    attachment_count += 1
                    filename = part.get_filename()
                    
                    if filename:
                        # Decode filename if needed
                        filename = self._decode_header(filename)
                    else:
                        # Generate a default filename
                        content_type = part.get_content_type()
                        ext = self._get_extension_from_content_type(content_type)
                        filename = f"attachment_{attachment_count}{ext}"
                    
                    # Get content info
                    content_type = part.get_content_type()
                    
                    # Calculate size
                    try:
                        payload = part.get_payload(decode=True)
                        content_size = len(payload) if payload else 0
                    except Exception:
                        content_size = 0
                    
                    # Extract additional metadata
                    content_id = part.get('Content-ID', '').strip('<>')
                    content_description = part.get('Content-Description', '')
                    
                    # Determine if it's an inline attachment
                    is_inline = 'inline' in content_disposition
                    
                    # Get creation/modification dates if available
                    creation_date = None
                    modification_date = None
                    
                    # Parse Content-Disposition for dates
                    if 'creation-date' in content_disposition:
                        try:
                            date_match = content_disposition.split('creation-date=')[1].split(';')[0].strip('"')
                            creation_date = self._parse_email_date(date_match)
                        except:
                            pass
                    
                    if 'modification-date' in content_disposition:
                        try:
                            date_match = content_disposition.split('modification-date=')[1].split(';')[0].strip('"')
                            modification_date = self._parse_email_date(date_match)
                        except:
                            pass
                    
                    attachment_info = {
                        'filename': filename,
                        'content_type': content_type,
                        'size': content_size,
                        'content_id': content_id,
                        'content_description': content_description,
                        'is_inline': is_inline,
                        'creation_date': creation_date.isoformat() if creation_date else None,
                        'modification_date': modification_date.isoformat() if modification_date else None,
                        'part_index': attachment_count,
                        'part_id': id(part)  # Unique identifier for this part
                    }
                    
                    attachments.append(attachment_info)
        
        except Exception as e:
            self.logger.warning(f"Failed to extract attachment info: {e}")
        
        return attachments
    
    def _get_extension_from_content_type(self, content_type: str) -> str:
        """Get file extension from content type"""
        content_type_map = {
            'application/pdf': '.pdf',
            'application/msword': '.doc',
            'application/vnd.openxmlformats-officedocument.wordprocessingml.document': '.docx',
            'application/vnd.ms-excel': '.xls',
            'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet': '.xlsx',
            'application/vnd.ms-powerpoint': '.ppt',
            'application/vnd.openxmlformats-officedocument.presentationml.presentation': '.pptx',
            'application/zip': '.zip',
            'application/x-zip-compressed': '.zip',
            'application/octet-stream': '.bin',
            'text/plain': '.txt',
            'text/html': '.html',
            'text/csv': '.csv',
            'image/jpeg': '.jpg',
            'image/png': '.png',
            'image/gif': '.gif',
            'image/bmp': '.bmp',
            'image/tiff': '.tiff',
            'audio/mpeg': '.mp3',
            'audio/wav': '.wav',
            'video/mp4': '.mp4',
            'video/avi': '.avi',
            'video/quicktime': '.mov'
        }
        
        return content_type_map.get(content_type.lower(), '.bin')
    
    def download_attachments(self, email_id: str, output_path: str) -> List[str]:
        """
        Download attachments for a specific email with organized storage
        
        Args:
            email_id: Email message ID
            output_path: Directory to save attachments
            
        Returns:
            List of downloaded file paths
        """
        if not self._authenticated:
            self.logger.error("Not authenticated. Call authenticate() first.")
            return []
        
        downloaded_files = []
        
        # Search for the email across all authenticated accounts
        for i, account_config in enumerate(self.accounts):
            account_id = f"account_{i}"
            
            if account_id not in self.authenticated_accounts:
                continue
            
            try:
                files = self._download_attachments_from_account(
                    account_id, account_config, email_id, output_path
                )
                downloaded_files.extend(files)
                
                if files:  # Found and processed the email
                    self.logger.info(f"Successfully downloaded {len(files)} attachments for email {email_id}")
                    break
                    
            except Exception as e:
                self.logger.error(f"Error downloading attachments from account {account_id}: {e}")
                continue
        
        if not downloaded_files:
            self.logger.warning(f"No attachments found or downloaded for email {email_id}")
        
        return downloaded_files
    
    def _download_attachments_from_account(self, account_id: str, config: Dict[str, Any], 
                                         email_id: str, output_path: str) -> List[str]:
        """Download attachments from a specific account"""
        connection = self.connection_pool.get_connection(account_id, config)
        if not connection:
            return []
        
        downloaded_files = []
        
        try:
            # Search for the email by Message-ID
            # Try different folders
            folders_to_search = ['INBOX', 'Sent', 'Drafts', 'All Mail', '[Gmail]/All Mail']
            
            for folder in folders_to_search:
                try:
                    status, _ = connection.select(folder)
                    if status != 'OK':
                        continue
                    
                    # Search for email by Message-ID
                    search_criteria = f'HEADER Message-ID "{email_id}"'
                    status, message_ids = connection.search(None, search_criteria)
                    
                    if status == 'OK' and message_ids[0]:
                        msg_id = message_ids[0].split()[0]  # Get first match
                        files = self._extract_and_save_attachments(
                            connection, msg_id, output_path, email_id
                        )
                        downloaded_files.extend(files)
                        break  # Found the email, stop searching
                        
                except Exception as e:
                    self.logger.debug(f"Could not search folder {folder}: {e}")
                    continue
            
            return downloaded_files
            
        except Exception as e:
            self.logger.error(f"Error downloading attachments for email {email_id}: {e}")
            return []
    
    def _extract_and_save_attachments(self, connection: imaplib.IMAP4_SSL, msg_id: bytes, 
                                    output_path: str, email_id: str) -> List[str]:
        """Extract and save attachments from an email message with enhanced error handling"""
        try:
            # Fetch the email message
            status, msg_data = connection.fetch(msg_id, '(RFC822)')
            if status != 'OK' or not msg_data:
                self.logger.error(f"Failed to fetch email message {msg_id.decode()}")
                return []
            
            # Parse the email
            raw_email = msg_data[0][1]
            email_message = email.message_from_bytes(raw_email)
            
            # Create output directory with proper error handling
            try:
                os.makedirs(output_path, exist_ok=True)
            except OSError as e:
                self.logger.error(f"Failed to create output directory {output_path}: {e}")
                return []
            
            downloaded_files = []
            attachment_count = 0
            failed_downloads = []
            
            # Walk through all parts of the email
            for part in email_message.walk():
                content_disposition = str(part.get('Content-Disposition', ''))
                
                # Check if this part is an attachment (including inline attachments)
                if 'attachment' in content_disposition or 'inline' in content_disposition:
                    attachment_count += 1
                    filename = part.get_filename()
                    
                    if filename:
                        # Decode filename
                        filename = self._decode_header(filename)
                        
                        # Generate unique filename to avoid conflicts
                        unique_filename = self._generate_unique_attachment_filename(
                            filename, output_path, email_id, attachment_count
                        )
                        
                        file_path = os.path.join(output_path, unique_filename)
                        
                        try:
                            # Get attachment content
                            attachment_data = part.get_payload(decode=True)
                            if attachment_data:
                                # Validate attachment size (prevent extremely large files)
                                max_size = 100 * 1024 * 1024  # 100MB limit
                                if len(attachment_data) > max_size:
                                    self.logger.warning(f"Attachment {filename} too large ({len(attachment_data)} bytes), skipping")
                                    failed_downloads.append(f"{filename} (too large)")
                                    continue
                                
                                # Save the attachment with atomic write
                                temp_path = file_path + '.tmp'
                                try:
                                    with open(temp_path, 'wb') as f:
                                        f.write(attachment_data)
                                    
                                    # Atomic rename
                                    os.rename(temp_path, file_path)
                                    
                                    downloaded_files.append(file_path)
                                    self.logger.info(f"Downloaded attachment: {unique_filename} ({len(attachment_data)} bytes)")
                                    
                                except OSError as e:
                                    self.logger.error(f"Failed to write attachment {filename}: {e}")
                                    failed_downloads.append(f"{filename} (write error)")
                                    # Clean up temp file if it exists
                                    if os.path.exists(temp_path):
                                        try:
                                            os.remove(temp_path)
                                        except:
                                            pass
                                    continue
                                    
                            else:
                                self.logger.warning(f"No data found for attachment: {filename}")
                                failed_downloads.append(f"{filename} (no data)")
                                
                        except Exception as e:
                            self.logger.error(f"Failed to process attachment {filename}: {e}")
                            failed_downloads.append(f"{filename} (processing error)")
                            continue
                    else:
                        # Generate default filename for unnamed attachments
                        content_type = part.get_content_type()
                        ext = self._get_extension_from_content_type(content_type)
                        default_filename = f"attachment_{attachment_count}{ext}"
                        
                        unique_filename = self._generate_unique_attachment_filename(
                            default_filename, output_path, email_id, attachment_count
                        )
                        
                        file_path = os.path.join(output_path, unique_filename)
                        
                        try:
                            attachment_data = part.get_payload(decode=True)
                            if attachment_data:
                                with open(file_path, 'wb') as f:
                                    f.write(attachment_data)
                                
                                downloaded_files.append(file_path)
                                self.logger.info(f"Downloaded unnamed attachment: {unique_filename} ({len(attachment_data)} bytes)")
                            else:
                                failed_downloads.append(f"attachment_{attachment_count} (no data)")
                                
                        except Exception as e:
                            self.logger.error(f"Failed to save unnamed attachment {attachment_count}: {e}")
                            failed_downloads.append(f"attachment_{attachment_count} (save error)")
                            continue
            
            # Log summary
            if downloaded_files:
                self.logger.info(f"Successfully downloaded {len(downloaded_files)} attachments for email {email_id}")
            
            if failed_downloads:
                self.logger.warning(f"Failed to download {len(failed_downloads)} attachments for email {email_id}: {', '.join(failed_downloads)}")
            
            if not downloaded_files and not failed_downloads:
                self.logger.info(f"No attachments found for email {email_id}")
            
            return downloaded_files
            
        except Exception as e:
            self.logger.error(f"Failed to extract attachments from email {email_id}: {e}")
            return []
    
    def _generate_unique_attachment_filename(self, original_filename: str, output_path: str, 
                                           email_id: str, attachment_num: int) -> str:
        """Generate a unique filename for an attachment"""
        # Clean the email ID for use in filename
        clean_email_id = email_id.replace('<', '').replace('>', '').replace('@', '_at_')
        clean_email_id = ''.join(c for c in clean_email_id if c.isalnum() or c in '-_.')[:20]
        
        # Get file extension
        name, ext = os.path.splitext(original_filename)
        if not ext:
            ext = '.bin'  # Default extension for files without extension
        
        # Clean the original filename
        clean_name = ''.join(c for c in name if c.isalnum() or c in '-_')[:50]
        if not clean_name:
            clean_name = f'attachment_{attachment_num}'
        
        # Generate base filename
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        base_filename = f"{clean_name}_{clean_email_id}_{timestamp}{ext}"
        
        # Ensure uniqueness
        counter = 1
        unique_filename = base_filename
        while os.path.exists(os.path.join(output_path, unique_filename)):
            name_part, ext_part = os.path.splitext(base_filename)
            unique_filename = f"{name_part}_{counter}{ext_part}"
            counter += 1
        
        return unique_filename
    
    def download_attachments_batch(self, email_attachments: List[Dict[str, Any]], 
                                 output_path: str) -> Dict[str, List[str]]:
        """
        Download attachments for multiple emails in batch with organized storage
        
        Args:
            email_attachments: List of dicts with 'email_id' and optional 'folder' keys
            output_path: Base directory to save attachments
            
        Returns:
            Dict mapping email IDs to lists of downloaded file paths
        """
        results = {}
        total_emails = len(email_attachments)
        successful_downloads = 0
        failed_downloads = 0
        
        self.logger.info(f"Starting batch download of attachments for {total_emails} emails")
        
        for i, item in enumerate(email_attachments, 1):
            email_id = item.get('email_id')
            if not email_id:
                self.logger.warning(f"Skipping item {i}: no email_id provided")
                continue
            
            try:
                # Create subdirectory for this email's attachments
                clean_email_id = email_id.replace('<', '').replace('>', '').replace('@', '_at_')[:20]
                email_output_path = os.path.join(output_path, f"email_{clean_email_id}")
                
                downloaded_files = self.download_attachments(email_id, email_output_path)
                results[email_id] = downloaded_files
                
                if downloaded_files:
                    successful_downloads += 1
                    self.logger.debug(f"Progress: {i}/{total_emails} - Downloaded {len(downloaded_files)} attachments for email {email_id}")
                else:
                    self.logger.debug(f"Progress: {i}/{total_emails} - No attachments found for email {email_id}")
                
                # Add small delay between downloads to be respectful to the server
                time.sleep(0.1)
                
            except Exception as e:
                self.logger.error(f"Failed to download attachments for email {email_id}: {e}")
                results[email_id] = []
                failed_downloads += 1
        
        self.logger.info(f"Batch download completed: {successful_downloads} emails with attachments, {failed_downloads} failed")
        return results
    
    def download_attachments_with_storage(self, email_id: str, storage_manager, 
                                        source_date: str = None) -> List[str]:
        """
        Download attachments using StorageManager for organized storage
        
        Args:
            email_id: Email message ID
            storage_manager: StorageManager instance for organized storage
            source_date: Date string for organization (YYYY-MM-DD), defaults to today
            
        Returns:
            List of downloaded file paths
        """
        if not storage_manager:
            self.logger.error("StorageManager instance required")
            return []
        
        if not source_date:
            source_date = datetime.now().strftime('%Y-%m-%d')
        
        # Get organized storage paths
        storage_paths = storage_manager.get_storage_paths('email', source_date)
        attachment_path = storage_paths['media']
        
        # Create email-specific subdirectory
        clean_email_id = email_id.replace('<', '').replace('>', '').replace('@', '_at_')[:20]
        email_attachment_path = os.path.join(attachment_path, f"email_{clean_email_id}")
        
        return self.download_attachments(email_id, email_attachment_path)
    
    def get_attachment_metadata(self, email_id: str) -> List[Dict[str, Any]]:
        """
        Get attachment metadata without downloading the files
        
        Args:
            email_id: Email message ID
            
        Returns:
            List of attachment metadata dictionaries
        """
        if not self._authenticated:
            self.logger.error("Not authenticated. Call authenticate() first.")
            return []
        
        # Search for the email across all authenticated accounts
        for i, account_config in enumerate(self.accounts):
            account_id = f"account_{i}"
            
            if account_id not in self.authenticated_accounts:
                continue
            
            try:
                metadata = self._get_attachment_metadata_from_account(
                    account_id, account_config, email_id
                )
                
                if metadata:  # Found the email
                    return metadata
                    
            except Exception as e:
                self.logger.error(f"Error getting attachment metadata from account {account_id}: {e}")
                continue
        
        return []
    
    def _get_attachment_metadata_from_account(self, account_id: str, config: Dict[str, Any], 
                                            email_id: str) -> List[Dict[str, Any]]:
        """Get attachment metadata from a specific account"""
        connection = self.connection_pool.get_connection(account_id, config)
        if not connection:
            return []
        
        try:
            # Search for the email by Message-ID
            folders_to_search = ['INBOX', 'Sent', 'Drafts', 'All Mail', '[Gmail]/All Mail']
            
            for folder in folders_to_search:
                try:
                    status, _ = connection.select(folder)
                    if status != 'OK':
                        continue
                    
                    # Search for email by Message-ID
                    search_criteria = f'HEADER Message-ID "{email_id}"'
                    status, message_ids = connection.search(None, search_criteria)
                    
                    if status == 'OK' and message_ids[0]:
                        msg_id = message_ids[0].split()[0]  # Get first match
                        
                        # Fetch the email message
                        status, msg_data = connection.fetch(msg_id, '(RFC822)')
                        if status != 'OK' or not msg_data:
                            continue
                        
                        # Parse the email and extract attachment info
                        raw_email = msg_data[0][1]
                        email_message = email.message_from_bytes(raw_email)
                        
                        return self._extract_attachment_info(email_message)
                        
                except Exception as e:
                    self.logger.debug(f"Could not search folder {folder}: {e}")
                    continue
            
            return []
            
        except Exception as e:
            self.logger.error(f"Error getting attachment metadata for email {email_id}: {e}")
            return []
    
    def save_data(self, emails: List[Email], output_path: str) -> None:
        """
        Save extracted email data to storage
        
        Args:
            emails: List of Email objects to save
            output_path: Base path for saving data
        """
        # This is a placeholder implementation
        # The actual saving will be handled by the StorageManager
        self.logger.info(f"Would save {len(emails)} emails to {output_path}")
    
    def extract_data(self, **kwargs) -> List[Dict[str, Any]]:
        """
        Extract data from email sources (BaseExtractor interface)
        
        Returns:
            List of email data dictionaries
        """
        emails = self.extract_emails(kwargs)
        return [self._email_to_dict(email_obj) for email_obj in emails]
    
    def _email_to_dict(self, email_obj: Email) -> Dict[str, Any]:
        """Convert Email object to dictionary"""
        return {
            'id': email_obj.id,
            'timestamp': email_obj.timestamp.isoformat(),
            'sender_email': email_obj.sender_email,
            'recipient_emails': email_obj.recipient_emails,
            'subject': email_obj.subject,
            'body_text': email_obj.body_text,
            'body_html': email_obj.body_html,
            'attachments': email_obj.attachments,
            'is_read': email_obj.is_read,
            'folder': email_obj.folder,
            'extracted_at': email_obj.extracted_at.isoformat()
        }
    
    def search_emails(self, search_criteria: Dict[str, Any]) -> List[Email]:
        """
        Search emails with specific criteria across all accounts
        
        Args:
            search_criteria: Search parameters
                - keywords: List of keywords to search in subject/body
                - sender_domains: List of sender domains to include
                - date_after: datetime object for emails after this date
                - date_before: datetime object for emails before this date
                - folders: List of folders to search (default: ['INBOX'])
                - include_read: bool (default: True)
                - include_unread: bool (default: True)
                
        Returns:
            List of matching Email objects
        """
        # Convert search criteria to filters format
        filters = {}
        
        # Date range
        date_after = search_criteria.get('date_after')
        date_before = search_criteria.get('date_before')
        if date_after or date_before:
            filters['date_range'] = (date_after, date_before)
        
        # Read status
        include_read = search_criteria.get('include_read', True)
        include_unread = search_criteria.get('include_unread', True)
        
        if include_unread and not include_read:
            filters['unread_only'] = True
        
        # Folders to search
        folders = search_criteria.get('folders', ['INBOX'])
        
        all_results = []
        
        for folder in folders:
            folder_filters = filters.copy()
            folder_filters['folder'] = folder
            
            folder_emails = self.extract_emails(folder_filters)
            
            # Apply keyword filtering
            keywords = search_criteria.get('keywords', [])
            if keywords:
                folder_emails = self._filter_by_keywords(folder_emails, keywords)
            
            # Apply sender domain filtering
            sender_domains = search_criteria.get('sender_domains', [])
            if sender_domains:
                folder_emails = self._filter_by_sender_domains(folder_emails, sender_domains)
            
            all_results.extend(folder_emails)
        
        return all_results
    
    def _filter_by_keywords(self, emails: List[Email], keywords: List[str]) -> List[Email]:
        """Filter emails by keywords in subject or body"""
        filtered_emails = []
        
        for email_obj in emails:
            # Combine searchable text
            searchable_text = f"{email_obj.subject} {email_obj.body_text} {email_obj.body_html}".lower()
            
            # Check if any keyword matches
            for keyword in keywords:
                if keyword.lower() in searchable_text:
                    filtered_emails.append(email_obj)
                    break
        
        return filtered_emails
    
    def _filter_by_sender_domains(self, emails: List[Email], domains: List[str]) -> List[Email]:
        """Filter emails by sender domains"""
        filtered_emails = []
        
        for email_obj in emails:
            sender_domain = email_obj.sender_email.split('@')[-1].lower() if '@' in email_obj.sender_email else ''
            
            for domain in domains:
                if sender_domain == domain.lower():
                    filtered_emails.append(email_obj)
                    break
        
        return filtered_emails
    
    def get_folder_list(self, account_id: str = None) -> Dict[str, List[str]]:
        """
        Get list of available folders for each account
        
        Args:
            account_id: Specific account ID, or None for all accounts
            
        Returns:
            Dict mapping account emails to their folder lists
        """
        folder_lists = {}
        
        accounts_to_check = []
        if account_id:
            # Find specific account
            for i, account_config in enumerate(self.accounts):
                if f"account_{i}" == account_id:
                    accounts_to_check.append((f"account_{i}", account_config))
                    break
        else:
            # Check all authenticated accounts
            for i, account_config in enumerate(self.accounts):
                account_key = f"account_{i}"
                if account_key in self.authenticated_accounts:
                    accounts_to_check.append((account_key, account_config))
        
        for account_key, account_config in accounts_to_check:
            try:
                connection = self.connection_pool.get_connection(account_key, account_config)
                if connection:
                    status, folder_list = connection.list()
                    if status == 'OK':
                        folders = []
                        for folder_info in folder_list:
                            # Parse folder name from IMAP LIST response
                            folder_parts = folder_info.decode().split('"')
                            if len(folder_parts) >= 3:
                                folder_name = folder_parts[-2]
                                folders.append(folder_name)
                        
                        account_email = account_config.get('email', account_key)
                        folder_lists[account_email] = folders
            except Exception as e:
                self.logger.error(f"Failed to get folder list for account {account_key}: {e}")
        
        return folder_lists
    
    def close_connections(self):
        """Close all IMAP connections"""
        self.connection_pool.close_all()
        self.authenticated_accounts.clear()
        self._authenticated = False
        self.logger.info("All email connections closed")
    
    def __del__(self):
        """Cleanup connections on object destruction"""
        try:
            self.close_connections()
        except:
            pass  # Ignore errors during cleanup