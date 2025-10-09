"""
Main pipeline orchestrator

Central coordinator that manages the extraction workflow for all data sources.
"""

from typing import Dict, List, Any, Optional
from datetime import datetime
from pipeline.models import ExtractionResult
from pipeline.utils.config import ConfigManager
from pipeline.utils.logger import PipelineLogger
from pipeline.utils.storage import StorageManager
from pipeline.utils.error_handler import ErrorHandler, ErrorCategory, ErrorSeverity
from pipeline.utils.notification_manager import NotificationManager
from pipeline.whatsapp.whatsapp_extractor import WhatsAppExtractor
from pipeline.email.email_extractor import EmailExtractor


class PipelineOrchestrator:
    """Central coordinator that manages the extraction workflow"""
    
    def __init__(self, config_path: str = "config.yaml"):
        self.config_path = config_path
        self.config_manager = ConfigManager(config_path)
        self.logger = None
        self.error_handler = None
        self.storage_manager = None
        self.notification_manager = None
        self.whatsapp_extractors = []
        self.email_extractors = []
        self._initialized = False
    
    def initialize(self) -> bool:
        """
        Initialize configuration, logging, and extractors with comprehensive error handling
        
        Returns:
            bool: True if initialization successful
        """
        try:
            # Load configuration
            config = self.config_manager.load_config()
            
            # Initialize logging
            logger_config = config.get('logging', {})
            self.logger = PipelineLogger(logger_config)
            self.logger.setup_logging()
            
            # Initialize error handler
            self.error_handler = ErrorHandler(self.logger.logger)
            
            # Initialize storage manager
            storage_config = config.get('storage', {})
            self.storage_manager = StorageManager(storage_config.get('base_path', './data'))
            
            # Initialize notification manager
            self.notification_manager = NotificationManager(config, self.logger.logger)
            
            # Validate configuration
            validation_errors = self._validate_configuration()
            if validation_errors:
                for error in validation_errors:
                    self.logger.log_error("configuration", Exception(error))
                return False
            
            # Setup extractors
            self._setup_extractors()
            
            self._initialized = True
            self.logger.log_info("Pipeline initialization completed successfully", "orchestrator")
            return True
            
        except Exception as e:
            if self.error_handler:
                self.error_handler.handle_error(e, {
                    'component': 'orchestrator',
                    'operation': 'initialization'
                }, raise_on_critical=False)
            return False
    
    def run_extraction(self) -> Dict[str, ExtractionResult]:
        """
        Run extraction from all configured sources with graceful degradation
        
        Returns:
            Dict mapping source names to extraction results
        """
        if not self._initialized:
            if not self.initialize():
                return {}
        
        results = {}
        start_time = datetime.now()
        
        self.logger.log_info("Starting extraction pipeline", "orchestrator")
        
        # Extract from WhatsApp if configured
        if self.whatsapp_extractors:
            try:
                whatsapp_result = self._extract_from_whatsapp()
                results['whatsapp'] = whatsapp_result
            except Exception as e:
                self.error_handler.handle_error(e, {
                    'component': 'orchestrator',
                    'operation': 'whatsapp_extraction'
                }, raise_on_critical=False)
                
                # Create failed result
                results['whatsapp'] = ExtractionResult(
                    source='whatsapp',
                    success=False,
                    messages_count=0,
                    media_count=0,
                    errors=[str(e)],
                    execution_time=0.0,
                    output_paths={}
                )
        
        # Extract from email accounts if configured
        if self.email_extractors:
            try:
                email_result = self._extract_from_email()
                results['email'] = email_result
            except Exception as e:
                self.error_handler.handle_error(e, {
                    'component': 'orchestrator',
                    'operation': 'email_extraction'
                }, raise_on_critical=False)
                
                # Create failed result
                results['email'] = ExtractionResult(
                    source='email',
                    success=False,
                    messages_count=0,
                    media_count=0,
                    errors=[str(e)],
                    execution_time=0.0,
                    output_paths={}
                )
        
        # Log summary
        total_time = (datetime.now() - start_time).total_seconds()
        successful_sources = sum(1 for result in results.values() if result.success)
        total_sources = len(results)
        
        self.logger.log_info(
            f"Extraction pipeline completed: {successful_sources}/{total_sources} sources successful",
            "orchestrator",
            execution_time=total_time,
            results_summary={source: result.success for source, result in results.items()}
        )
        
        # Log error summary if there were errors
        error_summary = self.error_handler.get_error_summary()
        if error_summary['total_errors'] > 0:
            self.logger.log_warning(
                f"Pipeline completed with {error_summary['total_errors']} errors",
                "orchestrator",
                error_summary=error_summary
            )
        
        # Send notifications about extraction results
        try:
            self.send_notifications(results)
        except Exception as e:
            self.logger.log_error("Failed to send notifications", "orchestrator", error=str(e))
        
        return results
    
    def schedule_extraction(self, schedule_config: Dict[str, Any]) -> None:
        """
        Set up scheduled extraction
        
        Args:
            schedule_config: Dictionary containing schedule configuration
        """
        # Implementation will be added in later tasks
        raise NotImplementedError("Scheduling will be implemented in task 7.2")
    
    def send_notifications(self, results: Dict[str, ExtractionResult]) -> None:
        """
        Send notifications about extraction results
        
        Args:
            results: Dictionary of extraction results
        """
        if not self.notification_manager:
            if self.logger:
                self.logger.log_warning("Notification manager not initialized", "orchestrator")
            return
        
        # Convert ExtractionResult objects to dictionaries for notification
        results_dict = {}
        for source, result in results.items():
            results_dict[source] = {
                'success': result.success,
                'messages_count': result.messages_count,
                'media_count': result.media_count,
                'errors': result.errors,
                'execution_time': result.execution_time,
                'output_paths': result.output_paths
            }
        
        # Send extraction complete notification
        success = self.notification_manager.send_extraction_complete_notification(results_dict)
        
        if success:
            self.logger.log_info("Notifications sent successfully", "orchestrator")
        else:
            self.logger.log_warning("Failed to send some or all notifications", "orchestrator")
        
        # Send error notifications for any errors that occurred
        for source, result in results.items():
            if result.errors:
                for error in result.errors:
                    error_info = {
                        'component': f"{source}_extractor",
                        'message': error,
                        'severity': 'medium',
                        'context': {
                            'source': source,
                            'messages_processed': result.messages_count,
                            'execution_time': result.execution_time
                        }
                    }
                    self.notification_manager.send_error_notification(error_info)
    
    def _setup_extractors(self) -> None:
        """Setup extractor instances based on configuration with error handling"""
        config = self.config_manager.load_config()
        
        # Setup WhatsApp extractors if configured - support multiple numbers
        whatsapp_configs = self.config_manager.get_whatsapp_configs()
        if whatsapp_configs:
            self.whatsapp_extractors = []
            for i, account_config in enumerate(whatsapp_configs):
                try:
                    # Create individual extractor for each WhatsApp number
                    whatsapp_extractor = WhatsAppExtractor(account_config)
                    self.whatsapp_extractors.append(whatsapp_extractor)
                    phone_id = account_config.get('phone_number_id', account_config.get('twilio_whatsapp_number', 'unknown'))
                    self.logger.log_info(f"WhatsApp extractor {i+1} initialized for {phone_id}", "orchestrator")
                except Exception as e:
                    self.error_handler.handle_error(e, {
                        'component': 'orchestrator',
                        'operation': 'whatsapp_setup',
                        'account': account_config.get('phone_number_id', 'unknown')
                    }, raise_on_critical=False)
            
            if not self.whatsapp_extractors:
                self.logger.log_warning("No WhatsApp extractors could be initialized", "orchestrator")
        
        # Setup email extractors if configured - support multiple accounts
        email_configs = self.config_manager.get_email_configs()
        if email_configs:
            self.email_extractors = []
            for i, account_config in enumerate(email_configs):
                try:
                    # Create individual extractor for each account
                    email_extractor = EmailExtractor({'accounts': [account_config]})
                    self.email_extractors.append(email_extractor)
                    self.logger.log_info(f"Email extractor {i+1} initialized for {account_config.get('email', 'unknown')}", "orchestrator")
                except Exception as e:
                    self.error_handler.handle_error(e, {
                        'component': 'orchestrator',
                        'operation': 'email_setup',
                        'account': account_config.get('email', 'unknown')
                    }, raise_on_critical=False)
            
            if not self.email_extractors:
                self.logger.log_warning("No email extractors could be initialized", "orchestrator")
    
    def _validate_configuration(self) -> List[str]:
        """
        Validate all configuration settings with comprehensive error checking
        
        Returns:
            List of validation errors (empty if valid)
        """
        errors = []
        
        try:
            # Use config manager's validation
            config_errors = self.config_manager.validate_config()
            errors.extend(config_errors)
            
            # Additional validation for pipeline-specific requirements
            config = self.config_manager.load_config()
            
            # Check if at least one data source is configured
            has_whatsapp = bool(self.config_manager.get_whatsapp_configs())
            has_email = bool(self.config_manager.get_email_configs())
            
            if not has_whatsapp and not has_email:
                errors.append("At least one data source (WhatsApp or Email) must be configured")
            
            # Validate storage configuration
            storage_config = config.get('storage', {})
            base_path = storage_config.get('base_path', './data')
            
            try:
                import os
                os.makedirs(base_path, exist_ok=True)
            except Exception as e:
                errors.append(f"Cannot create storage directory '{base_path}': {str(e)}")
            
        except Exception as e:
            errors.append(f"Configuration validation failed: {str(e)}")
        
        return errors


    def _extract_from_whatsapp(self) -> ExtractionResult:
        """Extract data from WhatsApp accounts with error handling and graceful degradation"""
        start_time = datetime.now()
        all_messages = []
        media_count = 0
        errors = []
        output_paths = {}
        
        try:
            # Process each WhatsApp extractor
            for i, extractor in enumerate(self.whatsapp_extractors):
                try:
                    # Authenticate
                    if not extractor.authenticate():
                        errors.append(f"WhatsApp authentication failed for account {i+1}")
                        continue
                    
                    # Extract messages
                    messages = extractor.extract_messages()
                    all_messages.extend(messages)
                    
                    # Download media files with graceful degradation
                    for message in messages:
                        if message.media_url:
                            try:
                                media_path = extractor.download_media(
                                    message.media_url,
                                    message.media_filename or f"media_{message.id}",
                                    self.storage_manager.get_media_directory('whatsapp')
                                )
                                if media_path:
                                    media_count += 1
                            except Exception as e:
                                # Log error but continue processing
                                self.error_handler.handle_error(e, {
                                    'component': 'whatsapp_extractor',
                                    'operation': 'media_download',
                                    'message_id': message.id,
                                    'account': i+1
                                }, raise_on_critical=False)
                                errors.append(f"Failed to download media for message {message.id} from account {i+1}: {str(e)}")
                
                except Exception as e:
                    # Log error but continue with other extractors
                    self.error_handler.handle_error(e, {
                        'component': 'orchestrator',
                        'operation': 'whatsapp_extractor_processing',
                        'account': i+1
                    }, raise_on_critical=False)
                    errors.append(f"WhatsApp extractor {i+1} failed: {str(e)}")
            
            # Save data
            if all_messages:
                output_paths = self.storage_manager.save_whatsapp_data(all_messages)
            
            execution_time = (datetime.now() - start_time).total_seconds()
            
            return ExtractionResult(
                source='whatsapp',
                success=len(all_messages) > 0 or len(errors) == 0,
                messages_count=len(all_messages),
                media_count=media_count,
                errors=errors,
                execution_time=execution_time,
                output_paths=output_paths
            )
            
        except Exception as e:
            execution_time = (datetime.now() - start_time).total_seconds()
            self.error_handler.handle_error(e, {
                'component': 'orchestrator',
                'operation': 'whatsapp_extraction'
            }, raise_on_critical=False)
            
            return ExtractionResult(
                source='whatsapp',
                success=False,
                messages_count=len(all_messages),
                media_count=media_count,
                errors=errors + [str(e)],
                execution_time=execution_time,
                output_paths=output_paths
            )
    
    def _extract_from_email(self) -> ExtractionResult:
        """Extract data from email accounts with error handling and graceful degradation"""
        start_time = datetime.now()
        all_emails = []
        media_count = 0
        errors = []
        output_paths = {}
        
        try:
            # Process each email extractor
            for extractor in self.email_extractors:
                try:
                    # Authenticate
                    if not extractor.authenticate():
                        errors.append("Email authentication failed for one or more accounts")
                        continue
                    
                    # Extract emails
                    emails = extractor.extract_emails()
                    all_emails.extend(emails)
                    
                    # Download attachments with graceful degradation
                    for email_obj in emails:
                        for attachment in email_obj.attachments:
                            try:
                                # This would be implemented in the email extractor
                                # For now, just count attachments
                                media_count += 1
                            except Exception as e:
                                self.error_handler.handle_error(e, {
                                    'component': 'email_extractor',
                                    'operation': 'attachment_download',
                                    'email_id': email_obj.id
                                }, raise_on_critical=False)
                                errors.append(f"Failed to download attachment for email {email_obj.id}: {str(e)}")
                
                except Exception as e:
                    # Log error but continue with other extractors
                    self.error_handler.handle_error(e, {
                        'component': 'orchestrator',
                        'operation': 'email_extractor_processing'
                    }, raise_on_critical=False)
                    errors.append(f"Email extractor failed: {str(e)}")
            
            # Save data
            if all_emails:
                output_paths = self.storage_manager.save_email_data(all_emails)
            
            execution_time = (datetime.now() - start_time).total_seconds()
            
            return ExtractionResult(
                source='email',
                success=len(all_emails) > 0 or len(errors) == 0,
                messages_count=len(all_emails),
                media_count=media_count,
                errors=errors,
                execution_time=execution_time,
                output_paths=output_paths
            )
            
        except Exception as e:
            execution_time = (datetime.now() - start_time).total_seconds()
            self.error_handler.handle_error(e, {
                'component': 'orchestrator',
                'operation': 'email_extraction'
            }, raise_on_critical=False)
            
            return ExtractionResult(
                source='email',
                success=False,
                messages_count=len(all_emails),
                media_count=media_count,
                errors=errors + [str(e)],
                execution_time=execution_time,
                output_paths=output_paths
            )