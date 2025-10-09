"""
Centralized logging system for the extraction pipeline
"""

import logging
import logging.handlers
import os
from typing import Dict, Any, Optional
from datetime import datetime
import json


class PipelineLogger:
    """Centralized logging with structured output and error tracking"""
    
    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or {}
        self.logger = None
        self._setup_complete = False
        self._log_dir = self.config.get('log_dir', 'logs')
        self._log_level = self.config.get('log_level', 'INFO')
        self._max_bytes = self.config.get('max_bytes', 10 * 1024 * 1024)  # 10MB
        self._backup_count = self.config.get('backup_count', 5)
        self._console_output = self.config.get('console_output', True)
        self._file_output = self.config.get('file_output', True)
    
    def setup_logging(self) -> None:
        """
        Configure logging levels and formats with file rotation and console output
        """
        if self._setup_complete:
            return
            
        # Create logs directory if it doesn't exist
        if self._file_output and not os.path.exists(self._log_dir):
            os.makedirs(self._log_dir)
        
        # Create logger
        self.logger = logging.getLogger('pipeline')
        self.logger.setLevel(getattr(logging, self._log_level.upper()))
        
        # Clear any existing handlers
        self.logger.handlers.clear()
        
        # Create formatter for structured logging with fallback for missing component
        class ComponentFormatter(logging.Formatter):
            def format(self, record):
                if not hasattr(record, 'component'):
                    record.component = 'pipeline'
                return super().format(record)
        
        formatter = ComponentFormatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(component)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        
        # Add file handler with rotation if file output is enabled
        if self._file_output:
            log_file = os.path.join(self._log_dir, 'pipeline.log')
            file_handler = logging.handlers.RotatingFileHandler(
                log_file,
                maxBytes=self._max_bytes,
                backupCount=self._backup_count
            )
            file_handler.setFormatter(formatter)
            self.logger.addHandler(file_handler)
        
        # Add console handler if console output is enabled
        if self._console_output:
            console_handler = logging.StreamHandler()
            console_handler.setFormatter(formatter)
            self.logger.addHandler(console_handler)
        
        self._setup_complete = True
        self.log_info("Logging system initialized", "logger")
    
    def _log_with_component(self, level: str, message: str, component: str = "pipeline", **kwargs) -> None:
        """
        Internal method to log with component context
        
        Args:
            level: Log level (info, warning, error, debug)
            message: Log message
            component: Component generating the log
            **kwargs: Additional context data
        """
        if not self._setup_complete:
            self.setup_logging()
        
        # Add component to extra data for formatter
        extra = {'component': component}
        
        # Add any additional context
        if kwargs:
            context_str = json.dumps(kwargs, default=str)
            message = f"{message} | Context: {context_str}"
        
        # Log at appropriate level
        log_method = getattr(self.logger, level.lower())
        log_method(message, extra=extra)
    
    def log_extraction_start(self, source: str) -> None:
        """
        Log the start of an extraction process
        
        Args:
            source: Name of the data source (whatsapp, email)
        """
        self._log_with_component(
            'info',
            f"Starting extraction from {source}",
            f"{source}_extractor",
            timestamp=datetime.now().isoformat(),
            action="extraction_start"
        )
    
    def log_extraction_complete(self, source: str, stats: Dict[str, Any]) -> None:
        """
        Log the completion of an extraction process
        
        Args:
            source: Name of the data source
            stats: Dictionary containing extraction statistics
        """
        self._log_with_component(
            'info',
            f"Extraction from {source} completed successfully",
            f"{source}_extractor",
            timestamp=datetime.now().isoformat(),
            action="extraction_complete",
            stats=stats
        )
    
    def log_error(self, component: str, error: Exception, context: Optional[Dict[str, Any]] = None) -> None:
        """
        Log an error with context
        
        Args:
            component: Component where error occurred
            error: Exception object
            context: Additional context information
        """
        error_context = {
            'error_type': type(error).__name__,
            'error_message': str(error),
            'timestamp': datetime.now().isoformat()
        }
        
        if context:
            error_context.update(context)
        
        self._log_with_component(
            'error',
            f"Error in {component}: {str(error)}",
            component,
            **error_context
        )
    
    def log_info(self, message: str, component: str = "pipeline", **kwargs) -> None:
        """
        Log an informational message
        
        Args:
            message: Log message
            component: Component generating the log
            **kwargs: Additional context data
        """
        self._log_with_component('info', message, component, **kwargs)
    
    def log_warning(self, message: str, component: str = "pipeline", **kwargs) -> None:
        """
        Log a warning message
        
        Args:
            message: Warning message
            component: Component generating the warning
            **kwargs: Additional context data
        """
        self._log_with_component('warning', message, component, **kwargs)
    
    def log_debug(self, message: str, component: str = "pipeline", **kwargs) -> None:
        """
        Log a debug message
        
        Args:
            message: Debug message
            component: Component generating the debug info
            **kwargs: Additional context data
        """
        self._log_with_component('debug', message, component, **kwargs)
    
    def log_api_request(self, component: str, method: str, url: str, status_code: Optional[int] = None, **kwargs) -> None:
        """
        Log API request details for extraction activities
        
        Args:
            component: Component making the API request
            method: HTTP method
            url: API endpoint URL
            status_code: Response status code
            **kwargs: Additional request context
        """
        request_context = {
            'method': method,
            'url': url,
            'timestamp': datetime.now().isoformat(),
            'action': 'api_request'
        }
        
        if status_code:
            request_context['status_code'] = status_code
        
        request_context.update(kwargs)
        
        level = 'info' if not status_code or 200 <= status_code < 300 else 'warning'
        message = f"API {method} {url}"
        if status_code:
            message += f" - Status: {status_code}"
        
        self._log_with_component(level, message, component, **request_context)
    
    def log_data_processing(self, component: str, action: str, count: int, **kwargs) -> None:
        """
        Log data processing activities
        
        Args:
            component: Component processing the data
            action: Type of processing (extracted, saved, filtered, etc.)
            count: Number of items processed
            **kwargs: Additional processing context
        """
        processing_context = {
            'action': action,
            'count': count,
            'timestamp': datetime.now().isoformat()
        }
        processing_context.update(kwargs)
        
        self._log_with_component(
            'info',
            f"Data processing: {action} {count} items",
            component,
            **processing_context
        )