"""
WhatsApp data extractor

Extracts messages and media from WhatsApp using Business API or Twilio.
"""

import os
import time
import uuid
import requests
from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime
from urllib.parse import urlparse
import logging
from ..models import BaseExtractor, WhatsAppMessage, ExtractionResult
from ..utils.error_handler import (
    ErrorHandler, ErrorCategory, with_error_handling, graceful_degradation
)


class RateLimiter:
    """Rate limiter with exponential backoff"""
    
    def __init__(self, max_requests_per_minute: int = 60):
        self.max_requests_per_minute = max_requests_per_minute
        self.requests = []
        self.backoff_time = 1  # Start with 1 second backoff
        self.max_backoff = 300  # Maximum 5 minutes backoff
    
    def wait_if_needed(self):
        """Wait if rate limit would be exceeded"""
        now = time.time()
        # Remove requests older than 1 minute
        self.requests = [req_time for req_time in self.requests if now - req_time < 60]
        
        if len(self.requests) >= self.max_requests_per_minute:
            wait_time = 60 - (now - self.requests[0])
            if wait_time > 0:
                logging.info(f"Rate limit reached, waiting {wait_time:.2f} seconds")
                time.sleep(wait_time)
        
        self.requests.append(now)
    
    def handle_rate_limit_error(self):
        """Handle rate limit error with exponential backoff"""
        logging.warning(f"Rate limit error, backing off for {self.backoff_time} seconds")
        time.sleep(self.backoff_time)
        self.backoff_time = min(self.backoff_time * 2, self.max_backoff)
    
    def reset_backoff(self):
        """Reset backoff time after successful request"""
        self.backoff_time = 1


class WhatsAppExtractor(BaseExtractor):
    """WhatsApp message and media extractor"""
    
    def __init__(self, config: Dict[str, Any]):
        super().__init__(config)
        self.logger = logging.getLogger(__name__)
        
        # Initialize error handler
        self.error_handler = ErrorHandler(self.logger)
        
        # Determine API type and configuration
        self.api_type = self._determine_api_type(config)
        self.rate_limiter = RateLimiter(max_requests_per_minute=config.get('rate_limit', 60))
        
        # WhatsApp Business API configuration
        if self.api_type == 'business':
            self.api_token = config.get('api_token')
            self.phone_number_id = config.get('phone_number_id')
            self.base_url = config.get('base_url', 'https://graph.facebook.com/v18.0')
            self.webhook_verify_token = config.get('webhook_verify_token')
        
        # Twilio WhatsApp API configuration
        elif self.api_type == 'twilio':
            self.twilio_account_sid = config.get('twilio_account_sid')
            self.twilio_auth_token = config.get('twilio_auth_token')
            self.twilio_phone_number = config.get('twilio_phone_number')
            self.base_url = f'https://api.twilio.com/2010-04-01/Accounts/{self.twilio_account_sid}'
        
        # Common configuration
        self.timeout = config.get('timeout', 30)
        self.max_retries = config.get('max_retries', 3)
        self.session = requests.Session()
    
    def _determine_api_type(self, config: Dict[str, Any]) -> str:
        """Determine which API to use based on available configuration"""
        if config.get('api_token') and config.get('phone_number_id'):
            return 'business'
        elif config.get('twilio_account_sid') and config.get('twilio_auth_token'):
            return 'twilio'
        else:
            # Default to business API
            return 'business'
    
    def authenticate(self) -> bool:
        """
        Authenticate with WhatsApp API service
        
        Returns:
            bool: True if authentication successful, False otherwise
        """
        context = {'component': 'whatsapp_extractor', 'operation': 'authentication'}
        
        try:
            if self.api_type == 'business':
                return self.error_handler.with_retry(
                    self._authenticate_business_api,
                    category=ErrorCategory.AUTHENTICATION,
                    context=context
                )
            elif self.api_type == 'twilio':
                return self.error_handler.with_retry(
                    self._authenticate_twilio_api,
                    category=ErrorCategory.AUTHENTICATION,
                    context=context
                )
            else:
                self.logger.error(f"Unknown API type: {self.api_type}")
                return False
        except Exception as e:
            self.error_handler.handle_error(e, context, raise_on_critical=False)
            return False
    
    def _authenticate_business_api(self) -> bool:
        """Authenticate with WhatsApp Business API"""
        if not self.api_token or not self.phone_number_id:
            self.logger.error("WhatsApp Business API requires api_token and phone_number_id")
            return False
        
        try:
            # Test authentication by getting phone number info
            url = f"{self.base_url}/{self.phone_number_id}"
            headers = {
                'Authorization': f'Bearer {self.api_token}',
                'Content-Type': 'application/json'
            }
            
            self.rate_limiter.wait_if_needed()
            response = self.session.get(url, headers=headers, timeout=self.timeout)
            
            if response.status_code == 200:
                self.logger.info("WhatsApp Business API authentication successful")
                self._authenticated = True
                self.rate_limiter.reset_backoff()
                return True
            elif response.status_code == 429:
                self.rate_limiter.handle_rate_limit_error()
                return False
            else:
                self.logger.error(f"Business API authentication failed: {response.status_code} - {response.text}")
                return False
                
        except requests.exceptions.RequestException as e:
            self.logger.error(f"Business API authentication request failed: {e}")
            return False
    
    def _authenticate_twilio_api(self) -> bool:
        """Authenticate with Twilio WhatsApp API"""
        if not self.twilio_account_sid or not self.twilio_auth_token:
            self.logger.error("Twilio WhatsApp API requires twilio_account_sid and twilio_auth_token")
            return False
        
        try:
            # Test authentication by getting account info
            url = f"{self.base_url}.json"
            
            self.rate_limiter.wait_if_needed()
            response = self.session.get(
                url,
                auth=(self.twilio_account_sid, self.twilio_auth_token),
                timeout=self.timeout
            )
            
            if response.status_code == 200:
                self.logger.info("Twilio WhatsApp API authentication successful")
                self._authenticated = True
                self.rate_limiter.reset_backoff()
                return True
            elif response.status_code == 429:
                self.rate_limiter.handle_rate_limit_error()
                return False
            else:
                self.logger.error(f"Twilio API authentication failed: {response.status_code} - {response.text}")
                return False
                
        except requests.exceptions.RequestException as e:
            self.logger.error(f"Twilio API authentication request failed: {e}")
            return False
    
    def _make_authenticated_request(self, method: str, url: str, **kwargs) -> Optional[requests.Response]:
        """
        Make an authenticated request with error handling and retries
        
        Args:
            method: HTTP method (GET, POST, etc.)
            url: Request URL
            **kwargs: Additional request parameters
            
        Returns:
            Response object or None if failed
        """
        if not self._authenticated:
            self.logger.error("Not authenticated. Call authenticate() first.")
            return None
        
        # Add authentication headers
        if self.api_type == 'business':
            headers = kwargs.get('headers', {})
            headers['Authorization'] = f'Bearer {self.api_token}'
            headers['Content-Type'] = 'application/json'
            kwargs['headers'] = headers
        elif self.api_type == 'twilio':
            kwargs['auth'] = (self.twilio_account_sid, self.twilio_auth_token)
        
        # Add timeout
        kwargs['timeout'] = kwargs.get('timeout', self.timeout)
        
        # Retry logic with exponential backoff
        for attempt in range(self.max_retries):
            try:
                self.rate_limiter.wait_if_needed()
                response = self.session.request(method, url, **kwargs)
                
                if response.status_code == 200:
                    self.rate_limiter.reset_backoff()
                    return response
                elif response.status_code == 429:
                    self.rate_limiter.handle_rate_limit_error()
                    if attempt < self.max_retries - 1:
                        continue
                elif response.status_code in [401, 403]:
                    self.logger.error(f"Authentication error: {response.status_code} - {response.text}")
                    self._authenticated = False
                    return None
                else:
                    self.logger.warning(f"Request failed: {response.status_code} - {response.text}")
                    if attempt < self.max_retries - 1:
                        time.sleep(2 ** attempt)  # Exponential backoff
                        continue
                
                return response
                
            except requests.exceptions.RequestException as e:
                self.logger.error(f"Request attempt {attempt + 1} failed: {e}")
                if attempt < self.max_retries - 1:
                    time.sleep(2 ** attempt)  # Exponential backoff
                    continue
        
        self.logger.error(f"All {self.max_retries} request attempts failed")
        return None
    
    def extract_messages(self, date_range: Optional[Tuple[datetime, datetime]] = None) -> List[WhatsAppMessage]:
        """
        Extract messages from WhatsApp
        
        Args:
            date_range: Optional tuple of (start_date, end_date) for filtering
            
        Returns:
            List of WhatsAppMessage objects
        """
        if not self._authenticated:
            self.logger.error("Not authenticated. Call authenticate() first.")
            return []
        
        context = {'component': 'whatsapp_extractor', 'operation': 'extract_messages'}
        
        try:
            if self.api_type == 'business':
                return self.error_handler.with_retry(
                    self._extract_messages_business_api,
                    date_range,
                    category=ErrorCategory.NETWORK,
                    context=context
                )
            elif self.api_type == 'twilio':
                return self.error_handler.with_retry(
                    self._extract_messages_twilio_api,
                    date_range,
                    category=ErrorCategory.NETWORK,
                    context=context
                )
            else:
                self.logger.error(f"Unknown API type: {self.api_type}")
                return []
        except Exception as e:
            self.error_handler.handle_error(e, context, raise_on_critical=False)
            return []
    
    def _extract_messages_business_api(self, date_range: Optional[Tuple[datetime, datetime]] = None) -> List[WhatsAppMessage]:
        """Extract messages using WhatsApp Business API"""
        messages = []
        
        try:
            # WhatsApp Business API doesn't provide direct message history access
            # This would typically work with webhooks for real-time messages
            # For this implementation, we'll simulate the webhook message processing
            self.logger.info("WhatsApp Business API message extraction started")
            
            # In a real implementation, this would process webhook data
            # For now, we'll return an empty list and log the limitation
            self.logger.warning("WhatsApp Business API requires webhook setup for message extraction")
            self.logger.info("To extract messages, configure webhooks to receive message events")
            
            return messages
            
        except Exception as e:
            self.logger.error(f"Business API message extraction failed: {e}")
            return []
    
    def _extract_messages_twilio_api(self, date_range: Optional[Tuple[datetime, datetime]] = None) -> List[WhatsAppMessage]:
        """Extract messages using Twilio WhatsApp API"""
        messages = []
        
        try:
            self.logger.info("Twilio WhatsApp API message extraction started")
            
            # Build URL for messages endpoint
            url = f"{self.base_url}/Messages.json"
            
            # Build query parameters
            params = {
                'PageSize': 1000  # Maximum page size for Twilio
            }
            
            # Add date filtering if provided
            if date_range:
                start_date, end_date = date_range
                params['DateSent>'] = start_date.strftime('%Y-%m-%d')
                params['DateSent<'] = end_date.strftime('%Y-%m-%d')
            
            # Add WhatsApp filter
            if self.twilio_phone_number:
                params['From'] = f"whatsapp:{self.twilio_phone_number}"
            
            # Paginate through all messages
            next_page_uri = None
            page_count = 0
            
            while True:
                page_count += 1
                self.logger.debug(f"Fetching page {page_count}")
                
                # Use next page URI if available, otherwise use base URL with params
                if next_page_uri:
                    request_url = f"https://api.twilio.com{next_page_uri}"
                    response = self._make_authenticated_request('GET', request_url)
                else:
                    response = self._make_authenticated_request('GET', url, params=params)
                
                if not response or response.status_code != 200:
                    self.logger.error(f"Failed to fetch messages page {page_count}")
                    break
                
                try:
                    data = response.json()
                except ValueError as e:
                    self.logger.error(f"Invalid JSON response on page {page_count}: {e}")
                    break
                
                # Process messages from this page
                page_messages = data.get('messages', [])
                for msg_data in page_messages:
                    try:
                        message = self._parse_twilio_message(msg_data)
                        if message:
                            messages.append(message)
                    except Exception as e:
                        self.logger.warning(f"Failed to parse message {msg_data.get('sid', 'unknown')}: {e}")
                        continue
                
                self.logger.info(f"Processed page {page_count}: {len(page_messages)} messages")
                
                # Check for next page
                next_page_uri = data.get('next_page_uri')
                if not next_page_uri:
                    break
                
                # Safety check to prevent infinite loops
                if page_count >= 100:  # Arbitrary limit
                    self.logger.warning("Reached maximum page limit (100), stopping extraction")
                    break
            
            self.logger.info(f"Twilio message extraction completed: {len(messages)} messages extracted")
            return messages
            
        except Exception as e:
            self.logger.error(f"Twilio API message extraction failed: {e}")
            return []
    
    def _parse_twilio_message(self, msg_data: Dict[str, Any]) -> Optional[WhatsAppMessage]:
        """
        Parse Twilio message data into WhatsAppMessage object
        
        Args:
            msg_data: Raw message data from Twilio API
            
        Returns:
            WhatsAppMessage object or None if parsing fails
        """
        try:
            # Extract basic message information
            message_id = msg_data.get('sid')
            if not message_id:
                return None
            
            # Parse timestamp
            date_sent = msg_data.get('date_sent')
            if date_sent:
                # Twilio returns timestamps in RFC 2822 format
                timestamp = datetime.strptime(date_sent, '%a, %d %b %Y %H:%M:%S %z')
                # Convert to naive datetime (remove timezone info)
                timestamp = timestamp.replace(tzinfo=None)
            else:
                timestamp = datetime.now()
            
            # Extract sender phone number (remove 'whatsapp:' prefix if present)
            sender_phone = msg_data.get('from', '')
            if sender_phone.startswith('whatsapp:'):
                sender_phone = sender_phone[9:]  # Remove 'whatsapp:' prefix
            
            # Extract message content and determine type
            message_content = msg_data.get('body', '')
            message_type = self._determine_message_type_twilio(msg_data)
            
            # Extract media information if present
            media_url = None
            media_filename = None
            media_size = None
            
            num_media = int(msg_data.get('num_media', 0))
            if num_media > 0:
                # For Twilio, media URLs are in separate fields
                media_url = msg_data.get('media_url_0')  # First media item
                if media_url:
                    # Generate filename from media URL
                    media_filename = self._generate_media_filename(media_url, message_type)
            
            return WhatsAppMessage(
                id=message_id,
                timestamp=timestamp,
                sender_phone=sender_phone,
                message_content=message_content,
                message_type=message_type,
                media_url=media_url,
                media_filename=media_filename,
                media_size=media_size
            )
            
        except Exception as e:
            self.logger.error(f"Failed to parse Twilio message: {e}")
            return None
    
    def _determine_message_type_twilio(self, msg_data: Dict[str, Any]) -> str:
        """
        Determine message type from Twilio message data
        
        Args:
            msg_data: Raw message data from Twilio API
            
        Returns:
            Message type string
        """
        num_media = int(msg_data.get('num_media', 0))
        
        if num_media == 0:
            return 'text'
        
        # Check media content type if available
        media_content_type = msg_data.get('media_content_type_0', '')
        
        if media_content_type.startswith('image/'):
            return 'image'
        elif media_content_type.startswith('audio/'):
            return 'audio'
        elif media_content_type.startswith('video/'):
            return 'video'
        elif media_content_type.startswith('application/'):
            return 'document'
        else:
            return 'media'  # Generic media type
    
    def _generate_media_filename(self, media_url: str, message_type: str) -> str:
        """
        Generate a unique filename for media files
        
        Args:
            media_url: URL of the media file
            message_type: Type of message (image, audio, video, document)
            
        Returns:
            Generated filename
        """
        
        # Parse URL to get file extension
        parsed_url = urlparse(media_url)
        path = parsed_url.path
        
        # Try to extract extension from URL
        extension = ''
        if '.' in path:
            extension = path.split('.')[-1].lower()
        
        # Default extensions based on message type
        if not extension:
            extension_map = {
                'image': 'jpg',
                'audio': 'mp3',
                'video': 'mp4',
                'document': 'pdf'
            }
            extension = extension_map.get(message_type, 'bin')
        
        # Generate unique filename
        unique_id = str(uuid.uuid4())[:8]
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        return f"whatsapp_{message_type}_{timestamp}_{unique_id}.{extension}"
    
    def process_webhook_message(self, webhook_data: Dict[str, Any]) -> Optional[WhatsAppMessage]:
        """
        Process a webhook message from WhatsApp Business API
        
        Args:
            webhook_data: Webhook payload from WhatsApp
            
        Returns:
            WhatsAppMessage object or None if processing fails
        """
        try:
            # Extract message data from webhook payload
            entry = webhook_data.get('entry', [{}])[0]
            changes = entry.get('changes', [{}])[0]
            value = changes.get('value', {})
            messages = value.get('messages', [])
            
            if not messages:
                return None
            
            # Process first message (webhooks typically contain one message)
            msg_data = messages[0]
            
            # Extract basic information
            message_id = msg_data.get('id')
            timestamp_str = msg_data.get('timestamp')
            sender_phone = msg_data.get('from')
            
            # Convert timestamp
            if timestamp_str:
                timestamp = datetime.fromtimestamp(int(timestamp_str))
            else:
                timestamp = datetime.now()
            
            # Extract message content based on type
            message_type = msg_data.get('type', 'text')
            message_content = ''
            media_url = None
            media_filename = None
            media_size = None
            
            if message_type == 'text':
                message_content = msg_data.get('text', {}).get('body', '')
            elif message_type in ['image', 'audio', 'video', 'document']:
                media_data = msg_data.get(message_type, {})
                media_url = media_data.get('id')  # Media ID for Business API
                message_content = media_data.get('caption', '')
                media_filename = self._generate_media_filename(media_url or '', message_type)
                
                # For Business API, we need to make another call to get the actual media URL
                if media_url:
                    media_url = self._get_media_url_business_api(media_url)
            
            return WhatsAppMessage(
                id=message_id,
                timestamp=timestamp,
                sender_phone=sender_phone,
                message_content=message_content,
                message_type=message_type,
                media_url=media_url,
                media_filename=media_filename,
                media_size=media_size
            )
            
        except Exception as e:
            self.logger.error(f"Failed to process webhook message: {e}")
            return None
    
    def _get_media_url_business_api(self, media_id: str) -> Optional[str]:
        """
        Get media URL from WhatsApp Business API using media ID
        
        Args:
            media_id: Media ID from WhatsApp
            
        Returns:
            Media URL or None if failed
        """
        try:
            url = f"{self.base_url}/{media_id}"
            response = self._make_authenticated_request('GET', url)
            
            if response and response.status_code == 200:
                data = response.json()
                return data.get('url')
            else:
                self.logger.error(f"Failed to get media URL for ID {media_id}")
                return None
                
        except Exception as e:
            self.logger.error(f"Error getting media URL for ID {media_id}: {e}")
            return None
    
    def download_media(self, media_url: str, filename: str, output_dir: str = None) -> Optional[str]:
        """
        Download media file from WhatsApp
        
        Args:
            media_url: URL of the media file
            filename: Local filename to save as
            output_dir: Directory to save the file (optional)
            
        Returns:
            str: Path to downloaded file, or None if failed
        """
        if not self._authenticated:
            self.logger.error("Not authenticated. Call authenticate() first.")
            return None
        
        if not media_url:
            self.logger.error("Media URL is required")
            return None
        
        context = {
            'component': 'whatsapp_extractor', 
            'operation': 'download_media',
            'media_url': media_url,
            'filename': filename
        }
        
        # Determine output directory
        if output_dir is None:
            output_dir = './data/whatsapp/media'
        
        # Create output directory if it doesn't exist
        try:
            os.makedirs(output_dir, exist_ok=True)
        except Exception as e:
            self.error_handler.handle_error(e, context, raise_on_critical=False)
            return None
        
        # Full path for the file
        file_path = os.path.join(output_dir, filename)
        
        # Check if file already exists (deduplication)
        if os.path.exists(file_path):
            self.logger.info(f"Media file already exists: {file_path}")
            return file_path
        
        # Download with retry logic
        def _download_file():
            self.logger.info(f"Downloading media from {media_url} to {file_path}")
            
            response = self._make_authenticated_request('GET', media_url, stream=True)
            if not response or response.status_code != 200:
                raise requests.exceptions.HTTPError(f"HTTP {response.status_code if response else 'No response'}")
            
            # Save the file
            total_size = 0
            with open(file_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
                        total_size += len(chunk)
            
            self.logger.info(f"Media downloaded successfully: {file_path} ({total_size} bytes)")
            return file_path
        
        try:
            return self.error_handler.with_retry(
                _download_file,
                category=ErrorCategory.NETWORK,
                context=context
            )
        except Exception as e:
            self.error_handler.handle_error(e, context, raise_on_critical=False)
            return None
    
    def download_media_batch(self, media_items: List[Dict[str, str]], output_dir: str = None) -> Dict[str, Optional[str]]:
        """
        Download multiple media files in batch
        
        Args:
            media_items: List of dicts with 'url' and 'filename' keys
            output_dir: Directory to save files
            
        Returns:
            Dict mapping filenames to downloaded file paths (or None if failed)
        """
        results = {}
        
        for item in media_items:
            media_url = item.get('url')
            filename = item.get('filename')
            
            if not media_url or not filename:
                self.logger.warning(f"Skipping invalid media item: {item}")
                results[filename] = None
                continue
            
            try:
                file_path = self.download_media(media_url, filename, output_dir)
                results[filename] = file_path
                
                # Add small delay between downloads to be respectful
                time.sleep(0.1)
                
            except Exception as e:
                self.logger.error(f"Failed to download {filename}: {e}")
                results[filename] = None
        
        return results
    
    def organize_media_files(self, base_dir: str, date: datetime = None) -> str:
        """
        Create organized directory structure for media files
        
        Args:
            base_dir: Base directory for media storage
            date: Date for organization (defaults to current date)
            
        Returns:
            Path to the organized directory
        """
        if date is None:
            date = datetime.now()
        
        # Create date-based directory structure
        date_str = date.strftime('%Y-%m-%d')
        media_dir = os.path.join(base_dir, 'whatsapp', date_str, 'media')
        
        try:
            os.makedirs(media_dir, exist_ok=True)
            self.logger.debug(f"Created media directory: {media_dir}")
            return media_dir
        except Exception as e:
            self.logger.error(f"Failed to create media directory {media_dir}: {e}")
            # Fallback to base directory
            fallback_dir = os.path.join(base_dir, 'whatsapp', 'media')
            os.makedirs(fallback_dir, exist_ok=True)
            return fallback_dir
    
    def get_media_info(self, media_url: str) -> Optional[Dict[str, Any]]:
        """
        Get media file information without downloading
        
        Args:
            media_url: URL of the media file
            
        Returns:
            Dict with media info (size, content_type, etc.) or None if failed
        """
        if not self._authenticated:
            self.logger.error("Not authenticated. Call authenticate() first.")
            return None
        
        try:
            # Make HEAD request to get file info
            response = self._make_authenticated_request('HEAD', media_url)
            if not response or response.status_code != 200:
                return None
            
            headers = response.headers
            info = {
                'content_type': headers.get('content-type', 'unknown'),
                'content_length': int(headers.get('content-length', 0)),
                'last_modified': headers.get('last-modified'),
                'etag': headers.get('etag')
            }
            
            return info
            
        except Exception as e:
            self.logger.error(f"Failed to get media info for {media_url}: {e}")
            return None
    
    def validate_media_file(self, file_path: str, expected_size: int = None) -> bool:
        """
        Validate downloaded media file
        
        Args:
            file_path: Path to the downloaded file
            expected_size: Expected file size in bytes (optional)
            
        Returns:
            True if file is valid, False otherwise
        """
        try:
            if not os.path.exists(file_path):
                self.logger.error(f"Media file does not exist: {file_path}")
                return False
            
            file_size = os.path.getsize(file_path)
            
            if file_size == 0:
                self.logger.error(f"Media file is empty: {file_path}")
                return False
            
            if expected_size and file_size != expected_size:
                self.logger.warning(f"Media file size mismatch: expected {expected_size}, got {file_size}")
                return False
            
            self.logger.debug(f"Media file validation passed: {file_path} ({file_size} bytes)")
            return True
            
        except Exception as e:
            self.logger.error(f"Media file validation failed for {file_path}: {e}")
            return False
    
    def cleanup_failed_downloads(self, output_dir: str) -> int:
        """
        Clean up failed or incomplete media downloads
        
        Args:
            output_dir: Directory to clean up
            
        Returns:
            Number of files cleaned up
        """
        cleaned_count = 0
        
        try:
            if not os.path.exists(output_dir):
                return 0
            
            for filename in os.listdir(output_dir):
                file_path = os.path.join(output_dir, filename)
                
                if os.path.isfile(file_path):
                    # Check if file is empty or very small (likely failed download)
                    file_size = os.path.getsize(file_path)
                    if file_size < 100:  # Less than 100 bytes is likely incomplete
                        try:
                            os.remove(file_path)
                            self.logger.info(f"Cleaned up failed download: {file_path}")
                            cleaned_count += 1
                        except Exception as e:
                            self.logger.warning(f"Failed to clean up {file_path}: {e}")
            
            return cleaned_count
            
        except Exception as e:
            self.logger.error(f"Cleanup failed for {output_dir}: {e}")
            return 0
    
    def extract_data(self, **kwargs) -> List[Dict[str, Any]]:
        """
        Extract data from WhatsApp (implements BaseExtractor interface)
        
        Returns:
            List of message dictionaries
        """
        date_range = kwargs.get('date_range')
        messages = self.extract_messages(date_range)
        return [self._message_to_dict(msg) for msg in messages]
    
    def save_data(self, data: List[Dict[str, Any]], output_path: str) -> None:
        """
        Save extracted WhatsApp data to storage
        
        Args:
            data: List of message dictionaries
            output_path: Path to save data
        """
        # Implementation will be added in later tasks
        raise NotImplementedError("Data saving will be implemented in task 4")
    
    def _message_to_dict(self, message: WhatsAppMessage) -> Dict[str, Any]:
        """Convert WhatsAppMessage to dictionary"""
        return {
            'id': message.id,
            'timestamp': message.timestamp.isoformat(),
            'sender_phone': message.sender_phone,
            'message_content': message.message_content,
            'message_type': message.message_type,
            'media_url': message.media_url,
            'media_filename': message.media_filename,
            'media_size': message.media_size,
            'extracted_at': message.extracted_at.isoformat()
        }
    
    def get_api_info(self) -> Dict[str, Any]:
        """
        Get information about the configured API
        
        Returns:
            Dict containing API configuration info
        """
        info = {
            'api_type': self.api_type,
            'authenticated': self._authenticated,
            'rate_limit': self.rate_limiter.max_requests_per_minute,
            'timeout': self.timeout,
            'max_retries': self.max_retries
        }
        
        if self.api_type == 'business':
            info.update({
                'phone_number_id': self.phone_number_id,
                'base_url': self.base_url
            })
        elif self.api_type == 'twilio':
            info.update({
                'account_sid': self.twilio_account_sid,
                'phone_number': self.twilio_phone_number,
                'base_url': self.base_url
            })
        
        return info
    
    def close(self):
        """Close the session and cleanup resources"""
        if hasattr(self, 'session'):
            self.session.close()
            self.logger.info("WhatsApp extractor session closed")