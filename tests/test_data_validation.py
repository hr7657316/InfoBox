"""
Unit tests for data validation and processing
"""

import unittest
from unittest.mock import Mock, patch
from datetime import datetime, timedelta
import json
import re
from typing import Dict, List, Any

# Mock data validation classes
class DataValidator:
    """Data validator for pipeline data"""
    
    def __init__(self):
        self.validation_rules = {
            'whatsapp_message': {
                'required_fields': ['id', 'timestamp', 'sender_phone', 'message_content', 'message_type'],
                'field_types': {
                    'id': str,
                    'timestamp': datetime,
                    'sender_phone': str,
                    'message_content': str,
                    'message_type': str
                },
                'field_patterns': {
                    'sender_phone': r'^\+?[\d\s\-\(\)]+$',
                    'message_type': r'^(text|image|audio|video|document)$'
                }
            },
            'email': {
                'required_fields': ['id', 'timestamp', 'sender_email', 'recipient_emails', 'subject', 'body_text'],
                'field_types': {
                    'id': str,
                    'timestamp': datetime,
                    'sender_email': str,
                    'recipient_emails': list,
                    'subject': str,
                    'body_text': str
                },
                'field_patterns': {
                    'sender_email': r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
                }
            }
        }
    
    def validate_data(self, data: Dict[str, Any], data_type: str) -> Dict[str, Any]:
        """Validate data against rules"""
        if data_type not in self.validation_rules:
            return {'valid': False, 'errors': [f'Unknown data type: {data_type}']}
        
        rules = self.validation_rules[data_type]
        errors = []
        
        # Check required fields
        for field in rules['required_fields']:
            if field not in data:
                errors.append(f'Missing required field: {field}')
        
        # Check field types
        for field, expected_type in rules['field_types'].items():
            if field in data and not isinstance(data[field], expected_type):
                errors.append(f'Field {field} should be {expected_type.__name__}, got {type(data[field]).__name__}')
        
        # Check field patterns
        for field, pattern in rules.get('field_patterns', {}).items():
            if field in data and isinstance(data[field], str):
                if not re.match(pattern, data[field]):
                    errors.append(f'Field {field} does not match required pattern')
        
        return {
            'valid': len(errors) == 0,
            'errors': errors,
            'data': data
        }
    
    def validate_batch(self, data_list: List[Dict[str, Any]], data_type: str) -> Dict[str, Any]:
        """Validate a batch of data"""
        results = []
        total_errors = 0
        
        for i, data in enumerate(data_list):
            result = self.validate_data(data, data_type)
            result['index'] = i
            results.append(result)
            if not result['valid']:
                total_errors += len(result['errors'])
        
        valid_count = sum(1 for r in results if r['valid'])
        
        return {
            'total_items': len(data_list),
            'valid_items': valid_count,
            'invalid_items': len(data_list) - valid_count,
            'total_errors': total_errors,
            'results': results,
            'success_rate': valid_count / len(data_list) if data_list else 0
        }


class DataSanitizer:
    """Data sanitizer for cleaning and normalizing data"""
    
    def sanitize_phone_number(self, phone: str) -> str:
        """Sanitize phone number"""
        if not phone:
            return phone
        
        # Remove non-digit characters except +
        cleaned = re.sub(r'[^\d+]', '', phone)
        
        # Ensure it starts with +
        if not cleaned.startswith('+'):
            cleaned = '+' + cleaned
        
        return cleaned
    
    def sanitize_email(self, email: str) -> str:
        """Sanitize email address"""
        if not email:
            return email
        
        return email.lower().strip()
    
    def sanitize_text_content(self, text: str) -> str:
        """Sanitize text content"""
        if not text:
            return text
        
        # Remove excessive whitespace
        text = re.sub(r'\s+', ' ', text)
        
        # Remove control characters
        text = re.sub(r'[\x00-\x1f\x7f-\x9f]', '', text)
        
        return text.strip()
    
    def sanitize_whatsapp_message(self, message: Dict[str, Any]) -> Dict[str, Any]:
        """Sanitize WhatsApp message data"""
        sanitized = message.copy()
        
        if 'sender_phone' in sanitized:
            sanitized['sender_phone'] = self.sanitize_phone_number(sanitized['sender_phone'])
        
        if 'message_content' in sanitized:
            sanitized['message_content'] = self.sanitize_text_content(sanitized['message_content'])
        
        return sanitized
    
    def sanitize_email_message(self, email: Dict[str, Any]) -> Dict[str, Any]:
        """Sanitize email message data"""
        sanitized = email.copy()
        
        if 'sender_email' in sanitized:
            sanitized['sender_email'] = self.sanitize_email(sanitized['sender_email'])
        
        if 'recipient_emails' in sanitized and isinstance(sanitized['recipient_emails'], list):
            sanitized['recipient_emails'] = [self.sanitize_email(e) for e in sanitized['recipient_emails']]
        
        if 'subject' in sanitized:
            sanitized['subject'] = self.sanitize_text_content(sanitized['subject'])
        
        if 'body_text' in sanitized:
            sanitized['body_text'] = self.sanitize_text_content(sanitized['body_text'])
        
        return sanitized


class TestDataValidator(unittest.TestCase):
    """Test cases for data validation"""
    
    def setUp(self):
        self.validator = DataValidator()
    
    def test_validate_whatsapp_message_valid(self):
        """Test validation of valid WhatsApp message"""
        message = {
            'id': 'msg_123',
            'timestamp': datetime.now(),
            'sender_phone': '+1234567890',
            'message_content': 'Hello, world!',
            'message_type': 'text'
        }
        
        result = self.validator.validate_data(message, 'whatsapp_message')
        
        self.assertTrue(result['valid'])
        self.assertEqual(len(result['errors']), 0)
        self.assertEqual(result['data'], message)
    
    def test_validate_whatsapp_message_missing_fields(self):
        """Test validation of WhatsApp message with missing fields"""
        message = {
            'id': 'msg_123',
            'timestamp': datetime.now(),
            # Missing sender_phone, message_content, message_type
        }
        
        result = self.validator.validate_data(message, 'whatsapp_message')
        
        self.assertFalse(result['valid'])
        self.assertGreater(len(result['errors']), 0)
        self.assertIn('Missing required field: sender_phone', result['errors'])
        self.assertIn('Missing required field: message_content', result['errors'])
        self.assertIn('Missing required field: message_type', result['errors'])
    
    def test_validate_whatsapp_message_wrong_types(self):
        """Test validation of WhatsApp message with wrong field types"""
        message = {
            'id': 123,  # Should be string
            'timestamp': 'not_a_datetime',  # Should be datetime
            'sender_phone': '+1234567890',
            'message_content': 'Hello, world!',
            'message_type': 'text'
        }
        
        result = self.validator.validate_data(message, 'whatsapp_message')
        
        self.assertFalse(result['valid'])
        self.assertIn('Field id should be str, got int', result['errors'])
        self.assertIn('Field timestamp should be datetime, got str', result['errors'])
    
    def test_validate_whatsapp_message_invalid_patterns(self):
        """Test validation of WhatsApp message with invalid patterns"""
        message = {
            'id': 'msg_123',
            'timestamp': datetime.now(),
            'sender_phone': 'invalid_phone',  # Invalid phone pattern
            'message_content': 'Hello, world!',
            'message_type': 'invalid_type'  # Invalid message type
        }
        
        result = self.validator.validate_data(message, 'whatsapp_message')
        
        self.assertFalse(result['valid'])
        self.assertIn('Field sender_phone does not match required pattern', result['errors'])
        self.assertIn('Field message_type does not match required pattern', result['errors'])
    
    def test_validate_email_valid(self):
        """Test validation of valid email"""
        email = {
            'id': 'email_123',
            'timestamp': datetime.now(),
            'sender_email': 'sender@example.com',
            'recipient_emails': ['recipient@example.com'],
            'subject': 'Test Subject',
            'body_text': 'Test body content'
        }
        
        result = self.validator.validate_data(email, 'email')
        
        self.assertTrue(result['valid'])
        self.assertEqual(len(result['errors']), 0)
    
    def test_validate_email_invalid_email_pattern(self):
        """Test validation of email with invalid email pattern"""
        email = {
            'id': 'email_123',
            'timestamp': datetime.now(),
            'sender_email': 'invalid_email',  # Invalid email pattern
            'recipient_emails': ['recipient@example.com'],
            'subject': 'Test Subject',
            'body_text': 'Test body content'
        }
        
        result = self.validator.validate_data(email, 'email')
        
        self.assertFalse(result['valid'])
        self.assertIn('Field sender_email does not match required pattern', result['errors'])
    
    def test_validate_unknown_data_type(self):
        """Test validation of unknown data type"""
        data = {'test': 'data'}
        
        result = self.validator.validate_data(data, 'unknown_type')
        
        self.assertFalse(result['valid'])
        self.assertIn('Unknown data type: unknown_type', result['errors'])
    
    def test_validate_batch_all_valid(self):
        """Test batch validation with all valid items"""
        messages = [
            {
                'id': 'msg_1',
                'timestamp': datetime.now(),
                'sender_phone': '+1234567890',
                'message_content': 'Message 1',
                'message_type': 'text'
            },
            {
                'id': 'msg_2',
                'timestamp': datetime.now(),
                'sender_phone': '+0987654321',
                'message_content': 'Message 2',
                'message_type': 'image'
            }
        ]
        
        result = self.validator.validate_batch(messages, 'whatsapp_message')
        
        self.assertEqual(result['total_items'], 2)
        self.assertEqual(result['valid_items'], 2)
        self.assertEqual(result['invalid_items'], 0)
        self.assertEqual(result['total_errors'], 0)
        self.assertEqual(result['success_rate'], 1.0)
    
    def test_validate_batch_mixed_validity(self):
        """Test batch validation with mixed valid/invalid items"""
        messages = [
            {
                'id': 'msg_1',
                'timestamp': datetime.now(),
                'sender_phone': '+1234567890',
                'message_content': 'Message 1',
                'message_type': 'text'
            },
            {
                'id': 'msg_2',
                # Missing required fields
                'message_content': 'Message 2'
            },
            {
                'id': 'msg_3',
                'timestamp': datetime.now(),
                'sender_phone': 'invalid_phone',  # Invalid pattern
                'message_content': 'Message 3',
                'message_type': 'text'
            }
        ]
        
        result = self.validator.validate_batch(messages, 'whatsapp_message')
        
        self.assertEqual(result['total_items'], 3)
        self.assertEqual(result['valid_items'], 1)
        self.assertEqual(result['invalid_items'], 2)
        self.assertGreater(result['total_errors'], 0)
        self.assertAlmostEqual(result['success_rate'], 1/3, places=2)
    
    def test_validate_batch_empty_list(self):
        """Test batch validation with empty list"""
        result = self.validator.validate_batch([], 'whatsapp_message')
        
        self.assertEqual(result['total_items'], 0)
        self.assertEqual(result['valid_items'], 0)
        self.assertEqual(result['invalid_items'], 0)
        self.assertEqual(result['total_errors'], 0)
        self.assertEqual(result['success_rate'], 0)


class TestDataSanitizer(unittest.TestCase):
    """Test cases for data sanitization"""
    
    def setUp(self):
        self.sanitizer = DataSanitizer()
    
    def test_sanitize_phone_number_with_formatting(self):
        """Test phone number sanitization with formatting"""
        test_cases = [
            ('+1 (234) 567-8900', '+12345678900'),
            ('1-234-567-8900', '+12345678900'),
            ('(234) 567-8900', '+2345678900'),
            ('+44 20 7946 0958', '+442079460958')
        ]
        
        for input_phone, expected in test_cases:
            result = self.sanitizer.sanitize_phone_number(input_phone)
            self.assertEqual(result, expected)
    
    def test_sanitize_phone_number_edge_cases(self):
        """Test phone number sanitization edge cases"""
        # Empty or None
        self.assertEqual(self.sanitizer.sanitize_phone_number(''), '')
        self.assertEqual(self.sanitizer.sanitize_phone_number(None), None)
        
        # Already clean
        self.assertEqual(self.sanitizer.sanitize_phone_number('+1234567890'), '+1234567890')
        
        # No plus sign
        self.assertEqual(self.sanitizer.sanitize_phone_number('1234567890'), '+1234567890')
    
    def test_sanitize_email_normalization(self):
        """Test email sanitization and normalization"""
        test_cases = [
            ('User@Example.COM', 'user@example.com'),
            ('  test@domain.org  ', 'test@domain.org'),
            ('Test.User+tag@Gmail.Com', 'test.user+tag@gmail.com')
        ]
        
        for input_email, expected in test_cases:
            result = self.sanitizer.sanitize_email(input_email)
            self.assertEqual(result, expected)
    
    def test_sanitize_email_edge_cases(self):
        """Test email sanitization edge cases"""
        # Empty or None
        self.assertEqual(self.sanitizer.sanitize_email(''), '')
        self.assertEqual(self.sanitizer.sanitize_email(None), None)
        
        # Already clean
        self.assertEqual(self.sanitizer.sanitize_email('test@example.com'), 'test@example.com')
    
    def test_sanitize_text_content_whitespace(self):
        """Test text content sanitization for whitespace"""
        test_cases = [
            ('  Multiple   spaces  ', 'Multiple spaces'),
            ('Line\nbreaks\nhere', 'Line breaks here'),
            ('Tab\tcharacters\there', 'Tab characters here'),
            ('Mixed\n\t  whitespace  \n', 'Mixed whitespace')
        ]
        
        for input_text, expected in test_cases:
            result = self.sanitizer.sanitize_text_content(input_text)
            self.assertEqual(result, expected)
    
    def test_sanitize_text_content_control_characters(self):
        """Test text content sanitization for control characters"""
        # Text with control characters
        text_with_control = 'Hello\x00\x1f\x7f\x9fWorld'
        result = self.sanitizer.sanitize_text_content(text_with_control)
        self.assertEqual(result, 'Hello World')
    
    def test_sanitize_text_content_edge_cases(self):
        """Test text content sanitization edge cases"""
        # Empty or None
        self.assertEqual(self.sanitizer.sanitize_text_content(''), '')
        self.assertEqual(self.sanitizer.sanitize_text_content(None), None)
        
        # Already clean
        self.assertEqual(self.sanitizer.sanitize_text_content('Clean text'), 'Clean text')
    
    def test_sanitize_whatsapp_message(self):
        """Test WhatsApp message sanitization"""
        message = {
            'id': 'msg_123',
            'timestamp': datetime.now(),
            'sender_phone': '+1 (234) 567-8900',
            'message_content': '  Hello,\n\tworld!  ',
            'message_type': 'text'
        }
        
        result = self.sanitizer.sanitize_whatsapp_message(message)
        
        self.assertEqual(result['sender_phone'], '+12345678900')
        self.assertEqual(result['message_content'], 'Hello, world!')
        # Other fields should remain unchanged
        self.assertEqual(result['id'], message['id'])
        self.assertEqual(result['timestamp'], message['timestamp'])
        self.assertEqual(result['message_type'], message['message_type'])
    
    def test_sanitize_email_message(self):
        """Test email message sanitization"""
        email = {
            'id': 'email_123',
            'timestamp': datetime.now(),
            'sender_email': '  Sender@Example.COM  ',
            'recipient_emails': ['Recipient1@Domain.org', '  RECIPIENT2@test.com  '],
            'subject': '  Important\n\tSubject  ',
            'body_text': 'Email\n\n\tbody content\n  with   spaces  '
        }
        
        result = self.sanitizer.sanitize_email_message(email)
        
        self.assertEqual(result['sender_email'], 'sender@example.com')
        self.assertEqual(result['recipient_emails'], ['recipient1@domain.org', 'recipient2@test.com'])
        self.assertEqual(result['subject'], 'Important Subject')
        self.assertEqual(result['body_text'], 'Email body content with spaces')
    
    def test_sanitize_preserves_original_data(self):
        """Test that sanitization doesn't modify original data"""
        original_message = {
            'id': 'msg_123',
            'sender_phone': '+1 (234) 567-8900',
            'message_content': '  Hello,\n\tworld!  '
        }
        
        original_copy = original_message.copy()
        result = self.sanitizer.sanitize_whatsapp_message(original_message)
        
        # Original should be unchanged
        self.assertEqual(original_message, original_copy)
        
        # Result should be different
        self.assertNotEqual(result['sender_phone'], original_message['sender_phone'])
        self.assertNotEqual(result['message_content'], original_message['message_content'])


class TestDataProcessingIntegration(unittest.TestCase):
    """Test cases for integrated data processing workflows"""
    
    def setUp(self):
        self.validator = DataValidator()
        self.sanitizer = DataSanitizer()
    
    def test_sanitize_then_validate_workflow(self):
        """Test sanitize-then-validate workflow"""
        raw_message = {
            'id': 'msg_123',
            'timestamp': datetime.now(),
            'sender_phone': '+1 (234) 567-8900',  # Needs sanitization
            'message_content': '  Hello,\n\tworld!  ',  # Needs sanitization
            'message_type': 'text'
        }
        
        # First sanitize
        sanitized = self.sanitizer.sanitize_whatsapp_message(raw_message)
        
        # Then validate
        validation_result = self.validator.validate_data(sanitized, 'whatsapp_message')
        
        self.assertTrue(validation_result['valid'])
        self.assertEqual(len(validation_result['errors']), 0)
        self.assertEqual(validation_result['data']['sender_phone'], '+12345678900')
        self.assertEqual(validation_result['data']['message_content'], 'Hello, world!')
    
    def test_batch_sanitize_and_validate(self):
        """Test batch sanitization and validation"""
        raw_messages = [
            {
                'id': 'msg_1',
                'timestamp': datetime.now(),
                'sender_phone': '+1 (234) 567-8900',
                'message_content': '  Message 1  ',
                'message_type': 'text'
            },
            {
                'id': 'msg_2',
                'timestamp': datetime.now(),
                'sender_phone': '987-654-3210',  # Missing +
                'message_content': 'Message\n\t2',
                'message_type': 'image'
            },
            {
                'id': 'msg_3',
                # Missing required fields - should fail validation even after sanitization
                'message_content': 'Message 3'
            }
        ]
        
        # Sanitize all messages
        sanitized_messages = [
            self.sanitizer.sanitize_whatsapp_message(msg) for msg in raw_messages
        ]
        
        # Validate batch
        validation_result = self.validator.validate_batch(sanitized_messages, 'whatsapp_message')
        
        self.assertEqual(validation_result['total_items'], 3)
        self.assertEqual(validation_result['valid_items'], 2)  # First two should be valid after sanitization
        self.assertEqual(validation_result['invalid_items'], 1)  # Third should still be invalid
        
        # Check that sanitization worked for valid items
        valid_results = [r for r in validation_result['results'] if r['valid']]
        self.assertEqual(len(valid_results), 2)
        
        # Check sanitized phone numbers
        self.assertEqual(valid_results[0]['data']['sender_phone'], '+12345678900')
        self.assertEqual(valid_results[1]['data']['sender_phone'], '+9876543210')
    
    def test_data_quality_metrics(self):
        """Test data quality metrics calculation"""
        raw_data = [
            # Valid data
            {
                'id': 'msg_1',
                'timestamp': datetime.now(),
                'sender_phone': '+1234567890',
                'message_content': 'Clean message',
                'message_type': 'text'
            },
            # Data needing sanitization
            {
                'id': 'msg_2',
                'timestamp': datetime.now(),
                'sender_phone': '+1 (234) 567-8900',
                'message_content': '  Messy   message  ',
                'message_type': 'text'
            },
            # Invalid data
            {
                'id': 'msg_3',
                'timestamp': datetime.now(),
                'sender_phone': 'invalid_phone',
                'message_content': 'Message with invalid phone',
                'message_type': 'invalid_type'
            }
        ]
        
        # Process data
        sanitized_data = [self.sanitizer.sanitize_whatsapp_message(msg) for msg in raw_data]
        validation_result = self.validator.validate_batch(sanitized_data, 'whatsapp_message')
        
        # Calculate quality metrics
        total_items = len(raw_data)
        items_needing_sanitization = sum(1 for i, msg in enumerate(raw_data) 
                                       if sanitized_data[i] != msg)
        valid_after_processing = validation_result['valid_items']
        
        quality_metrics = {
            'total_items': total_items,
            'items_needing_sanitization': items_needing_sanitization,
            'sanitization_rate': items_needing_sanitization / total_items,
            'final_validity_rate': valid_after_processing / total_items,
            'data_quality_score': (valid_after_processing / total_items) * 100
        }
        
        self.assertEqual(quality_metrics['total_items'], 3)
        self.assertEqual(quality_metrics['items_needing_sanitization'], 2)  # msg_2 and msg_3 needed sanitization
        self.assertAlmostEqual(quality_metrics['sanitization_rate'], 1/3, places=2)
        self.assertAlmostEqual(quality_metrics['final_validity_rate'], 2/3, places=2)  # msg_1 and msg_2 valid after processing
        self.assertAlmostEqual(quality_metrics['data_quality_score'], 66.67, places=1)


if __name__ == '__main__':
    unittest.main()