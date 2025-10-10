"""
Unit tests for the comprehensive error handling system
"""

import pytest
import time
import logging
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime
import requests
import imaplib
import socket
import ssl

from pipeline.utils.error_handler import (
    ErrorHandler, ErrorCategory, ErrorSeverity, ErrorInfo, RetryConfig,
    PipelineError, AuthenticationError, NetworkError, RateLimitError,
    DataProcessingError, StorageError, ConfigurationError, ValidationError,
    with_error_handling, graceful_degradation, BatchErrorHandler, 
    ErrorRecoveryManager, resilient_operation
)


class TestErrorInfo:
    """Test ErrorInfo data class"""
    
    def test_error_info_creation(self):
        """Test creating ErrorInfo object"""
        error = ErrorInfo(
            category=ErrorCategory.NETWORK,
            severity=ErrorSeverity.MEDIUM,
            message="Test error",
            component="test_component"
        )
        
        assert error.category == ErrorCategory.NETWORK
        assert error.severity == ErrorSeverity.MEDIUM
        assert error.message == "Test error"
        assert error.component == "test_component"
        assert error.retry_count == 0
        assert error.max_retries == 3
        assert isinstance(error.timestamp, datetime)
    
    def test_error_info_to_dict(self):
        """Test converting ErrorInfo to dictionary"""
        exception = ValueError("Test exception")
        error = ErrorInfo(
            category=ErrorCategory.DATA_PROCESSING,
            severity=ErrorSeverity.HIGH,
            message="Processing failed",
            original_exception=exception,
            context={'key': 'value'},
            component="processor"
        )
        
        error_dict = error.to_dict()
        
        assert error_dict['category'] == 'data_processing'
        assert error_dict['severity'] == 'high'
        assert error_dict['message'] == 'Processing failed'
        assert error_dict['exception_type'] == 'ValueError'
        assert error_dict['exception_message'] == 'Test exception'
        assert error_dict['context'] == {'key': 'value'}
        assert error_dict['component'] == 'processor'


class TestRetryConfig:
    """Test RetryConfig functionality"""
    
    def test_default_retry_config(self):
        """Test default retry configuration"""
        config = RetryConfig()
        
        assert config.max_retries == 3
        assert config.base_delay == 1.0
        assert config.max_delay == 60.0
        assert config.exponential_base == 2.0
        assert config.jitter is True
    
    def test_get_delay_exponential(self):
        """Test exponential backoff delay calculation"""
        config = RetryConfig(base_delay=1.0, exponential_base=2.0, jitter=False)
        
        assert config.get_delay(0) == 1.0
        assert config.get_delay(1) == 2.0
        assert config.get_delay(2) == 4.0
        assert config.get_delay(3) == 8.0
    
    def test_get_delay_max_limit(self):
        """Test delay is capped at max_delay"""
        config = RetryConfig(base_delay=1.0, max_delay=5.0, exponential_base=2.0, jitter=False)
        
        assert config.get_delay(10) == 5.0  # Should be capped at max_delay
    
    def test_get_delay_with_jitter(self):
        """Test delay calculation with jitter"""
        config = RetryConfig(base_delay=2.0, exponential_base=2.0, jitter=True)
        
        # With jitter, delay should be between 50% and 100% of calculated value
        delay = config.get_delay(1)  # Base calculation would be 4.0
        assert 2.0 <= delay <= 4.0


class TestErrorHandler:
    """Test ErrorHandler functionality"""
    
    def setup_method(self):
        """Setup test fixtures"""
        self.logger = Mock(spec=logging.Logger)
        self.error_handler = ErrorHandler(self.logger)
    
    def test_categorize_network_error(self):
        """Test categorizing network-related errors"""
        error = requests.exceptions.ConnectionError("Connection failed")
        error_info = self.error_handler.categorize_error(error)
        
        assert error_info.category == ErrorCategory.NETWORK
        assert error_info.severity == ErrorSeverity.MEDIUM
        assert "internet connection" in error_info.message.lower()
    
    def test_categorize_authentication_error(self):
        """Test categorizing authentication errors"""
        response = Mock()
        response.status_code = 401
        error = requests.exceptions.HTTPError()
        error.response = response
        
        error_info = self.error_handler.categorize_error(error)
        
        assert error_info.category == ErrorCategory.AUTHENTICATION
        assert error_info.severity == ErrorSeverity.HIGH
    
    def test_categorize_rate_limit_error(self):
        """Test categorizing rate limit errors"""
        response = Mock()
        response.status_code = 429
        error = requests.exceptions.HTTPError()
        error.response = response
        
        error_info = self.error_handler.categorize_error(error)
        
        assert error_info.category == ErrorCategory.API_RATE_LIMIT
        assert error_info.severity == ErrorSeverity.MEDIUM
    
    def test_categorize_imap_authentication_error(self):
        """Test categorizing IMAP authentication errors"""
        error = imaplib.IMAP4.error("authentication failed")
        error_info = self.error_handler.categorize_error(error)
        
        assert error_info.category == ErrorCategory.AUTHENTICATION
        assert error_info.severity == ErrorSeverity.HIGH
    
    def test_categorize_data_processing_error(self):
        """Test categorizing data processing errors"""
        error = ValueError("Invalid data format")
        error_info = self.error_handler.categorize_error(error)
        
        assert error_info.category == ErrorCategory.DATA_PROCESSING
        assert error_info.severity == ErrorSeverity.MEDIUM
    
    def test_categorize_storage_error(self):
        """Test categorizing storage errors"""
        error = PermissionError("Permission denied")
        error_info = self.error_handler.categorize_error(error)
        
        assert error_info.category == ErrorCategory.STORAGE
        assert error_info.severity == ErrorSeverity.MEDIUM
    
    def test_categorize_configuration_error(self):
        """Test categorizing configuration errors"""
        error = FileNotFoundError("Config file not found")
        error_info = self.error_handler.categorize_error(error)
        
        assert error_info.category == ErrorCategory.CONFIGURATION
        assert error_info.severity == ErrorSeverity.HIGH
    
    def test_categorize_unknown_error(self):
        """Test categorizing unknown errors"""
        error = RuntimeError("Unknown error")
        error_info = self.error_handler.categorize_error(error)
        
        assert error_info.category == ErrorCategory.UNKNOWN
        assert error_info.severity == ErrorSeverity.MEDIUM
    
    def test_handle_error_logging(self):
        """Test error handling logs appropriately"""
        error = ValueError("Test error")
        context = {'component': 'test', 'operation': 'test_op'}
        
        error_info = self.error_handler.handle_error(error, context, raise_on_critical=False)
        
        assert len(self.error_handler.error_history) == 1
        assert self.error_handler.error_history[0] == error_info
        self.logger.error.assert_called_once()
    
    def test_handle_critical_error_raises(self):
        """Test critical errors are raised when raise_on_critical=True"""
        error = FileNotFoundError("Critical config missing")
        context = {'component': 'test'}
        
        with pytest.raises(ConfigurationError):
            self.error_handler.handle_error(error, context, raise_on_critical=True)
    
    def test_with_retry_success(self):
        """Test successful function execution with retry"""
        mock_func = Mock(return_value="success")
        
        result = self.error_handler.with_retry(
            mock_func,
            "arg1", "arg2",
            category=ErrorCategory.NETWORK,
            context={'test': 'context'},
            kwarg1="value1"
        )
        
        assert result == "success"
        mock_func.assert_called_once_with("arg1", "arg2", kwarg1="value1")
    
    def test_with_retry_eventual_success(self):
        """Test retry logic with eventual success"""
        mock_func = Mock(side_effect=[
            requests.exceptions.ConnectionError("Failed"),
            requests.exceptions.ConnectionError("Failed again"),
            "success"
        ])
        
        with patch('time.sleep'):  # Mock sleep to speed up test
            result = self.error_handler.with_retry(
                mock_func,
                category=ErrorCategory.NETWORK
            )
        
        assert result == "success"
        assert mock_func.call_count == 3
    
    def test_with_retry_exhausted(self):
        """Test retry logic when all attempts are exhausted"""
        mock_func = Mock(side_effect=requests.exceptions.ConnectionError("Always fails"))
        
        with patch('time.sleep'):  # Mock sleep to speed up test
            with pytest.raises(NetworkError):
                self.error_handler.with_retry(
                    mock_func,
                    category=ErrorCategory.NETWORK
                )
        
        # Should try max_retries + 1 times (initial + retries)
        retry_config = self.error_handler.retry_configs[ErrorCategory.NETWORK]
        assert mock_func.call_count == retry_config.max_retries + 1
    
    def test_with_retry_no_retry_for_auth_errors(self):
        """Test authentication errors are not retried"""
        mock_func = Mock(side_effect=requests.exceptions.HTTPError())
        mock_func.side_effect.response = Mock()
        mock_func.side_effect.response.status_code = 401
        
        with pytest.raises(AuthenticationError):
            self.error_handler.with_retry(
                mock_func,
                category=ErrorCategory.AUTHENTICATION
            )
        
        # Should only be called once (no retries for auth errors)
        assert mock_func.call_count == 1
    
    def test_get_error_summary_empty(self):
        """Test error summary when no errors occurred"""
        summary = self.error_handler.get_error_summary()
        
        assert summary['total_errors'] == 0
        assert summary['by_category'] == {}
        assert summary['by_severity'] == {}
        assert summary['recent_errors'] == []
    
    def test_get_error_summary_with_errors(self):
        """Test error summary with multiple errors"""
        # Add some errors
        error1 = ValueError("Error 1")
        error2 = requests.exceptions.ConnectionError("Error 2")
        error3 = PermissionError("Error 3")
        
        self.error_handler.handle_error(error1, raise_on_critical=False)
        self.error_handler.handle_error(error2, raise_on_critical=False)
        self.error_handler.handle_error(error3, raise_on_critical=False)
        
        summary = self.error_handler.get_error_summary()
        
        assert summary['total_errors'] == 3
        assert summary['by_category']['data_processing'] == 1
        assert summary['by_category']['network'] == 1
        assert summary['by_category']['storage'] == 1
        assert summary['by_severity']['medium'] == 3
        assert len(summary['recent_errors']) == 3
    
    def test_should_continue_processing(self):
        """Test processing continuation logic"""
        # Should continue with no errors
        assert self.error_handler.should_continue_processing()
        
        # Add some non-critical errors
        for _ in range(5):
            error = ValueError("Non-critical error")
            self.error_handler.handle_error(error, raise_on_critical=False)
        
        # Should still continue
        assert self.error_handler.should_continue_processing(max_errors=10)
        
        # Add more errors to exceed threshold
        for _ in range(6):
            error = ValueError("More errors")
            self.error_handler.handle_error(error, raise_on_critical=False)
        
        # Should not continue (11 errors > 10 max)
        assert not self.error_handler.should_continue_processing(max_errors=10)
    
    def test_clear_error_history(self):
        """Test clearing error history"""
        # Add some errors
        error = ValueError("Test error")
        self.error_handler.handle_error(error, raise_on_critical=False)
        
        assert len(self.error_handler.error_history) == 1
        
        self.error_handler.clear_error_history()
        
        assert len(self.error_handler.error_history) == 0


class TestErrorDecorators:
    """Test error handling decorators"""
    
    def setup_method(self):
        """Setup test fixtures"""
        self.logger = Mock(spec=logging.Logger)
        self.error_handler = ErrorHandler(self.logger)
    
    def test_with_error_handling_decorator_success(self):
        """Test with_error_handling decorator on successful function"""
        @with_error_handling(self.error_handler, raise_on_error=False)
        def test_function(x, y):
            return x + y
        
        result = test_function(1, 2)
        assert result == 3
    
    def test_with_error_handling_decorator_error(self):
        """Test with_error_handling decorator on function that raises error"""
        @with_error_handling(self.error_handler, raise_on_error=False)
        def test_function():
            raise ValueError("Test error")
        
        result = test_function()
        assert result is None
        assert len(self.error_handler.error_history) == 1
    
    def test_with_error_handling_decorator_raise_on_error(self):
        """Test with_error_handling decorator with raise_on_error=True"""
        @with_error_handling(self.error_handler, raise_on_error=True)
        def test_function():
            raise ValueError("Test error")
        
        with pytest.raises(DataProcessingError):
            test_function()
    
    def test_graceful_degradation_decorator_success(self):
        """Test graceful_degradation decorator on successful function"""
        @graceful_degradation(self.error_handler, fallback_value="fallback")
        def test_function(x):
            return x * 2
        
        result = test_function(5)
        assert result == 10
    
    def test_graceful_degradation_decorator_error(self):
        """Test graceful_degradation decorator on function that raises error"""
        @graceful_degradation(self.error_handler, fallback_value="fallback")
        def test_function():
            raise ValueError("Test error")
        
        result = test_function()
        assert result == "fallback"
        assert len(self.error_handler.error_history) == 1
    
    def test_graceful_degradation_no_logging(self):
        """Test graceful_degradation decorator with log_errors=False"""
        @graceful_degradation(self.error_handler, fallback_value="fallback", log_errors=False)
        def test_function():
            raise ValueError("Test error")
        
        result = test_function()
        assert result == "fallback"
        assert len(self.error_handler.error_history) == 0


class TestPipelineExceptions:
    """Test custom pipeline exceptions"""
    
    def test_pipeline_error_creation(self):
        """Test creating PipelineError with ErrorInfo"""
        error_info = ErrorInfo(
            category=ErrorCategory.NETWORK,
            severity=ErrorSeverity.MEDIUM,
            message="Network error"
        )
        
        exception = PipelineError(error_info)
        assert exception.error_info == error_info
        assert str(exception) == "Network error"
    
    def test_specific_exception_types(self):
        """Test specific exception types inherit from PipelineError"""
        error_info = ErrorInfo(
            category=ErrorCategory.AUTHENTICATION,
            severity=ErrorSeverity.HIGH,
            message="Auth failed"
        )
        
        auth_error = AuthenticationError(error_info)
        assert isinstance(auth_error, PipelineError)
        assert auth_error.error_info.category == ErrorCategory.AUTHENTICATION


class TestErrorRecoveryScenarios:
    """Test error recovery in realistic scenarios"""
    
    def setup_method(self):
        """Setup test fixtures"""
        self.logger = Mock(spec=logging.Logger)
        self.error_handler = ErrorHandler(self.logger)
    
    def test_network_timeout_recovery(self):
        """Test recovery from network timeout"""
        call_count = 0
        
        def flaky_network_call():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise socket.timeout("Network timeout")
            return "success"
        
        with patch('time.sleep'):
            result = self.error_handler.with_retry(
                flaky_network_call,
                category=ErrorCategory.NETWORK
            )
        
        assert result == "success"
        assert call_count == 3
    
    def test_rate_limit_recovery(self):
        """Test recovery from API rate limiting"""
        call_count = 0
        
        def rate_limited_api_call():
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                response = Mock()
                response.status_code = 429
                error = requests.exceptions.HTTPError()
                error.response = response
                raise error
            return {"data": "success"}
        
        with patch('time.sleep'):
            result = self.error_handler.with_retry(
                rate_limited_api_call,
                category=ErrorCategory.API_RATE_LIMIT
            )
        
        assert result == {"data": "success"}
        assert call_count == 2
    
    def test_partial_failure_graceful_degradation(self):
        """Test graceful degradation with partial failures"""
        items = ["item1", "item2", "item3", "item4"]
        results = []
        
        @graceful_degradation(self.error_handler, fallback_value=None)
        def process_item(item):
            if item == "item2":
                raise ValueError("Processing failed for item2")
            return f"processed_{item}"
        
        # Process all items, some may fail
        for item in items:
            result = process_item(item)
            if result is not None:
                results.append(result)
        
        # Should have processed 3 out of 4 items
        assert len(results) == 3
        assert "processed_item1" in results
        assert "processed_item3" in results
        assert "processed_item4" in results
        
        # Should have logged one error
        assert len(self.error_handler.error_history) == 1
    
    def test_cascading_failure_prevention(self):
        """Test prevention of cascading failures"""
        failure_count = 0
        
        def potentially_failing_operation():
            nonlocal failure_count
            failure_count += 1
            if failure_count <= 2:
                raise ConnectionError("Service unavailable")
            return "recovered"
        
        # First few calls should fail but not stop processing
        results = []
        for i in range(5):
            try:
                result = self.error_handler.with_retry(
                    potentially_failing_operation,
                    category=ErrorCategory.NETWORK
                )
                results.append(result)
            except NetworkError:
                # Expected for first few attempts
                pass
            
            # Reset failure count to simulate service recovery
            if i == 2:
                failure_count = 0
        
        # Should have some successful results after recovery
        assert len(results) >= 1
        assert "recovered" in results


if __name__ == "__main__":
    pytest.main([__file__])


class TestCircuitBreaker:
    """Test circuit breaker functionality"""
    
    def setup_method(self):
        """Setup test fixtures"""
        self.logger = Mock(spec=logging.Logger)
        self.error_handler = ErrorHandler(self.logger)
    
    def test_circuit_breaker_closed_initially(self):
        """Test circuit breaker starts in closed state"""
        assert not self.error_handler.is_circuit_breaker_open('test_component')
        
        state = self.error_handler.get_circuit_breaker_state('test_component')
        assert state['state'] == 'closed'
        assert state['failure_count'] == 0
    
    def test_circuit_breaker_opens_after_failures(self):
        """Test circuit breaker opens after multiple failures"""
        component = 'test_component'
        
        # Simulate 5 failures to trigger circuit breaker
        for i in range(5):
            self.error_handler.update_circuit_breaker(component, False)
        
        # Circuit breaker should now be open
        assert self.error_handler.is_circuit_breaker_open(component)
        
        state = self.error_handler.get_circuit_breaker_state(component)
        assert state['state'] == 'open'
        assert state['failure_count'] == 5
    
    def test_circuit_breaker_resets_on_success(self):
        """Test circuit breaker resets after success"""
        component = 'test_component'
        
        # Simulate some failures
        for i in range(3):
            self.error_handler.update_circuit_breaker(component, False)
        
        # Then a success
        self.error_handler.update_circuit_breaker(component, True)
        
        # Circuit breaker should be closed and reset
        assert not self.error_handler.is_circuit_breaker_open(component)
        
        state = self.error_handler.get_circuit_breaker_state(component)
        assert state['state'] == 'closed'
        assert state['failure_count'] == 0
    
    def test_circuit_breaker_half_open_state(self):
        """Test circuit breaker half-open state after timeout"""
        component = 'test_component'
        
        # Open the circuit breaker
        for i in range(5):
            self.error_handler.update_circuit_breaker(component, False)
        
        assert self.error_handler.is_circuit_breaker_open(component)
        
        # Manually set next attempt time to past (simulate timeout)
        self.error_handler.circuit_breaker_state[component]['next_attempt_time'] = time.time() - 1
        
        # Should now allow attempts (half-open state)
        assert not self.error_handler.is_circuit_breaker_open(component)
        
        state = self.error_handler.get_circuit_breaker_state(component)
        assert state['state'] == 'half-open'


class TestBatchErrorHandler:
    """Test batch error handling functionality"""
    
    def setup_method(self):
        """Setup test fixtures"""
        self.logger = Mock(spec=logging.Logger)
        self.error_handler = ErrorHandler(self.logger)
        self.batch_handler = BatchErrorHandler(self.error_handler, max_failures_per_batch=3)
    
    def test_batch_processing_all_success(self):
        """Test batch processing when all items succeed"""
        items = [1, 2, 3, 4, 5]
        
        def processor(item):
            return item * 2
        
        result = self.batch_handler.process_batch(items, processor)
        
        assert result['successful_count'] == 5
        assert result['failed_count'] == 0
        assert result['success_rate'] == 1.0
        assert len(result['successful_items']) == 5
        assert len(result['failed_items']) == 0
    
    def test_batch_processing_partial_failure(self):
        """Test batch processing with some failures"""
        items = [1, 2, 3, 4, 5]
        
        def processor(item):
            if item in [2, 4]:
                raise ValueError(f"Processing failed for item {item}")
            return item * 2
        
        result = self.batch_handler.process_batch(items, processor)
        
        assert result['successful_count'] == 3
        assert result['failed_count'] == 2
        assert result['success_rate'] == 0.6
        assert len(result['successful_items']) == 3
        assert len(result['failed_items']) == 2
        assert result['should_retry_failed'] is True
    
    def test_batch_processing_stops_on_threshold(self):
        """Test batch processing stops when failure threshold is reached"""
        items = [1, 2, 3, 4, 5, 6, 7, 8]
        
        def processor(item):
            if item <= 4:  # First 4 items fail
                raise ValueError(f"Processing failed for item {item}")
            return item * 2
        
        result = self.batch_handler.process_batch(items, processor)
        
        # Should stop after 3 failures (threshold)
        assert result['failed_count'] == 3
        assert result['successful_count'] == 0  # No successful items processed
        assert len(result['errors']) == 3
    
    def test_retry_failed_items(self):
        """Test retrying failed items from a batch"""
        items = [1, 2, 3, 4, 5]
        failure_count = 0
        
        def flaky_processor(item):
            nonlocal failure_count
            if item in [2, 4] and failure_count < 2:
                failure_count += 1
                raise ValueError(f"Temporary failure for item {item}")
            return item * 2
        
        # Initial batch processing
        result = self.batch_handler.process_batch(items, flaky_processor)
        assert result['failed_count'] == 2
        
        # Retry failed items
        retry_result = self.batch_handler.retry_failed_items(result, flaky_processor, max_retries=2)
        
        # After retry, should have more successes
        assert retry_result['successful_count'] > result['successful_count']
        assert retry_result['success_rate'] > result['success_rate']


class TestErrorRecoveryManager:
    """Test error recovery manager functionality"""
    
    def setup_method(self):
        """Setup test fixtures"""
        self.logger = Mock(spec=logging.Logger)
        self.error_handler = ErrorHandler(self.logger)
        self.recovery_manager = ErrorRecoveryManager(self.error_handler)
    
    def test_register_fallback_strategy(self):
        """Test registering fallback strategies"""
        def network_fallback(*args, **kwargs):
            return "fallback_result"
        
        self.recovery_manager.register_fallback_strategy(
            ErrorCategory.NETWORK, 
            "simple_fallback", 
            network_fallback
        )
        
        assert ErrorCategory.NETWORK in self.recovery_manager.fallback_strategies
        assert "simple_fallback" in self.recovery_manager.fallback_strategies[ErrorCategory.NETWORK]
    
    def test_execute_with_fallback_success(self):
        """Test successful execution without fallback"""
        def primary_func(x, y):
            return x + y
        
        result = self.recovery_manager.execute_with_fallback(
            primary_func, 
            ErrorCategory.NETWORK, 
            {}, 
            5, 
            y=3
        )
        
        assert result == 8
        assert len(self.recovery_manager.recovery_history) == 0  # No fallback needed
    
    def test_execute_with_fallback_failure_and_recovery(self):
        """Test fallback execution when primary function fails"""
        def primary_func(x):
            raise ConnectionError("Network failed")
        
        def fallback_func(x):
            return f"fallback_result_{x}"
        
        self.recovery_manager.register_fallback_strategy(
            ErrorCategory.NETWORK,
            "connection_fallback",
            fallback_func
        )
        
        result = self.recovery_manager.execute_with_fallback(
            primary_func,
            ErrorCategory.NETWORK,
            {},
            "test"
        )
        
        assert result == "fallback_result_test"
        assert len(self.recovery_manager.recovery_history) == 1
        assert self.recovery_manager.recovery_history[0]['success'] is True
    
    def test_execute_with_fallback_all_fail(self):
        """Test when both primary and fallback functions fail"""
        def primary_func():
            raise ConnectionError("Primary failed")
        
        def fallback_func():
            raise ConnectionError("Fallback also failed")
        
        self.recovery_manager.register_fallback_strategy(
            ErrorCategory.NETWORK,
            "failing_fallback",
            fallback_func
        )
        
        with pytest.raises(ConnectionError):
            self.recovery_manager.execute_with_fallback(
                primary_func,
                ErrorCategory.NETWORK,
                {}
            )
        
        assert len(self.recovery_manager.recovery_history) == 1
        assert self.recovery_manager.recovery_history[0]['success'] is False
    
    def test_recovery_statistics(self):
        """Test recovery statistics generation"""
        # Simulate some recovery attempts
        self.recovery_manager.recovery_history = [
            {
                'timestamp': datetime.now(),
                'error_category': ErrorCategory.NETWORK,
                'strategy_used': 'strategy1',
                'success': True,
                'context': {}
            },
            {
                'timestamp': datetime.now(),
                'error_category': ErrorCategory.NETWORK,
                'strategy_used': 'strategy2',
                'success': False,
                'context': {}
            },
            {
                'timestamp': datetime.now(),
                'error_category': ErrorCategory.STORAGE,
                'strategy_used': 'strategy3',
                'success': True,
                'context': {}
            }
        ]
        
        stats = self.recovery_manager.get_recovery_statistics()
        
        assert stats['total_attempts'] == 3
        assert stats['successful_attempts'] == 2
        assert stats['success_rate'] == 2/3
        assert 'network' in stats['by_category']
        assert 'storage' in stats['by_category']
        assert stats['by_category']['network']['attempts'] == 2
        assert stats['by_category']['network']['successes'] == 1


class TestResilientOperationDecorator:
    """Test resilient operation decorator"""
    
    def setup_method(self):
        """Setup test fixtures"""
        self.logger = Mock(spec=logging.Logger)
        self.error_handler = ErrorHandler(self.logger)
    
    def test_resilient_operation_success(self):
        """Test resilient operation with successful execution"""
        @resilient_operation(self.error_handler, component="test_component")
        def test_function(x):
            return x * 2
        
        result = test_function(5)
        assert result == 10
    
    def test_resilient_operation_with_retries(self):
        """Test resilient operation with retries"""
        call_count = 0
        
        @resilient_operation(self.error_handler, max_attempts=3, component="test_component")
        def flaky_function():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise ConnectionError("Temporary failure")
            return "success"
        
        with patch('time.sleep'):  # Mock sleep to speed up test
            result = flaky_function()
        
        assert result == "success"
        assert call_count == 3
    
    def test_resilient_operation_circuit_breaker(self):
        """Test resilient operation respects circuit breaker"""
        # Open the circuit breaker
        for i in range(5):
            self.error_handler.update_circuit_breaker("test_component", False)
        
        @resilient_operation(self.error_handler, fallback_value="circuit_open", component="test_component")
        def test_function():
            return "should_not_execute"
        
        result = test_function()
        assert result == "circuit_open"
    
    def test_resilient_operation_fallback_on_failure(self):
        """Test resilient operation returns fallback on complete failure"""
        @resilient_operation(self.error_handler, max_attempts=2, fallback_value="fallback", component="test_component")
        def always_failing_function():
            raise ValueError("Always fails")
        
        with patch('time.sleep'):  # Mock sleep to speed up test
            result = always_failing_function()
        
        assert result == "fallback"


class TestAdvancedErrorScenarios:
    """Test advanced error handling scenarios"""
    
    def setup_method(self):
        """Setup test fixtures"""
        self.logger = Mock(spec=logging.Logger)
        self.error_handler = ErrorHandler(self.logger)
    
    def test_component_specific_error_tracking(self):
        """Test error tracking per component"""
        # Add errors for different components
        error1 = ValueError("Component A error")
        error2 = ConnectionError("Component B error")
        error3 = ValueError("Another Component A error")
        
        self.error_handler.handle_error(error1, {'component': 'component_a'}, raise_on_critical=False)
        self.error_handler.handle_error(error2, {'component': 'component_b'}, raise_on_critical=False)
        self.error_handler.handle_error(error3, {'component': 'component_a'}, raise_on_critical=False)
        
        # Check component-specific continuation logic
        assert self.error_handler.should_continue_processing(max_errors=5, component='component_a')
        assert self.error_handler.should_continue_processing(max_errors=1, component='component_b')
        assert not self.error_handler.should_continue_processing(max_errors=1, component='component_a')
    
    def test_error_categorization_with_context(self):
        """Test error categorization includes context information"""
        context = {
            'component': 'whatsapp_extractor',
            'operation': 'message_download',
            'message_id': 'msg_123',
            'user_id': 'user_456'
        }
        
        error = requests.exceptions.Timeout("Request timeout")
        error_info = self.error_handler.categorize_error(error, context)
        
        assert error_info.category == ErrorCategory.NETWORK
        assert error_info.context == context
        assert error_info.component == 'whatsapp_extractor'
    
    def test_user_friendly_error_messages(self):
        """Test user-friendly error message generation"""
        # Test authentication error
        auth_error = requests.exceptions.HTTPError()
        auth_error.response = Mock()
        auth_error.response.status_code = 401
        
        error_info = self.error_handler.categorize_error(auth_error)
        
        assert "Authentication failed" in error_info.message
        assert "check your credentials" in error_info.message.lower()
        assert "troubleshooting suggestions" in error_info.message.lower()
    
    def test_error_recovery_strategies(self):
        """Test custom error recovery strategies"""
        recovery_called = False
        
        def custom_recovery_strategy(error_info: ErrorInfo) -> bool:
            nonlocal recovery_called
            recovery_called = True
            return True
        
        self.error_handler.register_recovery_strategy(ErrorCategory.NETWORK, custom_recovery_strategy)
        
        # Create a network error
        error_info = ErrorInfo(
            category=ErrorCategory.NETWORK,
            severity=ErrorSeverity.MEDIUM,
            message="Network error"
        )
        
        # Attempt recovery
        success = self.error_handler.attempt_recovery(error_info)
        
        assert success is True
        assert recovery_called is True
    
    def test_exponential_backoff_with_jitter(self):
        """Test exponential backoff calculation with jitter"""
        retry_config = RetryConfig(base_delay=1.0, exponential_base=2.0, jitter=True)
        
        # Test multiple delay calculations
        delays = [retry_config.get_delay(i) for i in range(5)]
        
        # Delays should generally increase (allowing for jitter variation)
        # Base delays would be: 1, 2, 4, 8, 16
        # With jitter, they should be between 50% and 100% of base
        assert 0.5 <= delays[0] <= 1.0
        assert 1.0 <= delays[1] <= 2.0
        assert 2.0 <= delays[2] <= 4.0
    
    def test_error_history_management(self):
        """Test error history management and cleanup"""
        # Add many errors
        for i in range(15):
            error = ValueError(f"Error {i}")
            self.error_handler.handle_error(error, {'index': i}, raise_on_critical=False)
        
        # Check error summary
        summary = self.error_handler.get_error_summary()
        assert summary['total_errors'] == 15
        assert len(summary['recent_errors']) == 10  # Should limit to 10 recent
        
        # Clear history
        self.error_handler.clear_error_history()
        assert len(self.error_handler.error_history) == 0
        
        new_summary = self.error_handler.get_error_summary()
        assert new_summary['total_errors'] == 0