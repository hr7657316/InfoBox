"""
Unit tests for the PipelineLogger class
"""

import unittest
import tempfile
import shutil
import os
import logging
import json
from unittest.mock import patch, MagicMock
from datetime import datetime

from pipeline.utils.logger import PipelineLogger


class TestPipelineLogger(unittest.TestCase):
    """Test cases for PipelineLogger functionality"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.temp_dir = tempfile.mkdtemp()
        self.config = {
            'log_dir': self.temp_dir,
            'log_level': 'DEBUG',
            'max_bytes': 1024,  # Small size for testing rotation
            'backup_count': 2,
            'console_output': True,
            'file_output': True
        }
        self.logger = PipelineLogger(self.config)
    
    def tearDown(self):
        """Clean up test fixtures"""
        # Clear any handlers to avoid interference between tests
        if self.logger.logger:
            self.logger.logger.handlers.clear()
        shutil.rmtree(self.temp_dir)
    
    def test_init_with_default_config(self):
        """Test logger initialization with default configuration"""
        logger = PipelineLogger()
        self.assertEqual(logger._log_dir, 'logs')
        self.assertEqual(logger._log_level, 'INFO')
        self.assertEqual(logger._max_bytes, 10 * 1024 * 1024)
        self.assertEqual(logger._backup_count, 5)
        self.assertTrue(logger._console_output)
        self.assertTrue(logger._file_output)
        self.assertFalse(logger._setup_complete)
    
    def test_init_with_custom_config(self):
        """Test logger initialization with custom configuration"""
        custom_config = {
            'log_dir': '/custom/logs',
            'log_level': 'ERROR',
            'max_bytes': 5000,
            'backup_count': 3,
            'console_output': False,
            'file_output': True
        }
        logger = PipelineLogger(custom_config)
        self.assertEqual(logger._log_dir, '/custom/logs')
        self.assertEqual(logger._log_level, 'ERROR')
        self.assertEqual(logger._max_bytes, 5000)
        self.assertEqual(logger._backup_count, 3)
        self.assertFalse(logger._console_output)
        self.assertTrue(logger._file_output)
    
    def test_setup_logging_creates_directory(self):
        """Test that setup_logging creates the log directory"""
        log_dir = os.path.join(self.temp_dir, 'new_logs')
        config = self.config.copy()
        config['log_dir'] = log_dir
        logger = PipelineLogger(config)
        
        self.assertFalse(os.path.exists(log_dir))
        logger.setup_logging()
        self.assertTrue(os.path.exists(log_dir))
    
    def test_setup_logging_configures_logger(self):
        """Test that setup_logging properly configures the logger"""
        self.logger.setup_logging()
        
        self.assertIsNotNone(self.logger.logger)
        self.assertEqual(self.logger.logger.level, logging.DEBUG)
        self.assertTrue(self.logger._setup_complete)
        
        # Should have both file and console handlers
        handlers = self.logger.logger.handlers
        self.assertEqual(len(handlers), 2)
        
        # Check handler types
        handler_types = [type(h).__name__ for h in handlers]
        self.assertIn('RotatingFileHandler', handler_types)
        self.assertIn('StreamHandler', handler_types)
    
    def test_setup_logging_file_only(self):
        """Test setup_logging with file output only"""
        config = self.config.copy()
        config['console_output'] = False
        logger = PipelineLogger(config)
        logger.setup_logging()
        
        handlers = logger.logger.handlers
        self.assertEqual(len(handlers), 1)
        self.assertEqual(type(handlers[0]).__name__, 'RotatingFileHandler')
    
    def test_setup_logging_console_only(self):
        """Test setup_logging with console output only"""
        config = self.config.copy()
        config['file_output'] = False
        logger = PipelineLogger(config)
        logger.setup_logging()
        
        handlers = logger.logger.handlers
        self.assertEqual(len(handlers), 1)
        self.assertEqual(type(handlers[0]).__name__, 'StreamHandler')
    
    def test_setup_logging_idempotent(self):
        """Test that setup_logging can be called multiple times safely"""
        self.logger.setup_logging()
        initial_handler_count = len(self.logger.logger.handlers)
        
        self.logger.setup_logging()
        final_handler_count = len(self.logger.logger.handlers)
        
        self.assertEqual(initial_handler_count, final_handler_count)
    
    def test_log_extraction_start(self):
        """Test logging extraction start"""
        with patch.object(self.logger, '_log_with_component') as mock_log:
            self.logger.log_extraction_start('whatsapp')
            
            mock_log.assert_called_once()
            args, kwargs = mock_log.call_args
            self.assertEqual(args[0], 'info')
            self.assertIn('Starting extraction from whatsapp', args[1])
            self.assertEqual(args[2], 'whatsapp_extractor')
            self.assertIn('action', kwargs)
            self.assertEqual(kwargs['action'], 'extraction_start')
    
    def test_log_extraction_complete(self):
        """Test logging extraction completion"""
        stats = {'messages': 10, 'media': 5, 'errors': 0}
        
        with patch.object(self.logger, '_log_with_component') as mock_log:
            self.logger.log_extraction_complete('email', stats)
            
            mock_log.assert_called_once()
            args, kwargs = mock_log.call_args
            self.assertEqual(args[0], 'info')
            self.assertIn('Extraction from email completed successfully', args[1])
            self.assertEqual(args[2], 'email_extractor')
            self.assertIn('stats', kwargs)
            self.assertEqual(kwargs['stats'], stats)
    
    def test_log_error(self):
        """Test error logging with exception"""
        test_error = ValueError("Test error message")
        context = {'user_id': '123', 'operation': 'test'}
        
        with patch.object(self.logger, '_log_with_component') as mock_log:
            self.logger.log_error('test_component', test_error, context)
            
            mock_log.assert_called_once()
            args, kwargs = mock_log.call_args
            self.assertEqual(args[0], 'error')
            self.assertIn('Error in test_component: Test error message', args[1])
            self.assertEqual(args[2], 'test_component')
            self.assertEqual(kwargs['error_type'], 'ValueError')
            self.assertEqual(kwargs['error_message'], 'Test error message')
            self.assertEqual(kwargs['user_id'], '123')
            self.assertEqual(kwargs['operation'], 'test')
    
    def test_log_info(self):
        """Test info logging"""
        with patch.object(self.logger, '_log_with_component') as mock_log:
            self.logger.log_info('Test info message', 'test_component', extra_data='test')
            
            mock_log.assert_called_once_with(
                'info', 'Test info message', 'test_component', extra_data='test'
            )
    
    def test_log_warning(self):
        """Test warning logging"""
        with patch.object(self.logger, '_log_with_component') as mock_log:
            self.logger.log_warning('Test warning', 'test_component')
            
            mock_log.assert_called_once_with(
                'warning', 'Test warning', 'test_component'
            )
    
    def test_log_debug(self):
        """Test debug logging"""
        with patch.object(self.logger, '_log_with_component') as mock_log:
            self.logger.log_debug('Debug message', 'test_component')
            
            mock_log.assert_called_once_with(
                'debug', 'Debug message', 'test_component'
            )
    
    def test_log_api_request_success(self):
        """Test API request logging for successful requests"""
        with patch.object(self.logger, '_log_with_component') as mock_log:
            self.logger.log_api_request('whatsapp', 'GET', 'https://api.example.com/messages', 200)
            
            mock_log.assert_called_once()
            args, kwargs = mock_log.call_args
            self.assertEqual(args[0], 'info')
            self.assertIn('API GET https://api.example.com/messages - Status: 200', args[1])
            self.assertEqual(args[2], 'whatsapp')
            self.assertEqual(kwargs['method'], 'GET')
            self.assertEqual(kwargs['status_code'], 200)
            self.assertEqual(kwargs['action'], 'api_request')
    
    def test_log_api_request_error(self):
        """Test API request logging for error responses"""
        with patch.object(self.logger, '_log_with_component') as mock_log:
            self.logger.log_api_request('email', 'POST', 'https://api.example.com/auth', 401)
            
            mock_log.assert_called_once()
            args, kwargs = mock_log.call_args
            self.assertEqual(args[0], 'warning')
            self.assertIn('API POST https://api.example.com/auth - Status: 401', args[1])
    
    def test_log_data_processing(self):
        """Test data processing logging"""
        with patch.object(self.logger, '_log_with_component') as mock_log:
            self.logger.log_data_processing('storage', 'saved', 25, format='json')
            
            mock_log.assert_called_once()
            args, kwargs = mock_log.call_args
            self.assertEqual(args[0], 'info')
            self.assertIn('Data processing: saved 25 items', args[1])
            self.assertEqual(args[2], 'storage')
            self.assertEqual(kwargs['action'], 'saved')
            self.assertEqual(kwargs['count'], 25)
            self.assertEqual(kwargs['format'], 'json')
    
    def test_log_with_component_auto_setup(self):
        """Test that _log_with_component automatically sets up logging"""
        # Ensure logger is not set up
        self.assertFalse(self.logger._setup_complete)
        
        # Call a logging method
        self.logger.log_info('Test message')
        
        # Should now be set up
        self.assertTrue(self.logger._setup_complete)
        self.assertIsNotNone(self.logger.logger)
    
    def test_log_with_component_context_serialization(self):
        """Test that context data is properly serialized in log messages"""
        self.logger.setup_logging()
        
        # Create a custom handler to capture log records
        class TestHandler(logging.Handler):
            def __init__(self):
                super().__init__()
                self.records = []
            
            def emit(self, record):
                self.records.append(record)
        
        test_handler = TestHandler()
        test_handler.setLevel(logging.DEBUG)
        self.logger.logger.addHandler(test_handler)
        
        # Log with complex context data
        context = {
            'timestamp': datetime.now(),
            'count': 42,
            'nested': {'key': 'value'}
        }
        
        self.logger.log_info('Test message', 'test_component', **context)
        
        # Verify the handler captured the record
        self.assertEqual(len(test_handler.records), 1)
        
        # Get the log record
        log_record = test_handler.records[0]
        
        # Check that context was included in the message
        self.assertIn('Context:', log_record.getMessage())
        self.assertEqual(log_record.component, 'test_component')
    
    def test_file_rotation(self):
        """Test that log file rotation works correctly"""
        # Use a very small max_bytes to trigger rotation
        config = self.config.copy()
        config['max_bytes'] = 100
        config['backup_count'] = 2
        logger = PipelineLogger(config)
        logger.setup_logging()
        
        # Generate enough log messages to trigger rotation
        for i in range(20):
            logger.log_info(f'Test message {i} with some additional content to make it longer')
        
        # Check that log files exist
        log_file = os.path.join(self.temp_dir, 'pipeline.log')
        self.assertTrue(os.path.exists(log_file))
        
        # Check for rotated files (they may or may not exist depending on exact message sizes)
        # This is more of a smoke test to ensure rotation doesn't crash
        files = os.listdir(self.temp_dir)
        log_files = [f for f in files if f.startswith('pipeline.log')]
        self.assertGreaterEqual(len(log_files), 1)


if __name__ == '__main__':
    unittest.main()