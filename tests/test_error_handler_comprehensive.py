"""
Comprehensive unit tests for the error handling system
"""

import unittest
from unittest.mock import Mock, patch
import time
import logging
from datetime import datetime, timedelta
import requests
import imaplib
import socket
import ssl

from pipeline.utils.error_handler import (
    ErrorHandler, ErrorCategory, ErrorSeverity, ErrorInfo, RetryConfig,
    PipelineError, AuthenticationError, NetworkError, RateLimitError,
    DataProcessingError, StorageError, ConfigurationError, ValidationError,
    BatchErrorHandler, with_error_handling, graceful_degradation
)


class TestErrorInfo(unittest.TestCase):
    """Test cases for ErrorInfo dataclass"""
    
    def test_init_basic(self):
        """Test basic ErrorInfo initialization"""
        error_info = ErrorInfo(
            category=ErrorCategory.NETWORK,
            severity=ErrorSeverity.MEDIUM,
            message="Network connection failed"
        )
        
        self.assertEqual(error_info.category, ErrorCategory.NETWORK)
        self.assertEqual(error_info.severity, ErrorSeverity.MEDIUM)
        self.assertEqual(error_info.message, "Network connection failed")
        self.assertIsNone(error_info.original_exception)
        self.assertEqual(error_info.context, {})
        self.assertIsInstance(error_info.timestamp, datetime)
        self.assertEqual(error_info.component, "unknown")
        self.assertEqual(error_info.retry_count, 0)
        self.assertEqual(error_info.max_retries, 3)
    
    def test_init_with_all_fields(self):
        """Test ErrorInfo initialization with all fields"""
        exception = ValueError("Test error")
        context = {"user_id": "123", "operation": "test_op"}
        timestamp = datetime.now()
        
        error_info = ErrorInfo(
            category=ErrorCategory.DATA_PROCESSING,
            severity=ErrorSeverity.HIGH,
            message="Data validation failed",
            original_exception=exception,
            context=context,
            timestamp=timestamp,
            component="data_processor",
            retry_count=2,
            max_retries=5
        )
        
        self.assertEqual(error_info.category, ErrorCategory.DATA_PROCESSING)
        self.assertEqual(error_info.severity, ErrorSeverity.HIGH)
        self.assertEqual(error_info.original_exception, exception)
        self.assertEqual(error_info.context, context)
        self.assertEqual(error_info.timestamp, timestamp)
        self.assertEqual(error_info.component, "data_processor")
        self.assertEqual(error_info.retry_count, 2)
        self.assertEqual(error_info.max_retries, 5)
    
    def test_to_dict(self):
        """Test ErrorInfo to_dict conversion"""
        exception = ValueError("Test error")
        context = {"user_id": "123"}
        
        error_info = ErrorInfo(
            category=ErrorCategory.AUTHENTICATION,
            severity=ErrorSeverity.CRITICAL,
            message="Auth failed",
            original_exception=exception,
            context=context,
            component="auth_module"
        )
        
        result_dict = error_info.to_dict()
        
        self.assertEqual(result_dict['category'], 'authentication')
        self.assertEqual(result_dict['severity'], 'critical')
        self.assertEqual(result_dict['message'], 'Auth failed')
        self.assertEqual(result_dict['exception_type'], 'ValueError')
        self.assertEqual(result_dict['exception_message'], 'Test error')
        self.assertEqual(result_dict['context'], context)
        self.assertEqual(result_dict['component'], 'auth_module')
        self.assertIn('timestamp', result_dict)


class TestRetryConfig(unittest.TestCase):
    """Test cases for RetryConfig"""
    
    def test_init_defaults(self):
        """Test RetryConfig with default values"""
        config = RetryConfig()
        
        self.assertEqual(config.max_retries, 3)
        self.assertEqual(config.base_delay, 1.0)
        self.assertEqual(config.max_delay, 60.0)
        self.assertEqual(config.exponential_base, 2.0)
        self.assertTrue(config.jitter)
    
    def test_init_custom(self):
        """Test RetryConfig with custom values"""
        config = RetryConfig(
            max_retries=5,
            base_delay=2.0,
            max_delay=120.0,
            exponential_base=1.5,
            jitter=False
        )
        
        self.assertEqual(config.max_retries, 5)
        self.assertEqual(config.base_delay, 2.0)
        self.assertEqual(config.max_delay, 120.0)
        self.assertEqual(config.exponential_base, 1.5)
        self.assertFalse(config.jitter)
    
    def test_get_delay_no_jitter(self):
        """Test delay calculation without jitter"""
        config = RetryConfig(base_delay=1.0, exponential_base=2.0, jitter=False)
        
        self.assertEqual(config.get_delay(0), 1.0)  # 1.0 * 2^0
        self.assertEqual(config.get_delay(1), 2.0)  # 1.0 * 2^1
        self.assertEqual(config.get_delay(2), 4.0)  # 1.0 * 2^2
        self.assertEqual(config.get_delay(3), 8.0)  # 1.0 * 2^3
    
    def test_get_delay_with_max(self):
        """Test delay calculation with max delay limit"""
        config = RetryConfig(base_delay=1.0, max_delay=5.0, exponential_base=2.0, jitter=False)
        
        self.assertEqual(config.get_delay(0), 1.0)
        self.assertEqual(config.get_delay(1), 2.0)
        self.assertEqual(config.get_delay(2), 4.0)
        self.assertEqual(config.get_delay(3), 5.0)  # Capped at max_delay
        self.assertEqual(config.get_delay(10), 5.0)  # Still capped
    
    def test_get_delay_with_jitter(self):
        """Test delay calculation with jitter"""
        config = RetryConfig(base_delay=2.0, exponential_base=2.0, jitter=True)
        
        # With jitter, delay should be between 50% and 100% of calculated value
        delay = config.get_delay(1)  # Base calculation: 2.0 * 2^1 = 4.0
        self.assertGreaterEqual(delay, 2.0)  # At least 50% of 4.0
        self.assertLessEqual(delay, 4.0)     # At most 100% of 4.0


class TestErrorHandler(unittest.TestCase):
    """Test cases for ErrorHandler class"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.logger = Mock(spec=logging.Logger)
        self.error_handler = ErrorHandler(self.logger)
    
    def test_init_with_logger(self):
        """Test ErrorHandler initialization with logger"""
        self.assertEqual(self.error_handler.logger, self.logger)
        self.assertEqual(len(self.error_handler.error_history), 0)
        self.assertIn(ErrorCategory.NETWORK, self.error_handler.retry_configs)
    
    def test_init_without_logger(self):
        """Test ErrorHandler initialization without logger"""
        handler = ErrorHandler()
        self.assertIsNotNone(handler.logger)
        self.assertEqual(handler.logger.name, 'pipeline.utils.error_handler')
    
    def test_categorize_network_error(self):
        """Test categorization of network errors"""
        # Connection error
        conn_error = requests.exceptions.ConnectionError("Connection failed")
        error_info = self.error_handler.categorize_error(conn_error)
        
        self.assertEqual(error_info.category, ErrorCategory.NETWORK)
        self.assertEqual(error_info.severity, ErrorSeverity.MEDIUM)
        self.assertIn("check your internet connection", error_info.message.lower())
        
        # Socket error
        socket_error = socket.error("Socket error")
        error_info = self.error_handler.categorize_error(socket_error)
        
        self.assertEqual(error_info.category, ErrorCategory.NETWORK)
        self.assertEqual(error_info.severity, ErrorSeverity.MEDIUM)
    
    def test_categorize_http_errors(self):
        """Test categorization of HTTP errors"""
        # Rate limit error (429)
        response_429 = Mock()
        response_429.status_code = 429
        http_error_429 = requests.exceptions.HTTPError("429 Rate Limit")
        http_error_429.response = response_429
        
        error_info = self.error_handler.categorize_error(http_error_429)
        
        self.assertEqual(error_info.category, ErrorCategory.API_RATE_LIMIT)
        self.assertEqual(error_info.severity, ErrorSeverity.MEDIUM)
        self.assertIn("rate limit", error_info.message.lower())
        
        # Authentication error (401)
        response_401 = Mock()
        response_401.status_code = 401
        http_error_401 = requests.exceptions.HTTPError("401 Unauthorized")
        http_error_401.response = response_401
        
        error_info = self.error_handler.categorize_error(http_error_401)
        
        self.assertEqual(error_info.category, ErrorCategory.AUTHENTICATION)
        self.assertEqual(error_info.severity, ErrorSeverity.HIGH)
        
        # Other HTTP error (500)
        response_500 = Mock()
        response_500.status_code = 500
        http_error_500 = requests.exceptions.HTTPError("500 Server Error")
        http_error_500.response = response_500
        
        error_info = self.error_handler.categorize_error(http_error_500)
        
        self.assertEqual(error_info.category, ErrorCategory.NETWORK)
        self.assertEqual(error_info.severity, ErrorSeverity.MEDIUM)
    
    def test_categorize_imap_errors(self):
        """Test categorization of IMAP errors"""
        # Authentication error
        auth_error = imaplib.IMAP4.error("LOGIN failed")
        error_info = self.error_handler.categorize_error(auth_error)
        
        self.assertEqual(error_info.category, ErrorCategory.AUTHENTICATION)
        self.assertEqual(error_info.severity, ErrorSeverity.HIGH)
        
        # General IMAP error
        imap_error = imaplib.IMAP4.error("Server error")
        error_info = self.error_handler.categorize_error(imap_error)
        
        self.assertEqual(error_info.category, ErrorCategory.NETWORK)
        self.assertEqual(error_info.severity, ErrorSeverity.MEDIUM)
    
    def test_categorize_data_processing_errors(self):
        """Test categorization of data processing errors"""
        errors = [
            ValueError("Invalid value"),
            TypeError("Wrong type"),
            KeyError("Missing key")
        ]
        
        for error in errors:
            error_info = self.error_handler.categorize_error(error)
            self.assertEqual(error_info.category, ErrorCategory.DATA_PROCESSING)
            self.assertEqual(error_info.severity, ErrorSeverity.MEDIUM)
    
    def test_categorize_storage_errors(self):
        """Test categorization of storage errors"""
        errors = [
            OSError("File not found"),
            IOError("I/O error"),
            PermissionError("Permission denied")  # This inherits from OSError
        ]
        
        for error in errors:
            error_info = self.error_handler.categorize_error(error)
            self.assertEqual(error_info.category, ErrorCategory.STORAGE)
            self.assertEqual(error_info.severity, ErrorSeverity.MEDIUM)
    
    def test_categorize_configuration_errors(self):
        """Test categorization of configuration errors"""
        # FileNotFoundError inherits from OSError, so it gets categorized as STORAGE
        file_error = FileNotFoundError("Config file not found")
        error_info = self.error_handler.categorize_error(file_error)
        self.assertEqual(error_info.category, ErrorCategory.STORAGE)  # OSError -> STORAGE
        self.assertEqual(error_info.severity, ErrorSeverity.MEDIUM)
        
        # ImportError should be categorized as CONFIGURATION
        import_error = ImportError("Module not found")
        error_info = self.error_handler.categorize_error(import_error)
        self.assertEqual(error_info.category, ErrorCategory.CONFIGURATION)
        self.assertEqual(error_info.severity, ErrorSeverity.HIGH)
    
    def test_categorize_unknown_error(self):
        """Test categorization of unknown errors"""
        unknown_error = RuntimeError("Unknown error")
        error_info = self.error_handler.categorize_error(unknown_error)
        
        self.assertEqual(error_info.category, ErrorCategory.UNKNOWN)
        self.assertEqual(error_info.severity, ErrorSeverity.MEDIUM)
        self.assertIn("Unexpected error", error_info.message)
    
    def test_handle_error_low_severity(self):
        """Test handling low severity errors"""
        error = ValueError("Minor issue")
        context = {"component": "test_component"}
        
        with patch.object(self.error_handler, 'categorize_error') as mock_categorize:
            mock_error_info = ErrorInfo(
                category=ErrorCategory.DATA_PROCESSING,
                severity=ErrorSeverity.LOW,
                message="Minor issue",
                original_exception=error,
                context=context
            )
            mock_categorize.return_value = mock_error_info
            
            result = self.error_handler.handle_error(error, context, raise_on_critical=True)
            
            self.assertEqual(result, mock_error_info)
            self.assertIn(mock_error_info, self.error_handler.error_history)
            self.logger.warning.assert_called_once()
    
    def test_handle_error_critical_with_raise(self):
        """Test handling critical errors with raise_on_critical=True"""
        error = ValueError("Critical issue")
        context = {"component": "test_component"}
        
        with patch.object(self.error_handler, 'categorize_error') as mock_categorize:
            mock_error_info = ErrorInfo(
                category=ErrorCategory.DATA_PROCESSING,
                severity=ErrorSeverity.CRITICAL,
                message="Critical issue",
                original_exception=error,
                context=context
            )
            mock_categorize.return_value = mock_error_info
            
            with self.assertRaises(DataProcessingError):
                self.error_handler.handle_error(error, context, raise_on_critical=True)
    
    def test_handle_error_critical_without_raise(self):
        """Test handling critical errors with raise_on_critical=False"""
        error = ValueError("Critical issue")
        context = {"component": "test_component"}
        
        with patch.object(self.error_handler, 'categorize_error') as mock_categorize:
            mock_error_info = ErrorInfo(
                category=ErrorCategory.DATA_PROCESSING,
                severity=ErrorSeverity.CRITICAL,
                message="Critical issue",
                original_exception=error,
                context=context
            )
            mock_categorize.return_value = mock_error_info
            
            result = self.error_handler.handle_error(error, context, raise_on_critical=False)
            
            self.assertEqual(result, mock_error_info)
            self.logger.error.assert_called()
    
    @patch('time.sleep')
    def test_with_retry_success_first_attempt(self, mock_sleep):
        """Test with_retry when function succeeds on first attempt"""
        mock_func = Mock(return_value="success")
        
        result = self.error_handler.with_retry(
            mock_func, "arg1", "arg2", 
            category=ErrorCategory.NETWORK,
            context={"component": "test"},
            kwarg1="value1"
        )
        
        self.assertEqual(result, "success")
        mock_func.assert_called_once_with("arg1", "arg2", kwarg1="value1")
        mock_sleep.assert_not_called()
    
    @patch('time.sleep')
    def test_with_retry_success_after_retries(self, mock_sleep):
        """Test with_retry when function succeeds after retries"""
        mock_func = Mock(side_effect=[
            ValueError("First failure"),
            ValueError("Second failure"),
            "success"
        ])
        
        result = self.error_handler.with_retry(
            mock_func,
            category=ErrorCategory.NETWORK,
            context={"component": "test"}
        )
        
        self.assertEqual(result, "success")
        self.assertEqual(mock_func.call_count, 3)
        self.assertEqual(mock_sleep.call_count, 2)  # Sleep between retries
    
    @patch('time.sleep')
    def test_with_retry_exhausted_retries(self, mock_sleep):
        """Test with_retry when all retries are exhausted"""
        mock_func = Mock(side_effect=ValueError("Persistent failure"))
        
        with self.assertRaises(DataProcessingError):
            self.error_handler.with_retry(
                mock_func,
                category=ErrorCategory.DATA_PROCESSING,
                context={"component": "test"}
            )
        
        # DATA_PROCESSING has max_retries=2, so tries max_retries + 1 = 3 times
        self.assertEqual(mock_func.call_count, 3)
        self.assertEqual(mock_sleep.call_count, 2)  # Sleep between retries
    
    def test_with_retry_auth_error_no_retry(self):
        """Test with_retry doesn't retry authentication errors"""
        mock_func = Mock(side_effect=ValueError("Auth failed"))
        
        with patch.object(self.error_handler, 'categorize_error') as mock_categorize:
            mock_error_info = ErrorInfo(
                category=ErrorCategory.AUTHENTICATION,
                severity=ErrorSeverity.HIGH,
                message="Auth failed"
            )
            mock_categorize.return_value = mock_error_info
            
            with self.assertRaises(AuthenticationError):
                self.error_handler.with_retry(
                    mock_func,
                    category=ErrorCategory.AUTHENTICATION,
                    context={"component": "test"}
                )
            
            # Should only try once for auth errors
            mock_func.assert_called_once()
    
    def test_create_retry_decorator(self):
        """Test retry decorator creation and usage"""
        decorator = self.error_handler.create_retry_decorator(
            category=ErrorCategory.NETWORK,
            context={"component": "test"}
        )
        
        @decorator
        def test_function(x, y):
            if x < 2:
                raise ValueError("Not ready yet")
            return x + y
        
        # Mock the with_retry method to avoid actual retries
        with patch.object(self.error_handler, 'with_retry', return_value=5) as mock_retry:
            result = test_function(3, 2)
            
            self.assertEqual(result, 5)
            mock_retry.assert_called_once()
    
    def test_get_error_summary_empty(self):
        """Test error summary when no errors occurred"""
        summary = self.error_handler.get_error_summary()
        
        expected = {
            "total_errors": 0,
            "by_category": {},
            "by_severity": {},
            "recent_errors": []
        }
        
        self.assertEqual(summary, expected)
    
    def test_get_error_summary_with_errors(self):
        """Test error summary with multiple errors"""
        # Add some errors to history
        errors = [
            ErrorInfo(ErrorCategory.NETWORK, ErrorSeverity.MEDIUM, "Network error 1"),
            ErrorInfo(ErrorCategory.NETWORK, ErrorSeverity.LOW, "Network error 2"),
            ErrorInfo(ErrorCategory.AUTHENTICATION, ErrorSeverity.HIGH, "Auth error"),
            ErrorInfo(ErrorCategory.DATA_PROCESSING, ErrorSeverity.MEDIUM, "Data error")
        ]
        
        self.error_handler.error_history = errors
        
        summary = self.error_handler.get_error_summary()
        
        self.assertEqual(summary["total_errors"], 4)
        self.assertEqual(summary["by_category"]["network"], 2)
        self.assertEqual(summary["by_category"]["authentication"], 1)
        self.assertEqual(summary["by_category"]["data_processing"], 1)
        self.assertEqual(summary["by_severity"]["medium"], 2)
        self.assertEqual(summary["by_severity"]["low"], 1)
        self.assertEqual(summary["by_severity"]["high"], 1)
        self.assertEqual(len(summary["recent_errors"]), 4)
    
    def test_clear_error_history(self):
        """Test clearing error history"""
        # Add some errors
        self.error_handler.error_history = [
            ErrorInfo(ErrorCategory.NETWORK, ErrorSeverity.MEDIUM, "Error 1"),
            ErrorInfo(ErrorCategory.AUTHENTICATION, ErrorSeverity.HIGH, "Error 2")
        ]
        
        self.assertEqual(len(self.error_handler.error_history), 2)
        
        self.error_handler.clear_error_history()
        
        self.assertEqual(len(self.error_handler.error_history), 0)
    
    def test_should_continue_processing_under_limits(self):
        """Test should_continue_processing when under error limits"""
        # Add some non-critical errors
        errors = [
            ErrorInfo(ErrorCategory.NETWORK, ErrorSeverity.MEDIUM, f"Error {i}")
            for i in range(5)
        ]
        self.error_handler.error_history = errors
        
        self.assertTrue(self.error_handler.should_continue_processing())
        self.assertTrue(self.error_handler.should_continue_processing(max_errors=10))
    
    def test_should_continue_processing_over_limits(self):
        """Test should_continue_processing when over error limits"""
        # Add many errors
        errors = [
            ErrorInfo(ErrorCategory.NETWORK, ErrorSeverity.MEDIUM, f"Error {i}")
            for i in range(15)
        ]
        self.error_handler.error_history = errors
        
        self.assertFalse(self.error_handler.should_continue_processing(max_errors=10))
    
    def test_should_continue_processing_critical_errors(self):
        """Test should_continue_processing with critical errors"""
        # Add critical errors
        errors = [
            ErrorInfo(ErrorCategory.NETWORK, ErrorSeverity.CRITICAL, f"Critical error {i}")
            for i in range(5)
        ]
        self.error_handler.error_history = errors
        
        self.assertFalse(self.error_handler.should_continue_processing(critical_error_threshold=3))
    
    def test_should_continue_processing_by_component(self):
        """Test should_continue_processing filtered by component"""
        # Add errors for different components
        errors = [
            ErrorInfo(ErrorCategory.NETWORK, ErrorSeverity.MEDIUM, "Error 1", component="comp1"),
            ErrorInfo(ErrorCategory.NETWORK, ErrorSeverity.MEDIUM, "Error 2", component="comp1"),
            ErrorInfo(ErrorCategory.NETWORK, ErrorSeverity.MEDIUM, "Error 3", component="comp2"),
        ]
        self.error_handler.error_history = errors
        
        # Should continue for comp2 (only 1 error)
        self.assertTrue(self.error_handler.should_continue_processing(
            max_errors=2, component="comp2"
        ))
        
        # Should not continue for comp1 (2 errors, limit is 2)
        self.assertFalse(self.error_handler.should_continue_processing(
            max_errors=1, component="comp1"
        ))
    
    def test_circuit_breaker_initial_state(self):
        """Test initial circuit breaker state"""
        state = self.error_handler.get_circuit_breaker_state("test_component")
        
        expected = {
            'state': 'closed',
            'failure_count': 0,
            'last_failure_time': None,
            'next_attempt_time': None
        }
        
        self.assertEqual(state, expected)
    
    def test_circuit_breaker_success_updates(self):
        """Test circuit breaker updates on success"""
        component = "test_component"
        
        # Simulate some failures first
        for _ in range(3):
            self.error_handler.update_circuit_breaker(component, False)
        
        # Then a success
        self.error_handler.update_circuit_breaker(component, True)
        
        state = self.error_handler.get_circuit_breaker_state(component)
        self.assertEqual(state['failure_count'], 0)
        self.assertEqual(state['state'], 'closed')
        self.assertIsNone(state['next_attempt_time'])
    
    def test_circuit_breaker_opens_on_failures(self):
        """Test circuit breaker opens after too many failures"""
        component = "test_component"
        
        # Simulate 5 failures (threshold)
        for _ in range(5):
            self.error_handler.update_circuit_breaker(component, False)
        
        state = self.error_handler.get_circuit_breaker_state(component)
        self.assertEqual(state['state'], 'open')
        self.assertEqual(state['failure_count'], 5)
        self.assertIsNotNone(state['next_attempt_time'])
    
    def test_is_circuit_breaker_open(self):
        """Test circuit breaker open detection"""
        component = "test_component"
        
        # Initially closed
        self.assertFalse(self.error_handler.is_circuit_breaker_open(component))
        
        # After failures, should be open
        for _ in range(5):
            self.error_handler.update_circuit_breaker(component, False)
        
        self.assertTrue(self.error_handler.is_circuit_breaker_open(component))


class TestBatchErrorHandler(unittest.TestCase):
    """Test cases for BatchErrorHandler"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.logger = Mock(spec=logging.Logger)
        self.error_handler = ErrorHandler(self.logger)
        self.batch_handler = BatchErrorHandler(self.error_handler, max_failures_per_batch=3)
    
    def test_process_batch_all_success(self):
        """Test batch processing when all items succeed"""
        items = [1, 2, 3, 4, 5]
        
        def processor(item):
            return item * 2
        
        result = self.batch_handler.process_batch(items, processor)
        
        self.assertEqual(result['successful_count'], 5)
        self.assertEqual(result['failed_count'], 0)
        self.assertEqual(result['total_count'], 5)
        self.assertEqual(result['success_rate'], 1.0)
        self.assertEqual(len(result['successful_items']), 5)
        self.assertEqual(len(result['failed_items']), 0)
        self.assertEqual(len(result['errors']), 0)
        self.assertFalse(result['should_retry_failed'])  # No failures, so no retry needed
    
    def test_process_batch_some_failures(self):
        """Test batch processing with some failures"""
        items = [1, 2, 3, 4, 5]
        
        def processor(item):
            if item in [2, 4]:
                raise ValueError(f"Failed on item {item}")
            return item * 2
        
        result = self.batch_handler.process_batch(items, processor)
        
        self.assertEqual(result['successful_count'], 3)
        self.assertEqual(result['failed_count'], 2)
        self.assertEqual(result['total_count'], 5)
        self.assertEqual(result['success_rate'], 0.6)
        self.assertEqual(len(result['successful_items']), 3)
        self.assertEqual(len(result['failed_items']), 2)
        self.assertEqual(len(result['errors']), 2)
        self.assertTrue(result['should_retry_failed'])
    
    def test_process_batch_too_many_failures(self):
        """Test batch processing stops after too many failures"""
        items = [1, 2, 3, 4, 5, 6, 7, 8]
        
        def processor(item):
            if item <= 4:  # First 4 items fail
                raise ValueError(f"Failed on item {item}")
            return item * 2
        
        result = self.batch_handler.process_batch(items, processor)
        
        # Should stop after 3 failures (max_failures_per_batch)
        self.assertEqual(result['failed_count'], 3)
        self.assertLess(result['successful_count'], 4)  # Didn't process all items
        self.assertFalse(result['should_retry_failed'])
    
    def test_process_batch_empty_items(self):
        """Test batch processing with empty items list"""
        items = []
        
        def processor(item):
            return item * 2
        
        result = self.batch_handler.process_batch(items, processor)
        
        self.assertEqual(result['successful_count'], 0)
        self.assertEqual(result['failed_count'], 0)
        self.assertEqual(result['total_count'], 0)
        self.assertEqual(result['success_rate'], 0)
    
    def test_retry_failed_items_success(self):
        """Test retrying failed items successfully"""
        # Create initial batch result with failures
        failed_items = [
            {'item': 2, 'error': Mock(), 'index': 1},
            {'item': 4, 'error': Mock(), 'index': 3}
        ]
        
        batch_result = {
            'successful_count': 3,
            'failed_count': 2,
            'total_count': 5,
            'success_rate': 0.6,
            'successful_items': [Mock(), Mock(), Mock()],
            'failed_items': failed_items,
            'should_retry_failed': True
        }
        
        def processor(item):
            return item * 2  # Now succeeds
        
        # Mock process_batch to simulate successful retry
        with patch.object(self.batch_handler, 'process_batch') as mock_process:
            mock_process.return_value = {
                'successful_count': 2,
                'failed_count': 0,
                'successful_items': [{'item': 2, 'result': 4}, {'item': 4, 'result': 8}],
                'failed_items': [],
                'should_retry_failed': False
            }
            
            updated_result = self.batch_handler.retry_failed_items(
                batch_result, processor, max_retries=2
            )
        
        self.assertEqual(updated_result['successful_count'], 5)  # 3 + 2
        self.assertEqual(updated_result['failed_count'], 0)
        self.assertEqual(updated_result['success_rate'], 1.0)
    
    def test_retry_failed_items_no_retry_needed(self):
        """Test retry when no retry is needed"""
        batch_result = {
            'should_retry_failed': False,
            'failed_items': []
        }
        
        def processor(item):
            return item * 2
        
        updated_result = self.batch_handler.retry_failed_items(batch_result, processor)
        
        self.assertEqual(updated_result, batch_result)  # Should return unchanged


class TestErrorDecorators(unittest.TestCase):
    """Test cases for error handling decorators"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.logger = Mock(spec=logging.Logger)
        self.error_handler = ErrorHandler(self.logger)
    
    def test_with_error_handling_success(self):
        """Test with_error_handling decorator on successful function"""
        @with_error_handling(self.error_handler, ErrorCategory.NETWORK)
        def test_function(x, y):
            return x + y
        
        result = test_function(2, 3)
        self.assertEqual(result, 5)
    
    def test_with_error_handling_failure_no_raise(self):
        """Test with_error_handling decorator on failing function without raise"""
        @with_error_handling(self.error_handler, ErrorCategory.NETWORK, raise_on_error=False)
        def test_function():
            raise ValueError("Test error")
        
        result = test_function()
        self.assertIsNone(result)
    
    def test_with_error_handling_failure_with_raise(self):
        """Test with_error_handling decorator on failing function with raise"""
        @with_error_handling(self.error_handler, ErrorCategory.NETWORK, raise_on_error=True)
        def test_function():
            raise ValueError("Test error")
        
        with self.assertRaises(ValueError):
            test_function()
    
    def test_graceful_degradation_success(self):
        """Test graceful_degradation decorator on successful function"""
        @graceful_degradation(self.error_handler, fallback_value="fallback")
        def test_function(x):
            return x * 2
        
        result = test_function(5)
        self.assertEqual(result, 10)
    
    def test_graceful_degradation_failure(self):
        """Test graceful_degradation decorator on failing function"""
        @graceful_degradation(self.error_handler, fallback_value="fallback")
        def test_function():
            raise ValueError("Test error")
        
        result = test_function()
        self.assertEqual(result, "fallback")
    
    def test_graceful_degradation_no_logging(self):
        """Test graceful_degradation decorator without error logging"""
        @graceful_degradation(self.error_handler, fallback_value="fallback", log_errors=False)
        def test_function():
            raise ValueError("Test error")
        
        result = test_function()
        self.assertEqual(result, "fallback")
        # Should not have called error handler since log_errors=False


class TestPipelineExceptions(unittest.TestCase):
    """Test cases for custom pipeline exceptions"""
    
    def test_pipeline_error_creation(self):
        """Test PipelineError creation with ErrorInfo"""
        error_info = ErrorInfo(
            category=ErrorCategory.NETWORK,
            severity=ErrorSeverity.HIGH,
            message="Network failure"
        )
        
        exception = PipelineError(error_info)
        
        self.assertEqual(exception.error_info, error_info)
        self.assertEqual(str(exception), "Network failure")
    
    def test_specific_exception_types(self):
        """Test specific exception type creation"""
        error_info = ErrorInfo(
            category=ErrorCategory.AUTHENTICATION,
            severity=ErrorSeverity.HIGH,
            message="Auth failed"
        )
        
        # Test each specific exception type
        exceptions = [
            (AuthenticationError, ErrorCategory.AUTHENTICATION),
            (NetworkError, ErrorCategory.NETWORK),
            (RateLimitError, ErrorCategory.API_RATE_LIMIT),
            (DataProcessingError, ErrorCategory.DATA_PROCESSING),
            (StorageError, ErrorCategory.STORAGE),
            (ConfigurationError, ErrorCategory.CONFIGURATION),
            (ValidationError, ErrorCategory.VALIDATION)
        ]
        
        for exception_class, category in exceptions:
            error_info.category = category
            exception = exception_class(error_info)
            
            self.assertIsInstance(exception, PipelineError)
            self.assertEqual(exception.error_info.category, category)


if __name__ == '__main__':
    unittest.main()