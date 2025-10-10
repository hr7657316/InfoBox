"""
Integration tests for error handling across pipeline components
"""

import pytest
import tempfile
import shutil
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path
import requests
import imaplib

from pipeline.main import PipelineOrchestrator
from pipeline.whatsapp.whatsapp_extractor import WhatsAppExtractor
from pipeline.email.email_extractor import EmailExtractor
from pipeline.utils.error_handler import (
    ErrorHandler, ErrorCategory, BatchErrorHandler, ErrorRecoveryManager,
    graceful_degradation, resilient_operation
)
from pipeline.utils.config import ConfigManager
from pipeline.utils.storage import StorageManager


class TestPipelineErrorIntegration:
    """Test error handling integration across pipeline components"""
    
    def setup_method(self):
        """Setup test fixtures"""
        self.temp_dir = tempfile.mkdtemp()
        self.config_path = Path(self.temp_dir) / "test_config.yaml"
        
        # Create minimal test configuration
        test_config = """
logging:
  log_level: INFO
  console_output: true
  file_output: false

storage:
  base_path: {temp_dir}/data

whatsapp:
  api_type: twilio
  twilio_account_sid: test_sid
  twilio_auth_token: test_token
  twilio_phone_number: +1234567890

email:
  accounts:
    - email: test@example.com
      password: test_password
      imap_server: imap.example.com
      auth_method: password
""".format(temp_dir=self.temp_dir)
        
        with open(self.config_path, 'w') as f:
            f.write(test_config)
    
    def teardown_method(self):
        """Cleanup test fixtures"""
        shutil.rmtree(self.temp_dir)
    
    def test_orchestrator_initialization_error_handling(self):
        """Test error handling during orchestrator initialization"""
        # Test with invalid config path
        orchestrator = PipelineOrchestrator("nonexistent_config.yaml")
        
        # Should handle missing config gracefully
        result = orchestrator.initialize()
        assert result is False
    
    def test_orchestrator_partial_extractor_failure(self):
        """Test orchestrator handles partial extractor failures gracefully"""
        orchestrator = PipelineOrchestrator(str(self.config_path))
        
        # Mock successful initialization but failing extractors
        with patch.object(orchestrator, '_setup_extractors') as mock_setup:
            # Simulate WhatsApp extractor failure but email success
            mock_whatsapp = Mock(spec=WhatsAppExtractor)
            mock_whatsapp.authenticate.side_effect = Exception("WhatsApp API unavailable")
            
            mock_email = Mock(spec=EmailExtractor)
            mock_email.authenticate.return_value = True
            mock_email.extract_emails.return_value = []
            
            orchestrator.whatsapp_extractor = mock_whatsapp
            orchestrator.email_extractors = [mock_email]
            
            # Should initialize successfully
            assert orchestrator.initialize()
            
            # Run extraction - should handle WhatsApp failure gracefully
            results = orchestrator.run_extraction()
            
            # Should have results for both sources
            assert 'whatsapp' in results
            assert 'email' in results
            
            # WhatsApp should have failed
            assert results['whatsapp'].success is False
            assert len(results['whatsapp'].errors) > 0
            
            # Email should have succeeded (even with no data)
            assert results['email'].success is True
    
    def test_whatsapp_extractor_network_error_recovery(self):
        """Test WhatsApp extractor recovers from network errors"""
        config = {
            'api_type': 'twilio',
            'twilio_account_sid': 'test_sid',
            'twilio_auth_token': 'test_token',
            'twilio_phone_number': '+1234567890'
        }
        
        extractor = WhatsAppExtractor(config)
        
        # Mock network failure followed by success
        with patch('requests.Session.get') as mock_get:
            mock_response = Mock()
            mock_response.status_code = 200
            mock_response.json.return_value = {'status': 'active'}
            
            # First call fails, second succeeds
            mock_get.side_effect = [
                requests.exceptions.ConnectionError("Network error"),
                mock_response
            ]
            
            with patch('time.sleep'):  # Speed up test
                # Should eventually succeed after retry
                result = extractor.authenticate()
                assert result is True
                
                # Should have made 2 attempts
                assert mock_get.call_count == 2
    
    def test_email_extractor_authentication_error_handling(self):
        """Test email extractor handles authentication errors properly"""
        config = {
            'accounts': [
                {
                    'email': 'test@example.com',
                    'password': 'wrong_password',
                    'imap_server': 'imap.example.com',
                    'auth_method': 'password'
                }
            ]
        }
        
        extractor = EmailExtractor(config)
        
        # Mock IMAP authentication failure
        with patch('imaplib.IMAP4_SSL') as mock_imap:
            mock_connection = Mock()
            mock_connection.login.side_effect = imaplib.IMAP4.error("Authentication failed")
            mock_imap.return_value = mock_connection
            
            # Should handle auth failure gracefully
            result = extractor.authenticate()
            assert result is False
            
            # Should have error in history
            assert len(extractor.error_handler.error_history) > 0
            error = extractor.error_handler.error_history[0]
            assert error.category == ErrorCategory.AUTHENTICATION
    
    def test_storage_error_graceful_degradation(self):
        """Test storage errors are handled gracefully"""
        # Create storage manager with invalid path
        storage_manager = StorageManager("/invalid/readonly/path")
        
        # Should handle directory creation errors
        with patch('pathlib.Path.mkdir', side_effect=PermissionError("Permission denied")):
            # Should not raise exception
            try:
                paths = storage_manager.get_storage_paths('test', '2023-01-01')
                # Should return paths even if creation failed
                assert 'base' in paths
            except Exception as e:
                pytest.fail(f"Storage manager should handle errors gracefully: {e}")
    
    def test_media_download_error_recovery(self):
        """Test media download error recovery and graceful degradation"""
        config = {
            'api_type': 'twilio',
            'twilio_account_sid': 'test_sid',
            'twilio_auth_token': 'test_token'
        }
        
        extractor = WhatsAppExtractor(config)
        extractor._authenticated = True
        
        # Mock failed media download
        with patch.object(extractor, '_make_authenticated_request') as mock_request:
            # First attempt fails, second succeeds
            mock_response_fail = Mock()
            mock_response_fail.status_code = 404
            
            mock_response_success = Mock()
            mock_response_success.status_code = 200
            mock_response_success.iter_content.return_value = [b'test_data']
            
            mock_request.side_effect = [mock_response_fail, mock_response_success]
            
            with patch('builtins.open', create=True) as mock_open:
                mock_file = Mock()
                mock_open.return_value.__enter__.return_value = mock_file
                
                with patch('os.makedirs'), patch('os.path.exists', return_value=False):
                    with patch('time.sleep'):  # Speed up test
                        # Should eventually succeed after retry
                        result = extractor.download_media(
                            "http://example.com/media.jpg",
                            "test_media.jpg",
                            self.temp_dir
                        )
                        
                        # Should succeed on retry
                        assert result is not None
                        assert mock_request.call_count == 2
    
    def test_configuration_validation_error_handling(self):
        """Test configuration validation error handling"""
        # Create config with missing required fields
        invalid_config_path = Path(self.temp_dir) / "invalid_config.yaml"
        invalid_config = """
logging:
  log_level: INFO

# Missing storage and data source configurations
"""
        
        with open(invalid_config_path, 'w') as f:
            f.write(invalid_config)
        
        orchestrator = PipelineOrchestrator(str(invalid_config_path))
        
        # Should handle invalid configuration gracefully
        result = orchestrator.initialize()
        assert result is False
        
        # Should have logged configuration errors
        assert orchestrator.error_handler is not None
        assert len(orchestrator.error_handler.error_history) > 0
    
    def test_concurrent_error_handling(self):
        """Test error handling with concurrent operations"""
        error_handler = ErrorHandler()
        
        # Simulate multiple concurrent operations with errors
        errors = []
        
        def failing_operation(operation_id):
            try:
                if operation_id % 2 == 0:
                    raise ValueError(f"Operation {operation_id} failed")
                return f"Success {operation_id}"
            except Exception as e:
                error_handler.handle_error(e, {
                    'component': 'test',
                    'operation_id': operation_id
                }, raise_on_critical=False)
                errors.append(operation_id)
                return None
        
        # Run multiple operations
        results = []
        for i in range(10):
            result = failing_operation(i)
            if result:
                results.append(result)
        
        # Should have handled errors for even-numbered operations
        assert len(errors) == 5  # Operations 0, 2, 4, 6, 8
        assert len(results) == 5  # Operations 1, 3, 5, 7, 9
        assert len(error_handler.error_history) == 5
    
    def test_error_threshold_circuit_breaker(self):
        """Test circuit breaker pattern with error thresholds"""
        error_handler = ErrorHandler()
        
        # Simulate operations that start failing
        operation_count = 0
        
        def unreliable_operation():
            nonlocal operation_count
            operation_count += 1
            
            # Start failing after 5 operations
            if operation_count > 5:
                raise ConnectionError("Service degraded")
            return "success"
        
        # Run operations until circuit breaker should trigger
        successful_operations = 0
        for i in range(15):
            try:
                result = error_handler.with_retry(
                    unreliable_operation,
                    category=ErrorCategory.NETWORK
                )
                successful_operations += 1
            except Exception:
                pass
            
            # Check if we should stop processing
            if not error_handler.should_continue_processing(max_errors=8):
                break
        
        # Should have stopped before processing all operations
        assert operation_count < 15
        assert successful_operations == 5  # Only first 5 should succeed
        assert len(error_handler.error_history) >= 8  # Should hit error threshold
    
    def test_error_recovery_after_service_restoration(self):
        """Test error recovery when service is restored"""
        error_handler = ErrorHandler()
        
        # Simulate service that goes down and comes back up
        service_down = True
        call_count = 0
        
        def service_call():
            nonlocal service_down, call_count
            call_count += 1
            
            # Service comes back up after 10 calls
            if call_count > 10:
                service_down = False
            
            if service_down:
                raise ConnectionError("Service unavailable")
            return "service_restored"
        
        # Keep trying until service is restored
        max_attempts = 20
        for attempt in range(max_attempts):
            try:
                result = error_handler.with_retry(
                    service_call,
                    category=ErrorCategory.NETWORK
                )
                # If we get here, service is restored
                assert result == "service_restored"
                break
            except Exception:
                # Service still down, continue trying
                continue
        else:
            pytest.fail("Service should have been restored within max_attempts")
        
        # Should have eventually succeeded
        assert call_count > 10
        assert not service_down


class TestErrorReportingAndLogging:
    """Test error reporting and logging functionality"""
    
    def setup_method(self):
        """Setup test fixtures"""
        self.temp_dir = tempfile.mkdtemp()
    
    def teardown_method(self):
        """Cleanup test fixtures"""
        shutil.rmtree(self.temp_dir)
    
    def test_error_summary_generation(self):
        """Test comprehensive error summary generation"""
        error_handler = ErrorHandler()
        
        # Generate various types of errors
        errors = [
            ValueError("Data error 1"),
            requests.exceptions.ConnectionError("Network error 1"),
            PermissionError("Storage error 1"),
            ValueError("Data error 2"),
            requests.exceptions.HTTPError("API error 1"),
        ]
        
        for error in errors:
            error_handler.handle_error(error, raise_on_critical=False)
        
        summary = error_handler.get_error_summary()
        
        # Verify summary structure
        assert summary['total_errors'] == 5
        assert 'by_category' in summary
        assert 'by_severity' in summary
        assert 'recent_errors' in summary
        
        # Verify categorization
        assert summary['by_category']['data_processing'] == 2  # 2 ValueErrors
        assert summary['by_category']['network'] >= 1  # At least 1 network error
        assert summary['by_category']['storage'] == 1  # 1 PermissionError
    
    def test_error_context_preservation(self):
        """Test error context is preserved through the pipeline"""
        error_handler = ErrorHandler()
        
        context = {
            'component': 'whatsapp_extractor',
            'operation': 'message_extraction',
            'account_id': 'test_account',
            'message_id': 'msg_123'
        }
        
        error = requests.exceptions.Timeout("Request timeout")
        error_info = error_handler.handle_error(error, context, raise_on_critical=False)
        
        # Verify context is preserved
        assert error_info.context == context
        assert error_info.component == 'whatsapp_extractor'
        
        # Verify context is included in error dictionary
        error_dict = error_info.to_dict()
        assert error_dict['context'] == context


if __name__ == "__main__":
    pytest.main([__file__])


class TestAdvancedErrorIntegration:
    """Test advanced error handling integration scenarios"""
    
    def setup_method(self):
        """Setup test fixtures"""
        self.temp_dir = tempfile.mkdtemp()
        self.error_handler = ErrorHandler()
        self.batch_handler = BatchErrorHandler(self.error_handler)
        self.recovery_manager = ErrorRecoveryManager(self.error_handler)
    
    def teardown_method(self):
        """Cleanup test fixtures"""
        shutil.rmtree(self.temp_dir)
    
    def test_pipeline_with_circuit_breaker_integration(self):
        """Test pipeline integration with circuit breaker functionality"""
        from pipeline.utils.error_handler import create_pipeline_error_handler, resilient_operation
        
        error_handler = create_pipeline_error_handler()
        failure_count = 0
        
        @resilient_operation(error_handler, max_attempts=2, fallback_value=None, component="test_extractor")
        def flaky_extractor_operation():
            nonlocal failure_count
            failure_count += 1
            if failure_count <= 6:  # Fail enough times to open circuit breaker
                raise ConnectionError("Service unavailable")
            return "success"
        
        results = []
        
        # First few calls should fail and eventually open circuit breaker
        for i in range(10):
            with patch('time.sleep'):  # Speed up test
                result = flaky_extractor_operation()
                results.append(result)
        
        # Should have some None results due to circuit breaker
        none_results = [r for r in results if r is None]
        assert len(none_results) > 0, "Circuit breaker should have prevented some calls"
    
    def test_batch_processing_with_recovery_strategies(self):
        """Test batch processing with custom recovery strategies"""
        items = ['item1', 'item2', 'item3', 'item4', 'item5']
        processing_attempts = {}
        
        def flaky_processor(item):
            if item not in processing_attempts:
                processing_attempts[item] = 0
            processing_attempts[item] += 1
            
            # Simulate intermittent failures
            if item in ['item2', 'item4'] and processing_attempts[item] == 1:
                raise ConnectionError(f"Temporary failure for {item}")
            
            return f"processed_{item}"
        
        # Register recovery strategy
        def network_recovery(error_info: ErrorInfo) -> bool:
            # Simulate network recovery by waiting
            time.sleep(0.1)
            return True
        
        self.error_handler.register_recovery_strategy(ErrorCategory.NETWORK, network_recovery)
        
        # Process batch
        result = self.batch_handler.process_batch(
            items, 
            flaky_processor,
            context={'component': 'batch_processor'}
        )
        
        # Should have some failures initially
        assert result['failed_count'] > 0
        
        # Retry failed items
        retry_result = self.batch_handler.retry_failed_items(
            result, 
            flaky_processor,
            context={'component': 'batch_processor'},
            max_retries=2
        )
        
        # After retry, should have better success rate
        assert retry_result['success_rate'] > result['success_rate']
    
    def test_multi_component_error_isolation(self):
        """Test error isolation between different pipeline components"""
        components = ['whatsapp_extractor', 'email_extractor', 'storage_manager']
        
        # Simulate different error patterns for each component
        for i, component in enumerate(components):
            # Each component gets different number of errors
            for j in range((i + 1) * 2):
                error = ValueError(f"Error {j} in {component}")
                self.error_handler.handle_error(error, {
                    'component': component,
                    'operation': f'operation_{j}'
                }, raise_on_critical=False)
        
        # Check component-specific error tracking
        assert self.error_handler.should_continue_processing(max_errors=3, component='whatsapp_extractor')
        assert not self.error_handler.should_continue_processing(max_errors=3, component='email_extractor')
        assert not self.error_handler.should_continue_processing(max_errors=3, component='storage_manager')
        
        # Global error count should still allow processing
        assert self.error_handler.should_continue_processing(max_errors=15)
    
    def test_fallback_strategy_chaining(self):
        """Test chaining multiple fallback strategies"""
        # Register multiple fallback strategies
        def primary_fallback(*args, **kwargs):
            raise ValueError("Primary fallback also failed")
        
        def secondary_fallback(*args, **kwargs):
            return "secondary_fallback_success"
        
        self.recovery_manager.register_fallback_strategy(
            ErrorCategory.NETWORK, 
            "primary", 
            primary_fallback
        )
        self.recovery_manager.register_fallback_strategy(
            ErrorCategory.NETWORK, 
            "secondary", 
            secondary_fallback
        )
        
        def failing_function():
            raise ConnectionError("Primary function failed")
        
        # Should try primary fallback, fail, then try secondary and succeed
        result = self.recovery_manager.execute_with_fallback(
            failing_function,
            ErrorCategory.NETWORK
        )
        
        assert result == "secondary_fallback_success"
        
        # Check recovery history
        stats = self.recovery_manager.get_recovery_statistics()
        assert stats['total_attempts'] == 1
        assert stats['successful_attempts'] == 1
    
    def test_error_context_propagation(self):
        """Test error context propagation through the pipeline"""
        context_chain = []
        
        def context_tracking_processor(item):
            # Simulate nested operations with context propagation
            try:
                if item == 'fail_item':
                    raise ValueError("Simulated processing error")
                return f"processed_{item}"
            except Exception as e:
                # Add context and re-raise
                enhanced_context = {
                    'component': 'processor',
                    'operation': 'item_processing',
                    'item': item,
                    'processing_stage': 'validation'
                }
                error_info = self.error_handler.handle_error(e, enhanced_context, raise_on_critical=False)
                context_chain.append(error_info.context)
                raise
        
        items = ['good_item', 'fail_item', 'another_good_item']
        
        # Process items and collect context
        for item in items:
            try:
                context_tracking_processor(item)
            except ValueError:
                pass  # Expected for fail_item
        
        # Verify context was captured
        assert len(context_chain) == 1
        captured_context = context_chain[0]
        assert captured_context['component'] == 'processor'
        assert captured_context['item'] == 'fail_item'
        assert captured_context['processing_stage'] == 'validation'
    
    def test_graceful_degradation_with_partial_success(self):
        """Test graceful degradation maintains partial success"""
        from pipeline.utils.error_handler import graceful_degradation
        
        successful_operations = []
        failed_operations = []
        
        @graceful_degradation(self.error_handler, fallback_value=None)
        def operation_with_partial_failure(operation_id):
            if operation_id % 3 == 0:  # Every third operation fails
                failed_operations.append(operation_id)
                raise RuntimeError(f"Operation {operation_id} failed")
            
            successful_operations.append(operation_id)
            return f"result_{operation_id}"
        
        # Run multiple operations
        results = []
        for i in range(10):
            result = operation_with_partial_failure(i)
            results.append(result)
        
        # Should have mix of successful results and None (failed)
        successful_results = [r for r in results if r is not None]
        failed_results = [r for r in results if r is None]
        
        assert len(successful_results) > 0
        assert len(failed_results) > 0
        assert len(successful_operations) == len(successful_results)
        assert len(failed_operations) == len(failed_results)
    
    def test_error_rate_monitoring_and_alerting(self):
        """Test error rate monitoring for alerting thresholds"""
        # Simulate operations with varying error rates
        operations_per_minute = 60
        error_threshold = 0.1  # 10% error rate threshold
        
        errors_in_window = 0
        total_operations = 0
        
        for minute in range(5):  # Simulate 5 minutes
            for operation in range(operations_per_minute):
                total_operations += 1
                
                # Simulate increasing error rate over time
                error_probability = minute * 0.05  # 0%, 5%, 10%, 15%, 20%
                
                if operation < operations_per_minute * error_probability:
                    # This operation fails
                    error = RuntimeError(f"Operation failed in minute {minute}")
                    self.error_handler.handle_error(error, {
                        'component': 'test_service',
                        'minute': minute,
                        'operation': operation
                    }, raise_on_critical=False)
                    errors_in_window += 1
        
        # Check if error rate exceeds threshold
        error_rate = errors_in_window / total_operations
        
        # Should detect high error rate in later minutes
        assert error_rate > error_threshold
        
        # Verify error tracking
        summary = self.error_handler.get_error_summary()
        assert summary['total_errors'] == errors_in_window
    
    def test_resource_cleanup_on_errors(self):
        """Test proper resource cleanup when errors occur"""
        cleanup_called = []
        
        class MockResource:
            def __init__(self, resource_id):
                self.resource_id = resource_id
                self.closed = False
            
            def close(self):
                self.closed = True
                cleanup_called.append(self.resource_id)
        
        def operation_with_resource_cleanup():
            resources = [MockResource(i) for i in range(3)]
            
            try:
                # Simulate operation that fails
                raise ConnectionError("Operation failed")
            
            except Exception as e:
                # Ensure cleanup happens even on error
                for resource in resources:
                    resource.close()
                
                # Re-raise after cleanup
                raise e
        
        # Test that cleanup happens on error
        with pytest.raises(ConnectionError):
            operation_with_resource_cleanup()
        
        # Verify all resources were cleaned up
        assert len(cleanup_called) == 3
        assert cleanup_called == [0, 1, 2]
    
    def test_error_correlation_and_root_cause_analysis(self):
        """Test error correlation for root cause analysis"""
        # Simulate correlated errors (same root cause)
        root_cause_id = "network_outage_001"
        
        correlated_errors = [
            ("whatsapp_extractor", "message_fetch", "Connection timeout"),
            ("whatsapp_extractor", "media_download", "Connection timeout"),
            ("email_extractor", "imap_connect", "Connection timeout"),
            ("storage_manager", "remote_backup", "Connection timeout")
        ]
        
        # Add correlated errors with same root cause identifier
        for component, operation, message in correlated_errors:
            error = ConnectionError(message)
            self.error_handler.handle_error(error, {
                'component': component,
                'operation': operation,
                'root_cause_id': root_cause_id,
                'timestamp': datetime.now().isoformat()
            }, raise_on_critical=False)
        
        # Analyze error patterns
        summary = self.error_handler.get_error_summary()
        
        # Should detect pattern of network errors across components
        assert summary['by_category']['network'] == len(correlated_errors)
        
        # Check that all errors have the same root cause context
        root_cause_errors = [
            error for error in self.error_handler.error_history
            if error.context.get('root_cause_id') == root_cause_id
        ]
        
        assert len(root_cause_errors) == len(correlated_errors)


class TestErrorHandlingPerformance:
    """Test error handling performance and overhead"""
    
    def setup_method(self):
        """Setup test fixtures"""
        self.error_handler = ErrorHandler()
    
    def test_error_handling_overhead(self):
        """Test that error handling doesn't add significant overhead"""
        import time
        
        # Measure time for operations without error handling
        start_time = time.time()
        for i in range(1000):
            result = i * 2  # Simple operation
        baseline_time = time.time() - start_time
        
        # Measure time for operations with error handling
        @graceful_degradation(self.error_handler, fallback_value=0)
        def operation_with_error_handling(x):
            return x * 2
        
        start_time = time.time()
        for i in range(1000):
            result = operation_with_error_handling(i)
        error_handling_time = time.time() - start_time
        
        # Error handling overhead should be minimal (less than 50% increase)
        overhead_ratio = error_handling_time / baseline_time
        assert overhead_ratio < 1.5, f"Error handling overhead too high: {overhead_ratio:.2f}x"
    
    def test_error_history_memory_usage(self):
        """Test error history doesn't consume excessive memory"""
        import sys
        
        # Measure initial memory usage
        initial_size = sys.getsizeof(self.error_handler.error_history)
        
        # Add many errors
        for i in range(1000):
            error = ValueError(f"Error {i}")
            self.error_handler.handle_error(error, {'index': i}, raise_on_critical=False)
        
        # Measure memory usage after adding errors
        final_size = sys.getsizeof(self.error_handler.error_history)
        
        # Memory growth should be reasonable (less than 1MB for 1000 errors)
        memory_growth = final_size - initial_size
        assert memory_growth < 1024 * 1024, f"Excessive memory usage: {memory_growth} bytes"
    
    def test_concurrent_error_handling(self):
        """Test error handling under concurrent access"""
        import threading
        import time
        
        errors_handled = []
        
        def worker_thread(thread_id):
            for i in range(100):
                try:
                    if i % 10 == 0:  # Every 10th operation fails
                        raise ValueError(f"Thread {thread_id} error {i}")
                    # Simulate work
                    time.sleep(0.001)
                except ValueError as e:
                    error_info = self.error_handler.handle_error(e, {
                        'thread_id': thread_id,
                        'operation': i
                    }, raise_on_critical=False)
                    errors_handled.append(error_info)
        
        # Start multiple threads
        threads = []
        for thread_id in range(5):
            thread = threading.Thread(target=worker_thread, args=(thread_id,))
            threads.append(thread)
            thread.start()
        
        # Wait for all threads to complete
        for thread in threads:
            thread.join()
        
        # Verify all errors were handled correctly
        expected_errors = 5 * 10  # 5 threads * 10 errors per thread
        assert len(self.error_handler.error_history) == expected_errors
        
        # Verify thread safety - no duplicate or missing errors
        thread_error_counts = {}
        for error_info in self.error_handler.error_history:
            thread_id = error_info.context['thread_id']
            thread_error_counts[thread_id] = thread_error_counts.get(thread_id, 0) + 1
        
        # Each thread should have exactly 10 errors
        for thread_id in range(5):
            assert thread_error_counts[thread_id] == 10