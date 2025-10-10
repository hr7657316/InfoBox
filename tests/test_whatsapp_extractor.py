"""
Unit tests for WhatsApp extractor
"""

import unittest
from unittest.mock import Mock, patch, MagicMock
import requests
import time
import os
from datetime import datetime

from pipeline.whatsapp.whatsapp_extractor import WhatsAppExtractor, RateLimiter


class TestRateLimiter(unittest.TestCase):
    """Test cases for RateLimiter class"""
    
    def setUp(self):
        self.rate_limiter = RateLimiter(max_requests_per_minute=60)
    
    def test_init(self):
        """Test RateLimiter initialization"""
        self.assertEqual(self.rate_limiter.max_requests_per_minute, 60)
        self.assertEqual(self.rate_limiter.requests, [])
        self.assertEqual(self.rate_limiter.backoff_time, 1)
        self.assertEqual(self.rate_limiter.max_backoff, 300)
    
    @patch('time.time')
    @patch('time.sleep')
    def test_wait_if_needed_no_wait(self, mock_sleep, mock_time):
        """Test wait_if_needed when no waiting is required"""
        mock_time.return_value = 100.0
        
        # Add some old requests (should be cleaned up)
        self.rate_limiter.requests = [30.0, 35.0]  # More than 60 seconds old
        
        self.rate_limiter.wait_if_needed()
        
        # Should not sleep and should clean up old requests
        mock_sleep.assert_not_called()
        self.assertEqual(len(self.rate_limiter.requests), 1)  # Only the new request
        self.assertEqual(self.rate_limiter.requests[0], 100.0)
    
    @patch('time.time')
    @patch('time.sleep')
    def test_wait_if_needed_with_wait(self, mock_sleep, mock_time):
        """Test wait_if_needed when waiting is required"""
        mock_time.return_value = 100.0
        
        # Fill up the rate limit with recent requests
        recent_requests = [100.0 - i for i in range(60)]  # 60 requests in the last minute
        self.rate_limiter.requests = recent_requests
        
        self.rate_limiter.wait_if_needed()
        
        # Should sleep for the remaining time
        mock_sleep.assert_called_once()
        sleep_time = mock_sleep.call_args[0][0]
        self.assertGreater(sleep_time, 0)
    
    @patch('time.sleep')
    def test_handle_rate_limit_error(self, mock_sleep):
        """Test rate limit error handling with exponential backoff"""
        initial_backoff = self.rate_limiter.backoff_time
        
        self.rate_limiter.handle_rate_limit_error()
        
        mock_sleep.assert_called_once_with(initial_backoff)
        self.assertEqual(self.rate_limiter.backoff_time, initial_backoff * 2)
    
    def test_reset_backoff(self):
        """Test backoff reset"""
        self.rate_limiter.backoff_time = 16
        self.rate_limiter.reset_backoff()
        self.assertEqual(self.rate_limiter.backoff_time, 1)


class TestWhatsAppExtractor(unittest.TestCase):
    """Test cases for WhatsAppExtractor class"""
    
    def setUp(self):
        self.business_config = {
            'api_token': 'test_business_token',
            'phone_number_id': 'test_phone_id',
            'base_url': 'https://graph.facebook.com/v18.0'
        }
        
        self.twilio_config = {
            'twilio_account_sid': 'test_account_sid',
            'twilio_auth_token': 'test_auth_token',
            'twilio_phone_number': '+1234567890'
        }
    
    def test_init_business_api(self):
        """Test initialization with Business API configuration"""
        extractor = WhatsAppExtractor(self.business_config)
        
        self.assertEqual(extractor.api_type, 'business')
        self.assertEqual(extractor.api_token, 'test_business_token')
        self.assertEqual(extractor.phone_number_id, 'test_phone_id')
        self.assertEqual(extractor.base_url, 'https://graph.facebook.com/v18.0')
        self.assertFalse(extractor._authenticated)
    
    def test_init_twilio_api(self):
        """Test initialization with Twilio API configuration"""
        extractor = WhatsAppExtractor(self.twilio_config)
        
        self.assertEqual(extractor.api_type, 'twilio')
        self.assertEqual(extractor.twilio_account_sid, 'test_account_sid')
        self.assertEqual(extractor.twilio_auth_token, 'test_auth_token')
        self.assertEqual(extractor.twilio_phone_number, '+1234567890')
        self.assertFalse(extractor._authenticated)
    
    def test_determine_api_type_business(self):
        """Test API type determination for Business API"""
        extractor = WhatsAppExtractor(self.business_config)
        api_type = extractor._determine_api_type(self.business_config)
        self.assertEqual(api_type, 'business')
    
    def test_determine_api_type_twilio(self):
        """Test API type determination for Twilio API"""
        extractor = WhatsAppExtractor(self.twilio_config)
        api_type = extractor._determine_api_type(self.twilio_config)
        self.assertEqual(api_type, 'twilio')
    
    def test_determine_api_type_default(self):
        """Test API type determination with incomplete config"""
        incomplete_config = {'some_other_key': 'value'}
        extractor = WhatsAppExtractor(incomplete_config)
        api_type = extractor._determine_api_type(incomplete_config)
        self.assertEqual(api_type, 'business')  # Should default to business
    
    @patch('pipeline.whatsapp.whatsapp_extractor.requests.Session.get')
    def test_authenticate_business_api_success(self, mock_get):
        """Test successful Business API authentication"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_get.return_value = mock_response
        
        extractor = WhatsAppExtractor(self.business_config)
        result = extractor.authenticate()
        
        self.assertTrue(result)
        self.assertTrue(extractor._authenticated)
        mock_get.assert_called_once()
    
    @patch('pipeline.whatsapp.whatsapp_extractor.requests.Session.get')
    def test_authenticate_business_api_failure(self, mock_get):
        """Test failed Business API authentication"""
        mock_response = Mock()
        mock_response.status_code = 401
        mock_response.text = 'Unauthorized'
        mock_get.return_value = mock_response
        
        extractor = WhatsAppExtractor(self.business_config)
        result = extractor.authenticate()
        
        self.assertFalse(result)
        self.assertFalse(extractor._authenticated)
    
    @patch('pipeline.whatsapp.whatsapp_extractor.requests.Session.get')
    def test_authenticate_twilio_api_success(self, mock_get):
        """Test successful Twilio API authentication"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_get.return_value = mock_response
        
        extractor = WhatsAppExtractor(self.twilio_config)
        result = extractor.authenticate()
        
        self.assertTrue(result)
        self.assertTrue(extractor._authenticated)
        mock_get.assert_called_once()
    
    @patch('pipeline.whatsapp.whatsapp_extractor.requests.Session.get')
    def test_authenticate_twilio_api_failure(self, mock_get):
        """Test failed Twilio API authentication"""
        mock_response = Mock()
        mock_response.status_code = 401
        mock_response.text = 'Unauthorized'
        mock_get.return_value = mock_response
        
        extractor = WhatsAppExtractor(self.twilio_config)
        result = extractor.authenticate()
        
        self.assertFalse(result)
        self.assertFalse(extractor._authenticated)
    
    def test_authenticate_missing_credentials_business(self):
        """Test authentication with missing Business API credentials"""
        incomplete_config = {'api_token': 'token'}  # Missing phone_number_id
        extractor = WhatsAppExtractor(incomplete_config)
        result = extractor.authenticate()
        
        self.assertFalse(result)
        self.assertFalse(extractor._authenticated)
    
    def test_authenticate_missing_credentials_twilio(self):
        """Test authentication with missing Twilio credentials"""
        incomplete_config = {
            'twilio_account_sid': 'sid'  # Missing twilio_auth_token
        }
        extractor = WhatsAppExtractor(incomplete_config)
        result = extractor.authenticate()
        
        self.assertFalse(result)
        self.assertFalse(extractor._authenticated)
    
    @patch('pipeline.whatsapp.whatsapp_extractor.requests.Session.request')
    def test_make_authenticated_request_not_authenticated(self, mock_request):
        """Test making request when not authenticated"""
        extractor = WhatsAppExtractor(self.business_config)
        result = extractor._make_authenticated_request('GET', 'http://test.com')
        
        self.assertIsNone(result)
        mock_request.assert_not_called()
    
    @patch('pipeline.whatsapp.whatsapp_extractor.requests.Session.request')
    def test_make_authenticated_request_business_success(self, mock_request):
        """Test successful authenticated request for Business API"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_request.return_value = mock_response
        
        extractor = WhatsAppExtractor(self.business_config)
        extractor._authenticated = True  # Simulate authenticated state
        
        result = extractor._make_authenticated_request('GET', 'http://test.com')
        
        self.assertEqual(result, mock_response)
        mock_request.assert_called_once()
        
        # Check that authorization header was added
        call_args = mock_request.call_args
        headers = call_args[1]['headers']
        self.assertEqual(headers['Authorization'], 'Bearer test_business_token')
    
    @patch('pipeline.whatsapp.whatsapp_extractor.requests.Session.request')
    def test_make_authenticated_request_twilio_success(self, mock_request):
        """Test successful authenticated request for Twilio API"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_request.return_value = mock_response
        
        extractor = WhatsAppExtractor(self.twilio_config)
        extractor._authenticated = True  # Simulate authenticated state
        
        result = extractor._make_authenticated_request('GET', 'http://test.com')
        
        self.assertEqual(result, mock_response)
        mock_request.assert_called_once()
        
        # Check that auth tuple was added
        call_args = mock_request.call_args
        auth = call_args[1]['auth']
        self.assertEqual(auth, ('test_account_sid', 'test_auth_token'))
    
    @patch('pipeline.whatsapp.whatsapp_extractor.requests.Session.request')
    @patch('time.sleep')
    def test_make_authenticated_request_retry_logic(self, mock_sleep, mock_request):
        """Test retry logic with exponential backoff"""
        # First two calls fail, third succeeds
        mock_responses = [
            Mock(status_code=500, text='Server Error'),
            Mock(status_code=500, text='Server Error'),
            Mock(status_code=200)
        ]
        mock_request.side_effect = mock_responses
        
        extractor = WhatsAppExtractor(self.business_config)
        extractor._authenticated = True
        extractor.max_retries = 3
        
        result = extractor._make_authenticated_request('GET', 'http://test.com')
        
        self.assertEqual(result, mock_responses[2])
        self.assertEqual(mock_request.call_count, 3)
        self.assertEqual(mock_sleep.call_count, 2)  # Sleep between retries
    
    def test_get_api_info_business(self):
        """Test getting API info for Business API"""
        extractor = WhatsAppExtractor(self.business_config)
        info = extractor.get_api_info()
        
        expected_keys = ['api_type', 'authenticated', 'rate_limit', 'timeout', 
                        'max_retries', 'phone_number_id', 'base_url']
        for key in expected_keys:
            self.assertIn(key, info)
        
        self.assertEqual(info['api_type'], 'business')
        self.assertEqual(info['phone_number_id'], 'test_phone_id')
    
    def test_get_api_info_twilio(self):
        """Test getting API info for Twilio API"""
        extractor = WhatsAppExtractor(self.twilio_config)
        info = extractor.get_api_info()
        
        expected_keys = ['api_type', 'authenticated', 'rate_limit', 'timeout', 
                        'max_retries', 'account_sid', 'phone_number', 'base_url']
        for key in expected_keys:
            self.assertIn(key, info)
        
        self.assertEqual(info['api_type'], 'twilio')
        self.assertEqual(info['account_sid'], 'test_account_sid')
    
    def test_close(self):
        """Test closing the extractor"""
        extractor = WhatsAppExtractor(self.business_config)
        mock_session = Mock()
        extractor.session = mock_session
        
        extractor.close()
        
        mock_session.close.assert_called_once()
    
    def test_extract_messages_not_authenticated(self):
        """Test extract_messages when not authenticated"""
        extractor = WhatsAppExtractor(self.business_config)
        messages = extractor.extract_messages()
        
        self.assertEqual(messages, [])
    
    @patch('pipeline.whatsapp.whatsapp_extractor.requests.Session.request')
    def test_extract_messages_twilio_success(self, mock_request):
        """Test successful message extraction with Twilio API"""
        # Mock response data
        mock_response_data = {
            'messages': [
                {
                    'sid': 'test_message_1',
                    'date_sent': 'Mon, 01 Jan 2024 12:00:00 +0000',
                    'from': 'whatsapp:+1234567890',
                    'body': 'Test message 1',
                    'num_media': '0'
                },
                {
                    'sid': 'test_message_2',
                    'date_sent': 'Mon, 01 Jan 2024 12:05:00 +0000',
                    'from': 'whatsapp:+1234567891',
                    'body': 'Test message 2',
                    'num_media': '1',
                    'media_url_0': 'https://api.twilio.com/media/test.jpg',
                    'media_content_type_0': 'image/jpeg'
                }
            ],
            'next_page_uri': None
        }
        
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = mock_response_data
        mock_request.return_value = mock_response
        
        extractor = WhatsAppExtractor(self.twilio_config)
        extractor._authenticated = True
        
        messages = extractor.extract_messages()
        
        self.assertEqual(len(messages), 2)
        self.assertEqual(messages[0].id, 'test_message_1')
        self.assertEqual(messages[0].sender_phone, '+1234567890')
        self.assertEqual(messages[0].message_content, 'Test message 1')
        self.assertEqual(messages[0].message_type, 'text')
        
        self.assertEqual(messages[1].id, 'test_message_2')
        self.assertEqual(messages[1].message_type, 'image')
        self.assertIsNotNone(messages[1].media_filename)
    
    def test_extract_messages_business_api_limitation(self):
        """Test Business API message extraction limitation"""
        extractor = WhatsAppExtractor(self.business_config)
        extractor._authenticated = True
        
        messages = extractor.extract_messages()
        
        # Business API should return empty list due to webhook requirement
        self.assertEqual(messages, [])
    
    def test_parse_twilio_message_text(self):
        """Test parsing text message from Twilio"""
        extractor = WhatsAppExtractor(self.twilio_config)
        
        msg_data = {
            'sid': 'test_message_id',
            'date_sent': 'Mon, 01 Jan 2024 12:00:00 +0000',
            'from': 'whatsapp:+1234567890',
            'body': 'Hello, world!',
            'num_media': '0'
        }
        
        message = extractor._parse_twilio_message(msg_data)
        
        self.assertIsNotNone(message)
        self.assertEqual(message.id, 'test_message_id')
        self.assertEqual(message.sender_phone, '+1234567890')
        self.assertEqual(message.message_content, 'Hello, world!')
        self.assertEqual(message.message_type, 'text')
        self.assertIsNone(message.media_url)
    
    def test_parse_twilio_message_with_media(self):
        """Test parsing message with media from Twilio"""
        extractor = WhatsAppExtractor(self.twilio_config)
        
        msg_data = {
            'sid': 'test_message_id',
            'date_sent': 'Mon, 01 Jan 2024 12:00:00 +0000',
            'from': 'whatsapp:+1234567890',
            'body': 'Check this image',
            'num_media': '1',
            'media_url_0': 'https://api.twilio.com/media/test.jpg',
            'media_content_type_0': 'image/jpeg'
        }
        
        message = extractor._parse_twilio_message(msg_data)
        
        self.assertIsNotNone(message)
        self.assertEqual(message.message_type, 'image')
        self.assertEqual(message.media_url, 'https://api.twilio.com/media/test.jpg')
        self.assertIsNotNone(message.media_filename)
        self.assertTrue(message.media_filename.endswith('.jpg'))
    
    def test_parse_twilio_message_invalid_data(self):
        """Test parsing invalid message data"""
        extractor = WhatsAppExtractor(self.twilio_config)
        
        # Missing required fields
        msg_data = {
            'body': 'Test message'
            # Missing 'sid' field
        }
        
        message = extractor._parse_twilio_message(msg_data)
        self.assertIsNone(message)
    
    def test_determine_message_type_twilio(self):
        """Test message type determination for Twilio messages"""
        extractor = WhatsAppExtractor(self.twilio_config)
        
        # Text message
        msg_data = {'num_media': '0'}
        self.assertEqual(extractor._determine_message_type_twilio(msg_data), 'text')
        
        # Image message
        msg_data = {'num_media': '1', 'media_content_type_0': 'image/jpeg'}
        self.assertEqual(extractor._determine_message_type_twilio(msg_data), 'image')
        
        # Audio message
        msg_data = {'num_media': '1', 'media_content_type_0': 'audio/mpeg'}
        self.assertEqual(extractor._determine_message_type_twilio(msg_data), 'audio')
        
        # Video message
        msg_data = {'num_media': '1', 'media_content_type_0': 'video/mp4'}
        self.assertEqual(extractor._determine_message_type_twilio(msg_data), 'video')
        
        # Document message
        msg_data = {'num_media': '1', 'media_content_type_0': 'application/pdf'}
        self.assertEqual(extractor._determine_message_type_twilio(msg_data), 'document')
        
        # Unknown media type
        msg_data = {'num_media': '1', 'media_content_type_0': 'unknown/type'}
        self.assertEqual(extractor._determine_message_type_twilio(msg_data), 'media')
    
    def test_generate_media_filename(self):
        """Test media filename generation"""
        extractor = WhatsAppExtractor(self.business_config)
        
        # Test with URL containing extension
        filename = extractor._generate_media_filename('https://example.com/image.jpg', 'image')
        self.assertTrue(filename.startswith('whatsapp_image_'))
        self.assertTrue(filename.endswith('.jpg'))
        
        # Test with URL without extension
        filename = extractor._generate_media_filename('https://example.com/media', 'audio')
        self.assertTrue(filename.startswith('whatsapp_audio_'))
        self.assertTrue(filename.endswith('.mp3'))
        
        # Test unknown message type
        filename = extractor._generate_media_filename('https://example.com/file', 'unknown')
        self.assertTrue(filename.endswith('.bin'))
    
    def test_process_webhook_message_text(self):
        """Test processing webhook message with text content"""
        extractor = WhatsAppExtractor(self.business_config)
        
        webhook_data = {
            'entry': [{
                'changes': [{
                    'value': {
                        'messages': [{
                            'id': 'webhook_msg_1',
                            'timestamp': '1704110400',  # Jan 1, 2024 12:00:00 UTC
                            'from': '+1234567890',
                            'type': 'text',
                            'text': {
                                'body': 'Hello from webhook!'
                            }
                        }]
                    }
                }]
            }]
        }
        
        message = extractor.process_webhook_message(webhook_data)
        
        self.assertIsNotNone(message)
        self.assertEqual(message.id, 'webhook_msg_1')
        self.assertEqual(message.sender_phone, '+1234567890')
        self.assertEqual(message.message_content, 'Hello from webhook!')
        self.assertEqual(message.message_type, 'text')
    
    @patch('pipeline.whatsapp.whatsapp_extractor.WhatsAppExtractor._get_media_url_business_api')
    def test_process_webhook_message_with_media(self, mock_get_media_url):
        """Test processing webhook message with media content"""
        mock_get_media_url.return_value = 'https://example.com/media.jpg'
        
        extractor = WhatsAppExtractor(self.business_config)
        extractor._authenticated = True  # Set authenticated for media URL retrieval
        
        webhook_data = {
            'entry': [{
                'changes': [{
                    'value': {
                        'messages': [{
                            'id': 'webhook_msg_2',
                            'timestamp': '1704110400',
                            'from': '+1234567890',
                            'type': 'image',
                            'image': {
                                'id': 'media_id_123',
                                'caption': 'Check this out!'
                            }
                        }]
                    }
                }]
            }]
        }
        
        message = extractor.process_webhook_message(webhook_data)
        
        self.assertIsNotNone(message)
        self.assertEqual(message.message_type, 'image')
        self.assertEqual(message.message_content, 'Check this out!')
        self.assertEqual(message.media_url, 'https://example.com/media.jpg')
        self.assertIsNotNone(message.media_filename)
        mock_get_media_url.assert_called_once_with('media_id_123')
    
    def test_process_webhook_message_invalid(self):
        """Test processing invalid webhook data"""
        extractor = WhatsAppExtractor(self.business_config)
        
        # Empty webhook data
        message = extractor.process_webhook_message({})
        self.assertIsNone(message)
        
        # Webhook data without messages
        webhook_data = {
            'entry': [{
                'changes': [{
                    'value': {}
                }]
            }]
        }
        message = extractor.process_webhook_message(webhook_data)
        self.assertIsNone(message)
    
    @patch('pipeline.whatsapp.whatsapp_extractor.requests.Session.request')
    def test_get_media_url_business_api_success(self, mock_request):
        """Test successful media URL retrieval from Business API"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.json.return_value = {'url': 'https://example.com/media.jpg'}
        mock_request.return_value = mock_response
        
        extractor = WhatsAppExtractor(self.business_config)
        extractor._authenticated = True
        
        media_url = extractor._get_media_url_business_api('media_id_123')
        
        self.assertEqual(media_url, 'https://example.com/media.jpg')
        mock_request.assert_called_once()
    
    @patch('pipeline.whatsapp.whatsapp_extractor.requests.Session.request')
    def test_get_media_url_business_api_failure(self, mock_request):
        """Test failed media URL retrieval from Business API"""
        mock_response = Mock()
        mock_response.status_code = 404
        mock_request.return_value = mock_response
        
        extractor = WhatsAppExtractor(self.business_config)
        extractor._authenticated = True
        
        media_url = extractor._get_media_url_business_api('invalid_media_id')
        
        self.assertIsNone(media_url)
    
    def test_download_media_not_authenticated(self):
        """Test download_media when not authenticated"""
        extractor = WhatsAppExtractor(self.business_config)
        result = extractor.download_media('http://test.com/media', 'test.jpg')
        
        self.assertIsNone(result)
    
    def test_download_media_no_url(self):
        """Test download_media with empty URL"""
        extractor = WhatsAppExtractor(self.business_config)
        extractor._authenticated = True
        
        result = extractor.download_media('', 'test.jpg')
        self.assertIsNone(result)
        
        result = extractor.download_media(None, 'test.jpg')
        self.assertIsNone(result)
    
    @patch('pipeline.whatsapp.whatsapp_extractor.requests.Session.request')
    @patch('os.makedirs')
    @patch('os.path.exists')
    @patch('builtins.open', create=True)
    def test_download_media_success(self, mock_open, mock_exists, mock_makedirs, mock_request):
        """Test successful media download"""
        # Mock file doesn't exist (no deduplication)
        mock_exists.return_value = False
        
        # Mock successful HTTP response
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.iter_content.return_value = [b'chunk1', b'chunk2', b'chunk3']
        mock_request.return_value = mock_response
        
        # Mock file operations
        mock_file = Mock()
        mock_open.return_value.__enter__.return_value = mock_file
        
        extractor = WhatsAppExtractor(self.business_config)
        extractor._authenticated = True
        
        result = extractor.download_media('http://test.com/media.jpg', 'test.jpg', '/tmp/test')
        
        self.assertEqual(result, '/tmp/test/test.jpg')
        mock_makedirs.assert_called_once_with('/tmp/test', exist_ok=True)
        mock_request.assert_called_once()
        mock_file.write.assert_called()
    
    @patch('os.path.exists')
    def test_download_media_file_exists(self, mock_exists):
        """Test download_media when file already exists (deduplication)"""
        mock_exists.return_value = True
        
        extractor = WhatsAppExtractor(self.business_config)
        extractor._authenticated = True
        
        result = extractor.download_media('http://test.com/media.jpg', 'test.jpg', '/tmp/test')
        
        self.assertEqual(result, '/tmp/test/test.jpg')
    
    @patch('pipeline.whatsapp.whatsapp_extractor.requests.Session.request')
    @patch('os.makedirs')
    @patch('os.path.exists')
    def test_download_media_http_failure(self, mock_exists, mock_makedirs, mock_request):
        """Test download_media with HTTP failure"""
        mock_exists.return_value = False
        
        # Mock failed HTTP response
        mock_response = Mock()
        mock_response.status_code = 404
        mock_request.return_value = mock_response
        
        extractor = WhatsAppExtractor(self.business_config)
        extractor._authenticated = True
        
        result = extractor.download_media('http://test.com/media.jpg', 'test.jpg')
        
        self.assertIsNone(result)
    
    @patch('pipeline.whatsapp.whatsapp_extractor.WhatsAppExtractor.download_media')
    @patch('time.sleep')
    def test_download_media_batch_success(self, mock_sleep, mock_download):
        """Test successful batch media download"""
        mock_download.side_effect = ['/tmp/file1.jpg', '/tmp/file2.mp4', None]
        
        extractor = WhatsAppExtractor(self.business_config)
        
        media_items = [
            {'url': 'http://test.com/file1.jpg', 'filename': 'file1.jpg'},
            {'url': 'http://test.com/file2.mp4', 'filename': 'file2.mp4'},
            {'url': 'http://test.com/file3.pdf', 'filename': 'file3.pdf'}
        ]
        
        results = extractor.download_media_batch(media_items, '/tmp/test')
        
        expected_results = {
            'file1.jpg': '/tmp/file1.jpg',
            'file2.mp4': '/tmp/file2.mp4',
            'file3.pdf': None
        }
        
        self.assertEqual(results, expected_results)
        self.assertEqual(mock_download.call_count, 3)
        self.assertEqual(mock_sleep.call_count, 3)  # Sleep after each download
    
    def test_download_media_batch_invalid_items(self):
        """Test batch download with invalid items"""
        extractor = WhatsAppExtractor(self.business_config)
        
        media_items = [
            {'url': 'http://test.com/file1.jpg'},  # Missing filename
            {'filename': 'file2.jpg'},  # Missing URL
            {'url': '', 'filename': 'file3.jpg'},  # Empty URL
        ]
        
        results = extractor.download_media_batch(media_items)
        
        expected_results = {
            None: None,  # Invalid item
            'file2.jpg': None,
            'file3.jpg': None
        }
        
        # All should fail
        for filename, result in results.items():
            self.assertIsNone(result)
    
    @patch('os.makedirs')
    def test_organize_media_files_success(self, mock_makedirs):
        """Test successful media file organization"""
        extractor = WhatsAppExtractor(self.business_config)
        
        test_date = datetime(2024, 1, 15)
        result = extractor.organize_media_files('/tmp/base', test_date)
        
        expected_path = '/tmp/base/whatsapp/2024-01-15/media'
        self.assertEqual(result, expected_path)
        mock_makedirs.assert_called_once_with(expected_path, exist_ok=True)
    
    @patch('os.makedirs')
    def test_organize_media_files_fallback(self, mock_makedirs):
        """Test media file organization with fallback"""
        # First call fails, second succeeds (fallback)
        mock_makedirs.side_effect = [OSError("Permission denied"), None]
        
        extractor = WhatsAppExtractor(self.business_config)
        
        result = extractor.organize_media_files('/tmp/base')
        
        expected_fallback = '/tmp/base/whatsapp/media'
        self.assertEqual(result, expected_fallback)
        self.assertEqual(mock_makedirs.call_count, 2)
    
    @patch('pipeline.whatsapp.whatsapp_extractor.requests.Session.request')
    def test_get_media_info_success(self, mock_request):
        """Test successful media info retrieval"""
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.headers = {
            'content-type': 'image/jpeg',
            'content-length': '12345',
            'last-modified': 'Mon, 01 Jan 2024 12:00:00 GMT',
            'etag': '"abc123"'
        }
        mock_request.return_value = mock_response
        
        extractor = WhatsAppExtractor(self.business_config)
        extractor._authenticated = True
        
        info = extractor.get_media_info('http://test.com/media.jpg')
        
        expected_info = {
            'content_type': 'image/jpeg',
            'content_length': 12345,
            'last_modified': 'Mon, 01 Jan 2024 12:00:00 GMT',
            'etag': '"abc123"'
        }
        
        self.assertEqual(info, expected_info)
        # Verify the request was made with HEAD method and correct URL
        mock_request.assert_called_once()
        call_args = mock_request.call_args
        self.assertEqual(call_args[0][0], 'HEAD')  # HTTP method
        self.assertEqual(call_args[0][1], 'http://test.com/media.jpg')  # URL
    
    def test_get_media_info_not_authenticated(self):
        """Test get_media_info when not authenticated"""
        extractor = WhatsAppExtractor(self.business_config)
        info = extractor.get_media_info('http://test.com/media.jpg')
        
        self.assertIsNone(info)
    
    @patch('os.path.exists')
    @patch('os.path.getsize')
    def test_validate_media_file_success(self, mock_getsize, mock_exists):
        """Test successful media file validation"""
        mock_exists.return_value = True
        mock_getsize.return_value = 12345
        
        extractor = WhatsAppExtractor(self.business_config)
        
        # Test without expected size
        result = extractor.validate_media_file('/tmp/test.jpg')
        self.assertTrue(result)
        
        # Test with matching expected size
        result = extractor.validate_media_file('/tmp/test.jpg', 12345)
        self.assertTrue(result)
    
    @patch('os.path.exists')
    def test_validate_media_file_not_exists(self, mock_exists):
        """Test media file validation when file doesn't exist"""
        mock_exists.return_value = False
        
        extractor = WhatsAppExtractor(self.business_config)
        result = extractor.validate_media_file('/tmp/nonexistent.jpg')
        
        self.assertFalse(result)
    
    @patch('os.path.exists')
    @patch('os.path.getsize')
    def test_validate_media_file_empty(self, mock_getsize, mock_exists):
        """Test media file validation with empty file"""
        mock_exists.return_value = True
        mock_getsize.return_value = 0
        
        extractor = WhatsAppExtractor(self.business_config)
        result = extractor.validate_media_file('/tmp/empty.jpg')
        
        self.assertFalse(result)
    
    @patch('os.path.exists')
    @patch('os.path.getsize')
    def test_validate_media_file_size_mismatch(self, mock_getsize, mock_exists):
        """Test media file validation with size mismatch"""
        mock_exists.return_value = True
        mock_getsize.return_value = 12345
        
        extractor = WhatsAppExtractor(self.business_config)
        result = extractor.validate_media_file('/tmp/test.jpg', 54321)  # Different expected size
        
        self.assertFalse(result)
    
    @patch('os.path.exists')
    @patch('os.listdir')
    @patch('os.path.isfile')
    @patch('os.path.getsize')
    @patch('os.remove')
    def test_cleanup_failed_downloads(self, mock_remove, mock_getsize, mock_isfile, mock_listdir, mock_exists):
        """Test cleanup of failed downloads"""
        mock_exists.return_value = True
        mock_listdir.return_value = ['small_file.jpg', 'good_file.jpg', 'empty_file.pdf']
        mock_isfile.return_value = True
        
        # Mock file sizes: small, good, empty
        mock_getsize.side_effect = [50, 5000, 0]
        
        extractor = WhatsAppExtractor(self.business_config)
        cleaned_count = extractor.cleanup_failed_downloads('/tmp/test')
        
        # Should clean up 2 files (small and empty)
        self.assertEqual(cleaned_count, 2)
        self.assertEqual(mock_remove.call_count, 2)
    
    @patch('os.path.exists')
    def test_cleanup_failed_downloads_no_dir(self, mock_exists):
        """Test cleanup when directory doesn't exist"""
        mock_exists.return_value = False
        
        extractor = WhatsAppExtractor(self.business_config)
        cleaned_count = extractor.cleanup_failed_downloads('/tmp/nonexistent')
        
        self.assertEqual(cleaned_count, 0)


if __name__ == '__main__':
    unittest.main()