"""
Comprehensive error handling system for the extraction pipeline

Provides error categorization, recovery mechanisms, retry logic, and graceful degradation.
"""

import time
import logging
from typing import Dict, List, Optional, Any, Callable, Type, Union
from datetime import datetime
from enum import Enum
from dataclasses import dataclass, field
from functools import wraps
import traceback
import requests
import imaplib
import socket
import ssl


class ErrorCategory(Enum):
    """Categories of errors that can occur in the pipeline"""
    AUTHENTICATION = "authentication"
    NETWORK = "network"
    API_RATE_LIMIT = "api_rate_limit"
    DATA_PROCESSING = "data_processing"
    STORAGE = "storage"
    CONFIGURATION = "configuration"
    VALIDATION = "validation"
    UNKNOWN = "unknown"


class ErrorSeverity(Enum):
    """Severity levels for errors"""
    LOW = "low"          # Warning, can continue
    MEDIUM = "medium"    # Error, retry possible
    HIGH = "high"        # Critical error, stop current operation
    CRITICAL = "critical"  # Fatal error, stop entire pipeline


@dataclass
class ErrorInfo:
    """Detailed information about an error"""
    category: ErrorCategory
    severity: ErrorSeverity
    message: str
    original_exception: Optional[Exception] = None
    context: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.now)
    component: str = "unknown"
    retry_count: int = 0
    max_retries: int = 3
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert error info to dictionary for logging"""
        return {
            'category': self.category.value,
            'severity': self.severity.value,
            'message': self.message,
            'exception_type': type(self.original_exception).__name__ if self.original_exception else None,
            'exception_message': str(self.original_exception) if self.original_exception else None,
            'context': self.context,
            'timestamp': self.timestamp.isoformat(),
            'component': self.component,
            'retry_count': self.retry_count,
            'max_retries': self.max_retries
        }


@dataclass
class RetryConfig:
    """Configuration for retry logic"""
    max_retries: int = 3
    base_delay: float = 1.0
    max_delay: float = 60.0
    exponential_base: float = 2.0
    jitter: bool = True
    
    def get_delay(self, attempt: int) -> float:
        """Calculate delay for given attempt number"""
        delay = min(self.base_delay * (self.exponential_base ** attempt), self.max_delay)
        
        if self.jitter:
            import random
            delay *= (0.5 + random.random() * 0.5)  # Add 0-50% jitter
        
        return delay


class PipelineError(Exception):
    """Base exception class for pipeline errors"""
    
    def __init__(self, error_info: ErrorInfo):
        self.error_info = error_info
        super().__init__(error_info.message)


class AuthenticationError(PipelineError):
    """Authentication-related errors"""
    pass


class NetworkError(PipelineError):
    """Network-related errors"""
    pass


class RateLimitError(PipelineError):
    """API rate limit errors"""
    pass


class DataProcessingError(PipelineError):
    """Data processing errors"""
    pass


class StorageError(PipelineError):
    """Storage-related errors"""
    pass


class ConfigurationError(PipelineError):
    """Configuration-related errors"""
    pass


class ValidationError(PipelineError):
    """Data validation errors"""
    pass


class ErrorHandler:
    """Comprehensive error handling and recovery system"""
    
    def __init__(self, logger: Optional[logging.Logger] = None):
        self.logger = logger or logging.getLogger(__name__)
        self.error_history: List[ErrorInfo] = []
        self.retry_configs: Dict[ErrorCategory, RetryConfig] = {
            ErrorCategory.NETWORK: RetryConfig(max_retries=3, base_delay=1.0),
            ErrorCategory.API_RATE_LIMIT: RetryConfig(max_retries=5, base_delay=2.0, max_delay=300.0),
            ErrorCategory.DATA_PROCESSING: RetryConfig(max_retries=2, base_delay=0.5),
            ErrorCategory.STORAGE: RetryConfig(max_retries=3, base_delay=1.0),
            ErrorCategory.AUTHENTICATION: RetryConfig(max_retries=2, base_delay=5.0),
        }
        self.circuit_breaker_state = {}  # Track circuit breaker states per component
        self.recovery_strategies = {}  # Custom recovery strategies per error type
    
    def categorize_error(self, exception: Exception, context: Dict[str, Any] = None) -> ErrorInfo:
        """
        Categorize an exception and create ErrorInfo
        
        Args:
            exception: The exception to categorize
            context: Additional context information
            
        Returns:
            ErrorInfo object with categorized error details
        """
        context = context or {}
        component = context.get('component', 'unknown')
        
        # Categorize based on exception type and message
        if isinstance(exception, (requests.exceptions.ConnectionError, 
                                socket.error, ssl.SSLError)):
            category = ErrorCategory.NETWORK
            severity = ErrorSeverity.MEDIUM
            message = self._get_user_friendly_message(ErrorCategory.NETWORK, str(exception))
            
        elif isinstance(exception, requests.exceptions.HTTPError):
            if hasattr(exception, 'response') and exception.response.status_code == 429:
                category = ErrorCategory.API_RATE_LIMIT
                severity = ErrorSeverity.MEDIUM
                message = "API rate limit exceeded. The system will automatically retry with delays."
            elif hasattr(exception, 'response') and exception.response.status_code in [401, 403]:
                category = ErrorCategory.AUTHENTICATION
                severity = ErrorSeverity.HIGH
                message = self._get_user_friendly_message(ErrorCategory.AUTHENTICATION, str(exception))
            else:
                category = ErrorCategory.NETWORK
                severity = ErrorSeverity.MEDIUM
                message = f"HTTP error occurred: {exception.response.status_code if hasattr(exception, 'response') else 'Unknown'}"
                
        elif isinstance(exception, (imaplib.IMAP4.error,)):
            if "authentication" in str(exception).lower() or "login" in str(exception).lower():
                category = ErrorCategory.AUTHENTICATION
                severity = ErrorSeverity.HIGH
                message = self._get_user_friendly_message(ErrorCategory.AUTHENTICATION, str(exception))
            else:
                category = ErrorCategory.NETWORK
                severity = ErrorSeverity.MEDIUM
                message = f"Email server error: {str(exception)}"
                
        elif isinstance(exception, (ValueError, TypeError, KeyError)):
            category = ErrorCategory.DATA_PROCESSING
            severity = ErrorSeverity.MEDIUM
            message = self._get_user_friendly_message(ErrorCategory.DATA_PROCESSING, str(exception))
            
        elif isinstance(exception, (OSError, IOError, PermissionError)):
            category = ErrorCategory.STORAGE
            severity = ErrorSeverity.MEDIUM
            message = self._get_user_friendly_message(ErrorCategory.STORAGE, str(exception))
            
        elif isinstance(exception, (FileNotFoundError, ImportError)):
            category = ErrorCategory.CONFIGURATION
            severity = ErrorSeverity.HIGH
            message = self._get_user_friendly_message(ErrorCategory.CONFIGURATION, str(exception))
            
        else:
            category = ErrorCategory.UNKNOWN
            severity = ErrorSeverity.MEDIUM
            message = f"Unexpected error occurred: {str(exception)}"
        
        return ErrorInfo(
            category=category,
            severity=severity,
            message=message,
            original_exception=exception,
            context=context,
            component=component
        )
    
    def _get_user_friendly_message(self, category: ErrorCategory, original_message: str) -> str:
        """
        Generate user-friendly error messages
        
        Args:
            category: Error category
            original_message: Original exception message
            
        Returns:
            User-friendly error message with troubleshooting hints
        """
        messages = {
            ErrorCategory.AUTHENTICATION: {
                "message": "Authentication failed. Please check your credentials.",
                "hints": [
                    "Verify your API tokens or passwords are correct",
                    "Check if your credentials have expired",
                    "Ensure you have the necessary permissions",
                    "For Gmail, make sure 2-factor authentication and app passwords are set up correctly"
                ]
            },
            ErrorCategory.NETWORK: {
                "message": "Network connection failed. Please check your internet connection.",
                "hints": [
                    "Verify your internet connection is stable",
                    "Check if the service is currently available",
                    "Try again in a few minutes",
                    "Check firewall settings if behind corporate network"
                ]
            },
            ErrorCategory.DATA_PROCESSING: {
                "message": "Data processing error occurred. Some data may be corrupted or in unexpected format.",
                "hints": [
                    "This item will be skipped and processing will continue",
                    "Check the logs for specific details",
                    "Verify the data source is providing valid data"
                ]
            },
            ErrorCategory.STORAGE: {
                "message": "File storage error occurred. Check disk space and permissions.",
                "hints": [
                    "Ensure you have sufficient disk space",
                    "Check file and directory permissions",
                    "Verify the output directory exists and is writable",
                    "Check if the file is already in use by another process"
                ]
            },
            ErrorCategory.CONFIGURATION: {
                "message": "Configuration error. Please check your setup.",
                "hints": [
                    "Verify all required configuration files exist",
                    "Check environment variables are set correctly",
                    "Ensure all required dependencies are installed",
                    "Review the configuration documentation"
                ]
            }
        }
        
        error_info = messages.get(category, {
            "message": "An error occurred during processing.",
            "hints": ["Check the logs for more details", "Try running the operation again"]
        })
        
        message = error_info["message"]
        if "hints" in error_info:
            hints_text = "\n".join([f"  • {hint}" for hint in error_info["hints"]])
            message += f"\n\nTroubleshooting suggestions:\n{hints_text}"
        
        return message
    
    def handle_error(self, exception: Exception, context: Dict[str, Any] = None, 
                    raise_on_critical: bool = True) -> ErrorInfo:
        """
        Handle an error with appropriate logging and categorization
        
        Args:
            exception: The exception to handle
            context: Additional context information
            raise_on_critical: Whether to re-raise critical errors
            
        Returns:
            ErrorInfo object
            
        Raises:
            PipelineError: If error is critical and raise_on_critical is True
        """
        error_info = self.categorize_error(exception, context)
        self.error_history.append(error_info)
        
        # Log the error with appropriate level
        if error_info.severity == ErrorSeverity.LOW:
            self.logger.warning(f"Warning in {error_info.component}: {error_info.message}")
        elif error_info.severity == ErrorSeverity.MEDIUM:
            self.logger.error(f"Error in {error_info.component}: {error_info.message}")
        elif error_info.severity in [ErrorSeverity.HIGH, ErrorSeverity.CRITICAL]:
            self.logger.error(f"Critical error in {error_info.component}: {error_info.message}")
            self.logger.debug(f"Error details: {error_info.to_dict()}")
            self.logger.debug(f"Traceback: {traceback.format_exc()}")
        
        # Raise appropriate pipeline exception for critical errors
        if raise_on_critical and error_info.severity in [ErrorSeverity.HIGH, ErrorSeverity.CRITICAL]:
            exception_class = self._get_exception_class(error_info.category)
            raise exception_class(error_info)
        
        return error_info
    
    def _get_exception_class(self, category: ErrorCategory) -> Type[PipelineError]:
        """Get appropriate exception class for error category"""
        exception_map = {
            ErrorCategory.AUTHENTICATION: AuthenticationError,
            ErrorCategory.NETWORK: NetworkError,
            ErrorCategory.API_RATE_LIMIT: RateLimitError,
            ErrorCategory.DATA_PROCESSING: DataProcessingError,
            ErrorCategory.STORAGE: StorageError,
            ErrorCategory.CONFIGURATION: ConfigurationError,
            ErrorCategory.VALIDATION: ValidationError,
        }
        return exception_map.get(category, PipelineError)
    
    def with_retry(self, func: Callable, *args, category: ErrorCategory = None, 
                  context: Dict[str, Any] = None, **kwargs) -> Any:
        """
        Execute function with retry logic and error handling
        
        Args:
            func: Function to execute
            *args: Function arguments
            category: Error category for retry configuration
            context: Additional context for error handling
            **kwargs: Function keyword arguments
            
        Returns:
            Function result
            
        Raises:
            PipelineError: If all retries are exhausted
        """
        context = context or {}
        retry_config = self.retry_configs.get(category, RetryConfig())
        last_error = None
        
        for attempt in range(retry_config.max_retries + 1):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                error_info = self.categorize_error(e, context)
                error_info.retry_count = attempt
                error_info.max_retries = retry_config.max_retries
                
                last_error = error_info
                
                # Don't retry for certain error types
                if error_info.category == ErrorCategory.AUTHENTICATION:
                    self.handle_error(e, context, raise_on_critical=True)
                
                if attempt < retry_config.max_retries:
                    delay = retry_config.get_delay(attempt)
                    self.logger.info(f"Retrying in {delay:.2f} seconds (attempt {attempt + 1}/{retry_config.max_retries})")
                    time.sleep(delay)
                else:
                    # All retries exhausted
                    self.logger.error(f"All {retry_config.max_retries} retries exhausted for {context.get('operation', 'operation')}")
                    self.handle_error(e, context, raise_on_critical=True)
        
        # This should not be reached, but just in case
        if last_error:
            exception_class = self._get_exception_class(last_error.category)
            raise exception_class(last_error)
    
    def create_retry_decorator(self, category: ErrorCategory = None, 
                             context: Dict[str, Any] = None):
        """
        Create a decorator for automatic retry functionality
        
        Args:
            category: Error category for retry configuration
            context: Additional context for error handling
            
        Returns:
            Decorator function
        """
        def decorator(func):
            @wraps(func)
            def wrapper(*args, **kwargs):
                return self.with_retry(func, *args, category=category, context=context, **kwargs)
            return wrapper
        return decorator
    
    def get_error_summary(self) -> Dict[str, Any]:
        """
        Get summary of all errors encountered
        
        Returns:
            Dictionary with error statistics and recent errors
        """
        if not self.error_history:
            return {"total_errors": 0, "by_category": {}, "by_severity": {}, "recent_errors": []}
        
        # Count by category
        by_category = {}
        for error in self.error_history:
            category = error.category.value
            by_category[category] = by_category.get(category, 0) + 1
        
        # Count by severity
        by_severity = {}
        for error in self.error_history:
            severity = error.severity.value
            by_severity[severity] = by_severity.get(severity, 0) + 1
        
        # Get recent errors (last 10)
        recent_errors = [error.to_dict() for error in self.error_history[-10:]]
        
        return {
            "total_errors": len(self.error_history),
            "by_category": by_category,
            "by_severity": by_severity,
            "recent_errors": recent_errors
        }
    
    def clear_error_history(self):
        """Clear the error history"""
        self.error_history.clear()
    
    def should_continue_processing(self, max_errors: int = 10, 
                                 critical_error_threshold: int = 3,
                                 component: str = None) -> bool:
        """
        Determine if processing should continue based on error history
        
        Args:
            max_errors: Maximum total errors before stopping
            critical_error_threshold: Maximum critical errors before stopping
            component: Specific component to check (if None, checks all)
            
        Returns:
            True if processing should continue, False otherwise
        """
        # Filter errors by component if specified
        if component:
            relevant_errors = [e for e in self.error_history if e.component == component]
        else:
            relevant_errors = self.error_history
        
        if len(relevant_errors) >= max_errors:
            return False
        
        critical_errors = sum(1 for error in relevant_errors 
                            if error.severity == ErrorSeverity.CRITICAL)
        
        return critical_errors < critical_error_threshold
    
    def register_recovery_strategy(self, category: ErrorCategory, 
                                 strategy: Callable[[ErrorInfo], bool]):
        """
        Register a custom recovery strategy for an error category
        
        Args:
            category: Error category
            strategy: Function that takes ErrorInfo and returns True if recovery succeeded
        """
        self.recovery_strategies[category] = strategy
    
    def attempt_recovery(self, error_info: ErrorInfo) -> bool:
        """
        Attempt to recover from an error using registered strategies
        
        Args:
            error_info: Error information
            
        Returns:
            True if recovery was successful, False otherwise
        """
        strategy = self.recovery_strategies.get(error_info.category)
        if strategy:
            try:
                return strategy(error_info)
            except Exception as e:
                self.logger.error(f"Recovery strategy failed for {error_info.category}: {e}")
                return False
        return False
    
    def get_circuit_breaker_state(self, component: str) -> Dict[str, Any]:
        """
        Get circuit breaker state for a component
        
        Args:
            component: Component name
            
        Returns:
            Circuit breaker state information
        """
        return self.circuit_breaker_state.get(component, {
            'state': 'closed',  # closed, open, half-open
            'failure_count': 0,
            'last_failure_time': None,
            'next_attempt_time': None
        })
    
    def update_circuit_breaker(self, component: str, success: bool):
        """
        Update circuit breaker state based on operation result
        
        Args:
            component: Component name
            success: Whether the operation was successful
        """
        if component not in self.circuit_breaker_state:
            self.circuit_breaker_state[component] = {
                'state': 'closed',
                'failure_count': 0,
                'last_failure_time': None,
                'next_attempt_time': None
            }
        
        state = self.circuit_breaker_state[component]
        
        if success:
            # Reset on success
            state['failure_count'] = 0
            state['state'] = 'closed'
            state['next_attempt_time'] = None
        else:
            # Increment failure count
            state['failure_count'] += 1
            state['last_failure_time'] = datetime.now()
            
            # Open circuit breaker if too many failures
            if state['failure_count'] >= 5:  # Configurable threshold
                state['state'] = 'open'
                # Set next attempt time (exponential backoff)
                backoff_seconds = min(60 * (2 ** (state['failure_count'] - 5)), 3600)  # Max 1 hour
                state['next_attempt_time'] = datetime.now().timestamp() + backoff_seconds
                
                self.logger.warning(f"Circuit breaker opened for {component}, next attempt in {backoff_seconds}s")
    
    def is_circuit_breaker_open(self, component: str) -> bool:
        """
        Check if circuit breaker is open for a component
        
        Args:
            component: Component name
            
        Returns:
            True if circuit breaker is open (should not attempt operation)
        """
        state = self.get_circuit_breaker_state(component)
        
        if state['state'] == 'closed':
            return False
        elif state['state'] == 'open':
            # Check if we should try again (half-open state)
            if state['next_attempt_time'] and datetime.now().timestamp() >= state['next_attempt_time']:
                self.circuit_breaker_state[component]['state'] = 'half-open'
                return False
            return True
        elif state['state'] == 'half-open':
            return False
        
        return False


def with_error_handling(error_handler: ErrorHandler, category: ErrorCategory = None,
                       context: Dict[str, Any] = None, raise_on_error: bool = False):
    """
    Decorator for adding error handling to functions
    
    Args:
        error_handler: ErrorHandler instance
        category: Error category for retry configuration
        context: Additional context for error handling
        raise_on_error: Whether to raise errors or return None on failure
        
    Returns:
        Decorator function
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                error_info = error_handler.handle_error(e, context, raise_on_critical=raise_on_error)
                if raise_on_error:
                    raise
                return None
        return wrapper
    return decorator


def graceful_degradation(error_handler: ErrorHandler, fallback_value: Any = None,
                        log_errors: bool = True):
    """
    Decorator for graceful degradation - continue processing even if function fails
    
    Args:
        error_handler: ErrorHandler instance
        fallback_value: Value to return on error
        log_errors: Whether to log errors
        
    Returns:
        Decorator function
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except Exception as e:
                if log_errors:
                    error_handler.handle_error(e, raise_on_critical=False)
                return fallback_value
        return wrapper
    return decorator


class BatchErrorHandler:
    """Specialized error handler for batch operations with partial failure support"""
    
    def __init__(self, error_handler: ErrorHandler, max_failures_per_batch: int = 5):
        self.error_handler = error_handler
        self.max_failures_per_batch = max_failures_per_batch
        self.batch_results = []
        self.batch_errors = []
    
    def process_batch(self, items: List[Any], processor_func: Callable, 
                     context: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Process a batch of items with graceful degradation
        
        Args:
            items: List of items to process
            processor_func: Function to process each item
            context: Additional context for error handling
            
        Returns:
            Dictionary with results and error summary
        """
        context = context or {}
        successful_items = []
        failed_items = []
        errors = []
        
        for i, item in enumerate(items):
            item_context = {**context, 'batch_index': i, 'item': str(item)[:100]}
            
            try:
                result = processor_func(item)
                successful_items.append({'item': item, 'result': result, 'index': i})
                
                # Update circuit breaker on success
                component = context.get('component', 'batch_processor')
                self.error_handler.update_circuit_breaker(component, True)
                
            except Exception as e:
                error_info = self.error_handler.handle_error(e, item_context, raise_on_critical=False)
                failed_items.append({'item': item, 'error': error_info, 'index': i})
                errors.append(error_info)
                
                # Update circuit breaker on failure
                component = context.get('component', 'batch_processor')
                self.error_handler.update_circuit_breaker(component, False)
                
                # Check if we should stop processing this batch
                if len(errors) >= self.max_failures_per_batch:
                    self.error_handler.logger.warning(
                        f"Stopping batch processing: {len(errors)} failures reached threshold"
                    )
                    break
                
                # Check circuit breaker
                if self.error_handler.is_circuit_breaker_open(component):
                    self.error_handler.logger.warning(
                        f"Stopping batch processing: circuit breaker open for {component}"
                    )
                    break
        
        return {
            'successful_count': len(successful_items),
            'failed_count': len(failed_items),
            'total_count': len(items),
            'success_rate': len(successful_items) / len(items) if items else 0,
            'successful_items': successful_items,
            'failed_items': failed_items,
            'errors': errors,
            'should_retry_failed': len(failed_items) > 0 and len(errors) < self.max_failures_per_batch
        }
    
    def retry_failed_items(self, batch_result: Dict[str, Any], processor_func: Callable,
                          context: Dict[str, Any] = None, max_retries: int = 2) -> Dict[str, Any]:
        """
        Retry processing failed items from a previous batch
        
        Args:
            batch_result: Result from previous batch processing
            processor_func: Function to process each item
            context: Additional context for error handling
            max_retries: Maximum number of retry attempts
            
        Returns:
            Updated batch result with retry information
        """
        if not batch_result.get('should_retry_failed', False):
            return batch_result
        
        failed_items = batch_result.get('failed_items', [])
        if not failed_items:
            return batch_result
        
        context = context or {}
        retry_successful = []
        still_failed = []
        
        for attempt in range(max_retries):
            self.error_handler.logger.info(f"Retry attempt {attempt + 1}/{max_retries} for {len(failed_items)} items")
            
            items_to_retry = [item_info['item'] for item_info in failed_items]
            retry_context = {**context, 'retry_attempt': attempt + 1}
            
            retry_result = self.process_batch(items_to_retry, processor_func, retry_context)
            
            # Update results
            retry_successful.extend(retry_result['successful_items'])
            failed_items = retry_result['failed_items']
            
            # If all items succeeded or no more failures, stop retrying
            if not failed_items or not retry_result.get('should_retry_failed', False):
                break
        
        # Update original batch result
        batch_result['successful_count'] += len(retry_successful)
        batch_result['failed_count'] = len(failed_items)
        batch_result['success_rate'] = batch_result['successful_count'] / batch_result['total_count']
        batch_result['successful_items'].extend(retry_successful)
        batch_result['failed_items'] = failed_items
        batch_result['retry_attempts'] = max_retries
        
        return batch_result


class ErrorRecoveryManager:
    """Manages error recovery strategies and fallback mechanisms"""
    
    def __init__(self, error_handler: ErrorHandler):
        self.error_handler = error_handler
        self.fallback_strategies = {}
        self.recovery_history = []
    
    def register_fallback_strategy(self, error_category: ErrorCategory, 
                                 strategy_name: str, strategy_func: Callable):
        """
        Register a fallback strategy for an error category
        
        Args:
            error_category: Category of errors this strategy handles
            strategy_name: Name of the strategy
            strategy_func: Function that implements the fallback
        """
        if error_category not in self.fallback_strategies:
            self.fallback_strategies[error_category] = {}
        
        self.fallback_strategies[error_category][strategy_name] = strategy_func
    
    def execute_with_fallback(self, primary_func: Callable, error_category: ErrorCategory,
                            context: Dict[str, Any] = None, *args, **kwargs) -> Any:
        """
        Execute function with automatic fallback on failure
        
        Args:
            primary_func: Primary function to execute
            error_category: Category for fallback selection
            context: Additional context
            *args, **kwargs: Arguments for the function
            
        Returns:
            Result from primary function or fallback
        """
        context = context or {}
        
        try:
            # Try primary function first
            return primary_func(*args, **kwargs)
        
        except Exception as e:
            error_info = self.error_handler.categorize_error(e, context)
            
            # Try fallback strategies
            strategies = self.fallback_strategies.get(error_category, {})
            
            for strategy_name, strategy_func in strategies.items():
                try:
                    self.error_handler.logger.info(f"Attempting fallback strategy: {strategy_name}")
                    result = strategy_func(*args, **kwargs)
                    
                    # Record successful recovery
                    self.recovery_history.append({
                        'timestamp': datetime.now(),
                        'error_category': error_category,
                        'strategy_used': strategy_name,
                        'success': True,
                        'context': context
                    })
                    
                    return result
                
                except Exception as fallback_error:
                    self.error_handler.logger.warning(
                        f"Fallback strategy {strategy_name} failed: {fallback_error}"
                    )
                    continue
            
            # All fallback strategies failed
            self.recovery_history.append({
                'timestamp': datetime.now(),
                'error_category': error_category,
                'strategy_used': None,
                'success': False,
                'context': context
            })
            
            # Re-raise the original error
            raise e
    
    def get_recovery_statistics(self) -> Dict[str, Any]:
        """
        Get statistics about recovery attempts
        
        Returns:
            Dictionary with recovery statistics
        """
        if not self.recovery_history:
            return {'total_attempts': 0, 'success_rate': 0, 'by_category': {}}
        
        total_attempts = len(self.recovery_history)
        successful_attempts = sum(1 for r in self.recovery_history if r['success'])
        success_rate = successful_attempts / total_attempts
        
        # Group by category
        by_category = {}
        for record in self.recovery_history:
            category = record['error_category'].value
            if category not in by_category:
                by_category[category] = {'attempts': 0, 'successes': 0}
            
            by_category[category]['attempts'] += 1
            if record['success']:
                by_category[category]['successes'] += 1
        
        # Calculate success rates per category
        for category_stats in by_category.values():
            category_stats['success_rate'] = (
                category_stats['successes'] / category_stats['attempts']
                if category_stats['attempts'] > 0 else 0
            )
        
        return {
            'total_attempts': total_attempts,
            'successful_attempts': successful_attempts,
            'success_rate': success_rate,
            'by_category': by_category,
            'recent_attempts': self.recovery_history[-10:]  # Last 10 attempts
        }


def create_pipeline_error_handler(logger: Optional[logging.Logger] = None) -> ErrorHandler:
    """
    Factory function to create a pre-configured error handler for the pipeline
    
    Args:
        logger: Optional logger instance
        
    Returns:
        Configured ErrorHandler instance
    """
    error_handler = ErrorHandler(logger)
    
    # Register common recovery strategies
    def network_recovery_strategy(error_info: ErrorInfo) -> bool:
        """Recovery strategy for network errors"""
        # Wait a bit longer and try to re-establish connection
        time.sleep(5)
        return True  # Indicate that recovery was attempted
    
    def storage_recovery_strategy(error_info: ErrorInfo) -> bool:
        """Recovery strategy for storage errors"""
        # Try to create directories or use alternative paths
        try:
            import os
            context = error_info.context
            if 'path' in context:
                os.makedirs(os.path.dirname(context['path']), exist_ok=True)
                return True
        except Exception:
            pass
        return False
    
    error_handler.register_recovery_strategy(ErrorCategory.NETWORK, network_recovery_strategy)
    error_handler.register_recovery_strategy(ErrorCategory.STORAGE, storage_recovery_strategy)
    
    return error_handler


# Utility decorators for common error handling patterns
def resilient_operation(error_handler: ErrorHandler, max_attempts: int = 3,
                       fallback_value: Any = None, component: str = "unknown"):
    """
    Decorator for resilient operations with circuit breaker and fallback
    
    Args:
        error_handler: ErrorHandler instance
        max_attempts: Maximum retry attempts
        fallback_value: Value to return if all attempts fail
        component: Component name for circuit breaker
        
    Returns:
        Decorator function
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Check circuit breaker
            if error_handler.is_circuit_breaker_open(component):
                error_handler.logger.warning(f"Circuit breaker open for {component}, returning fallback")
                return fallback_value
            
            last_error = None
            for attempt in range(max_attempts):
                try:
                    result = func(*args, **kwargs)
                    error_handler.update_circuit_breaker(component, True)
                    return result
                
                except Exception as e:
                    last_error = e
                    error_handler.update_circuit_breaker(component, False)
                    
                    if attempt < max_attempts - 1:
                        # Wait before retry
                        wait_time = 2 ** attempt
                        time.sleep(wait_time)
                    else:
                        # Log final failure
                        error_handler.handle_error(e, {
                            'component': component,
                            'operation': func.__name__,
                            'attempt': attempt + 1
                        }, raise_on_critical=False)
            
            return fallback_value
        
        return wrapper
    return decorator