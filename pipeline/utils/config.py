"""
Configuration management for the extraction pipeline
"""

from typing import Dict, List, Any, Optional
import os
import yaml
from pathlib import Path
from dotenv import load_dotenv


class ConfigManager:
    """Centralized configuration management with environment variable support"""
    
    def __init__(self, config_file: str = "config.yaml"):
        self.config_file = config_file
        self.config_data = {}
        self._loaded = False
        # Load .env file if it exists
        load_dotenv()
    
    def load_config(self) -> Dict[str, Any]:
        """
        Load configuration from files and environment variables
        
        Returns:
            Dict containing all configuration data
        """
        if self._loaded:
            return self.config_data
            
        # Load YAML config file if it exists
        config_path = Path(self.config_file)
        if config_path.exists():
            try:
                with open(config_path, 'r', encoding='utf-8') as file:
                    self.config_data = yaml.safe_load(file) or {}
            except yaml.YAMLError as e:
                raise ValueError(f"Invalid YAML in config file {self.config_file}: {e}")
            except Exception as e:
                raise ValueError(f"Error reading config file {self.config_file}: {e}")
        else:
            self.config_data = {}
        
        # Override with environment variables where applicable
        self._load_env_overrides()
        self._loaded = True
        
        return self.config_data
    
    def _load_env_overrides(self) -> None:
        """Load environment variable overrides for sensitive configuration"""
        # WhatsApp API credentials
        # WhatsApp credentials - support multiple numbers via numbered env vars
        whatsapp_configs = []
        account_num = 1
        
        # First check for legacy single account configuration
        if os.getenv('WHATSAPP_API_TOKEN') or os.getenv('TWILIO_ACCOUNT_SID'):
            whatsapp_config = {}
            
            # Business API configuration
            if os.getenv('WHATSAPP_API_TOKEN'):
                whatsapp_config['api_token'] = os.getenv('WHATSAPP_API_TOKEN')
                whatsapp_config['phone_number_id'] = os.getenv('WHATSAPP_PHONE_NUMBER_ID')
                whatsapp_config['webhook_verify_token'] = os.getenv('WHATSAPP_WEBHOOK_VERIFY_TOKEN')
            
            # Twilio configuration
            if os.getenv('TWILIO_ACCOUNT_SID'):
                whatsapp_config['twilio_account_sid'] = os.getenv('TWILIO_ACCOUNT_SID')
                whatsapp_config['twilio_auth_token'] = os.getenv('TWILIO_AUTH_TOKEN')
                whatsapp_config['twilio_whatsapp_number'] = os.getenv('TWILIO_WHATSAPP_NUMBER')
            
            whatsapp_configs.append(whatsapp_config)
        
        # Then check for numbered multi-account configuration
        while True:
            whatsapp_key = f'WHATSAPP_{account_num}_API_TOKEN'
            twilio_key = f'TWILIO_{account_num}_ACCOUNT_SID'
            
            if not os.getenv(whatsapp_key) and not os.getenv(twilio_key):
                break
                
            whatsapp_config = {}
            
            # Business API configuration
            if os.getenv(whatsapp_key):
                whatsapp_config['api_token'] = os.getenv(whatsapp_key)
                whatsapp_config['phone_number_id'] = os.getenv(f'WHATSAPP_{account_num}_PHONE_NUMBER_ID')
                whatsapp_config['webhook_verify_token'] = os.getenv(f'WHATSAPP_{account_num}_WEBHOOK_VERIFY_TOKEN')
            
            # Twilio configuration
            if os.getenv(twilio_key):
                whatsapp_config['twilio_account_sid'] = os.getenv(twilio_key)
                whatsapp_config['twilio_auth_token'] = os.getenv(f'TWILIO_{account_num}_AUTH_TOKEN')
                whatsapp_config['twilio_whatsapp_number'] = os.getenv(f'TWILIO_{account_num}_WHATSAPP_NUMBER')
            
            whatsapp_configs.append(whatsapp_config)
            account_num += 1
        
        if whatsapp_configs:
            self.config_data['whatsapp'] = {'accounts': whatsapp_configs}
        
        # Email credentials - support multiple accounts via numbered env vars
        email_configs = []
        account_num = 1
        while True:
            email_key = f'EMAIL_{account_num}_ADDRESS'
            if not os.getenv(email_key):
                break
                
            email_config = {
                'email': os.getenv(email_key),
                'password': os.getenv(f'EMAIL_{account_num}_PASSWORD'),
                'imap_server': os.getenv(f'EMAIL_{account_num}_IMAP_SERVER'),
                'imap_port': int(os.getenv(f'EMAIL_{account_num}_IMAP_PORT', '993')),
                'use_ssl': os.getenv(f'EMAIL_{account_num}_USE_SSL', 'true').lower() == 'true',
                'auth_method': os.getenv(f'EMAIL_{account_num}_AUTH_METHOD', 'password')
            }
            
            # Add OAuth2 credentials if present
            if os.getenv(f'EMAIL_{account_num}_CLIENT_ID'):
                email_config['client_id'] = os.getenv(f'EMAIL_{account_num}_CLIENT_ID')
                email_config['client_secret'] = os.getenv(f'EMAIL_{account_num}_CLIENT_SECRET')
                email_config['refresh_token'] = os.getenv(f'EMAIL_{account_num}_REFRESH_TOKEN')
            
            email_configs.append(email_config)
            account_num += 1
        
        if email_configs:
            self.config_data['email'] = {'accounts': email_configs}
        
        # Storage configuration
        if os.getenv('STORAGE_BASE_PATH'):
            if 'storage' not in self.config_data:
                self.config_data['storage'] = {}
            self.config_data['storage']['base_path'] = os.getenv('STORAGE_BASE_PATH')
    
    def get_whatsapp_config(self) -> Dict[str, Any]:
        """
        Get WhatsApp-specific configuration (legacy method for backward compatibility)
        
        Returns:
            Dict containing WhatsApp configuration
        """
        if not self._loaded:
            self.load_config()
        
        whatsapp_config = self.config_data.get('whatsapp', {})
        
        # If using new multi-account format, return the first account for backward compatibility
        if 'accounts' in whatsapp_config and whatsapp_config['accounts']:
            return whatsapp_config['accounts'][0]
        
        return whatsapp_config
    
    def get_whatsapp_configs(self) -> List[Dict[str, Any]]:
        """
        Get WhatsApp account configurations
        
        Returns:
            List of WhatsApp account configuration dictionaries
        """
        if not self._loaded:
            self.load_config()
        
        whatsapp_config = self.config_data.get('whatsapp', {})
        
        # If using new multi-account format
        if 'accounts' in whatsapp_config:
            return whatsapp_config['accounts']
        
        # If using legacy single account format
        if whatsapp_config:
            return [whatsapp_config]
        
        return []
    
    def get_email_configs(self) -> List[Dict[str, Any]]:
        """
        Get email account configurations
        
        Returns:
            List of email account configuration dictionaries
        """
        if not self._loaded:
            self.load_config()
        
        email_config = self.config_data.get('email', {})
        return email_config.get('accounts', [])
    
    def get_storage_config(self) -> Dict[str, Any]:
        """
        Get storage configuration
        
        Returns:
            Dict containing storage configuration
        """
        if not self._loaded:
            self.load_config()
        
        # Default storage configuration
        default_config = {
            'base_path': './data',
            'create_date_folders': True,
            'json_format': True,
            'csv_format': True,
            'media_folder': 'media'
        }
        
        storage_config = self.config_data.get('storage', {})
        # Merge with defaults
        return {**default_config, **storage_config}
    
    def validate_config(self) -> List[str]:
        """
        Validate configuration parameters
        
        Returns:
            List of validation error messages (empty if valid)
        """
        if not self._loaded:
            self.load_config()
        
        errors = []
        
        # Validate WhatsApp configuration
        whatsapp_config = self.get_whatsapp_config()
        if whatsapp_config:
            if not whatsapp_config.get('api_token') and not whatsapp_config.get('twilio_auth_token'):
                errors.append("WhatsApp configuration requires either 'api_token' or 'twilio_auth_token'")
            
            if whatsapp_config.get('api_token') and not whatsapp_config.get('phone_number_id'):
                errors.append("WhatsApp Business API requires 'phone_number_id' when using 'api_token'")
            
            if whatsapp_config.get('twilio_auth_token') and not whatsapp_config.get('twilio_account_sid'):
                errors.append("Twilio WhatsApp API requires 'twilio_account_sid' when using 'twilio_auth_token'")
        
        # Validate email configurations
        email_configs = self.get_email_configs()
        for i, email_config in enumerate(email_configs):
            if not email_config.get('email'):
                errors.append(f"Email account {i+1} missing 'email' address")
            
            if not email_config.get('imap_server'):
                errors.append(f"Email account {i+1} missing 'imap_server'")
            
            auth_method = email_config.get('auth_method', 'password')
            if auth_method == 'password' and not email_config.get('password'):
                errors.append(f"Email account {i+1} using password auth but 'password' not provided")
            elif auth_method == 'oauth2':
                required_oauth_fields = ['client_id', 'client_secret', 'refresh_token']
                for field in required_oauth_fields:
                    if not email_config.get(field):
                        errors.append(f"Email account {i+1} using OAuth2 but '{field}' not provided")
        
        # Validate storage configuration
        storage_config = self.get_storage_config()
        base_path = storage_config.get('base_path')
        if base_path:
            try:
                Path(base_path).mkdir(parents=True, exist_ok=True)
            except Exception as e:
                errors.append(f"Cannot create storage base path '{base_path}': {e}")
        
        return errors
    
    def get_env_var(self, key: str, default: Any = None) -> Any:
        """
        Get environment variable with optional default
        
        Args:
            key: Environment variable name
            default: Default value if not found
            
        Returns:
            Environment variable value or default
        """
        return os.getenv(key, default)
    
    def get_logging_config(self) -> Dict[str, Any]:
        """
        Get logging configuration
        
        Returns:
            Dict containing logging configuration
        """
        if not self._loaded:
            self.load_config()
        
        # Default logging configuration
        default_config = {
            'level': 'INFO',
            'format': '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            'file_logging': True,
            'console_logging': True,
            'log_file': 'pipeline.log',
            'max_file_size': '10MB',
            'backup_count': 5
        }
        
        logging_config = self.config_data.get('logging', {})
        return {**default_config, **logging_config}
    
    def get_scheduler_config(self) -> Dict[str, Any]:
        """
        Get scheduler configuration
        
        Returns:
            Dict containing scheduler configuration
        """
        if not self._loaded:
            self.load_config()
        
        # Default scheduler configuration
        default_config = {
            'enabled': False,
            'schedule_type': 'interval',  # 'interval', 'cron', 'daily'
            'interval_hours': 24,
            'cron_expression': None,
            'daily_time': '02:00'
        }
        
        scheduler_config = self.config_data.get('scheduler', {})
        return {**default_config, **scheduler_config}