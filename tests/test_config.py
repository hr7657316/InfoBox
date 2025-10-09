"""
Unit tests for configuration management system
"""

import os
import tempfile
import pytest
from pathlib import Path
from unittest.mock import patch, mock_open
import yaml

from pipeline.utils.config import ConfigManager


class TestConfigManager:
    """Test cases for ConfigManager class"""
    
    def setup_method(self):
        """Set up test fixtures before each test method"""
        self.temp_dir = tempfile.mkdtemp()
        self.config_file = os.path.join(self.temp_dir, 'test_config.yaml')
        self.env_file = os.path.join(self.temp_dir, '.env')
    
    def teardown_method(self):
        """Clean up after each test method"""
        # Clean up any environment variables set during tests
        env_vars_to_clean = [
            'WHATSAPP_API_TOKEN', 'WHATSAPP_PHONE_NUMBER_ID',
            'TWILIO_ACCOUNT_SID', 'TWILIO_AUTH_TOKEN',
            'EMAIL_1_ADDRESS', 'EMAIL_1_PASSWORD', 'EMAIL_1_IMAP_SERVER',
            'EMAIL_1_IMAP_PORT', 'EMAIL_1_USE_SSL', 'EMAIL_1_AUTH_METHOD',
            'EMAIL_1_CLIENT_ID', 'EMAIL_1_CLIENT_SECRET', 'EMAIL_1_REFRESH_TOKEN',
            'EMAIL_2_ADDRESS', 'EMAIL_2_PASSWORD', 'EMAIL_2_IMAP_SERVER',
            'EMAIL_2_IMAP_PORT', 'EMAIL_2_USE_SSL', 'EMAIL_2_AUTH_METHOD',
            'EMAIL_2_CLIENT_ID', 'EMAIL_2_CLIENT_SECRET', 'EMAIL_2_REFRESH_TOKEN',
            'STORAGE_BASE_PATH', 'TEST_VAR'
        ]
        for var in env_vars_to_clean:
            if var in os.environ:
                del os.environ[var]
    
    def test_init_default_config_file(self):
        """Test ConfigManager initialization with default config file"""
        config_manager = ConfigManager()
        assert config_manager.config_file == "config.yaml"
        assert config_manager.config_data == {}
        assert not config_manager._loaded
    
    def test_init_custom_config_file(self):
        """Test ConfigManager initialization with custom config file"""
        config_manager = ConfigManager("custom_config.yaml")
        assert config_manager.config_file == "custom_config.yaml"
    
    def test_load_config_nonexistent_file(self):
        """Test loading config when file doesn't exist"""
        config_manager = ConfigManager("nonexistent.yaml")
        config = config_manager.load_config()
        
        assert config == {}
        assert config_manager._loaded
    
    def test_load_config_valid_yaml(self):
        """Test loading valid YAML configuration"""
        test_config = {
            'whatsapp': {'provider': 'business_api'},
            'storage': {'base_path': './test_data'}
        }
        
        with open(self.config_file, 'w') as f:
            yaml.dump(test_config, f)
        
        config_manager = ConfigManager(self.config_file)
        config = config_manager.load_config()
        
        assert config == test_config
        assert config_manager._loaded
    
    def test_load_config_invalid_yaml(self):
        """Test loading invalid YAML configuration"""
        with open(self.config_file, 'w') as f:
            f.write("invalid: yaml: content: [")
        
        config_manager = ConfigManager(self.config_file)
        
        with pytest.raises(ValueError, match="Invalid YAML"):
            config_manager.load_config()
    
    def test_load_config_with_env_overrides(self):
        """Test loading config with environment variable overrides"""
        # Set environment variables
        os.environ['WHATSAPP_API_TOKEN'] = 'test_token'
        os.environ['WHATSAPP_PHONE_NUMBER_ID'] = 'test_phone_id'
        os.environ['EMAIL_1_ADDRESS'] = 'test@example.com'
        os.environ['EMAIL_1_PASSWORD'] = 'test_password'
        os.environ['EMAIL_1_IMAP_SERVER'] = 'imap.example.com'
        os.environ['STORAGE_BASE_PATH'] = '/test/storage'
        
        config_manager = ConfigManager("nonexistent.yaml")
        config = config_manager.load_config()
        
        # Check WhatsApp config
        assert config['whatsapp']['api_token'] == 'test_token'
        assert config['whatsapp']['phone_number_id'] == 'test_phone_id'
        
        # Check email config
        assert len(config['email']['accounts']) == 1
        assert config['email']['accounts'][0]['email'] == 'test@example.com'
        assert config['email']['accounts'][0]['password'] == 'test_password'
        assert config['email']['accounts'][0]['imap_server'] == 'imap.example.com'
        
        # Check storage config
        assert config['storage']['base_path'] == '/test/storage'
    
    def test_load_config_multiple_email_accounts(self):
        """Test loading multiple email accounts from environment"""
        os.environ['EMAIL_1_ADDRESS'] = 'first@example.com'
        os.environ['EMAIL_1_PASSWORD'] = 'password1'
        os.environ['EMAIL_1_IMAP_SERVER'] = 'imap1.example.com'
        
        os.environ['EMAIL_2_ADDRESS'] = 'second@example.com'
        os.environ['EMAIL_2_PASSWORD'] = 'password2'
        os.environ['EMAIL_2_IMAP_SERVER'] = 'imap2.example.com'
        os.environ['EMAIL_2_AUTH_METHOD'] = 'oauth2'
        os.environ['EMAIL_2_CLIENT_ID'] = 'client_id_2'
        
        config_manager = ConfigManager("nonexistent.yaml")
        config = config_manager.load_config()
        
        assert len(config['email']['accounts']) == 2
        assert config['email']['accounts'][0]['email'] == 'first@example.com'
        assert config['email']['accounts'][1]['email'] == 'second@example.com'
        assert config['email']['accounts'][1]['auth_method'] == 'oauth2'
        assert config['email']['accounts'][1]['client_id'] == 'client_id_2'
    
    def test_get_whatsapp_config(self):
        """Test getting WhatsApp configuration"""
        test_config = {
            'whatsapp': {
                'provider': 'business_api',
                'api_token': 'test_token'
            }
        }
        
        with open(self.config_file, 'w') as f:
            yaml.dump(test_config, f)
        
        config_manager = ConfigManager(self.config_file)
        whatsapp_config = config_manager.get_whatsapp_config()
        
        assert whatsapp_config == test_config['whatsapp']
    
    def test_get_whatsapp_config_empty(self):
        """Test getting WhatsApp config when not configured"""
        config_manager = ConfigManager("nonexistent.yaml")
        whatsapp_config = config_manager.get_whatsapp_config()
        
        assert whatsapp_config == {}
    
    def test_get_email_configs(self):
        """Test getting email configurations"""
        test_config = {
            'email': {
                'accounts': [
                    {'email': 'test1@example.com', 'password': 'pass1'},
                    {'email': 'test2@example.com', 'password': 'pass2'}
                ]
            }
        }
        
        with open(self.config_file, 'w') as f:
            yaml.dump(test_config, f)
        
        config_manager = ConfigManager(self.config_file)
        email_configs = config_manager.get_email_configs()
        
        assert len(email_configs) == 2
        assert email_configs[0]['email'] == 'test1@example.com'
        assert email_configs[1]['email'] == 'test2@example.com'
    
    def test_get_email_configs_empty(self):
        """Test getting email configs when not configured"""
        config_manager = ConfigManager("nonexistent.yaml")
        email_configs = config_manager.get_email_configs()
        
        assert email_configs == []
    
    def test_get_storage_config_defaults(self):
        """Test getting storage config with defaults"""
        config_manager = ConfigManager("nonexistent.yaml")
        storage_config = config_manager.get_storage_config()
        
        expected_defaults = {
            'base_path': './data',
            'create_date_folders': True,
            'json_format': True,
            'csv_format': True,
            'media_folder': 'media'
        }
        
        for key, value in expected_defaults.items():
            assert storage_config[key] == value
    
    def test_get_storage_config_with_overrides(self):
        """Test getting storage config with custom values"""
        test_config = {
            'storage': {
                'base_path': '/custom/path',
                'json_format': False
            }
        }
        
        with open(self.config_file, 'w') as f:
            yaml.dump(test_config, f)
        
        config_manager = ConfigManager(self.config_file)
        storage_config = config_manager.get_storage_config()
        
        assert storage_config['base_path'] == '/custom/path'
        assert storage_config['json_format'] is False
        assert storage_config['csv_format'] is True  # Default value
    
    def test_validate_config_valid(self):
        """Test validation of valid configuration"""
        os.environ['WHATSAPP_API_TOKEN'] = 'test_token'
        os.environ['WHATSAPP_PHONE_NUMBER_ID'] = 'test_phone_id'
        os.environ['EMAIL_1_ADDRESS'] = 'test@example.com'
        os.environ['EMAIL_1_PASSWORD'] = 'test_password'
        os.environ['EMAIL_1_IMAP_SERVER'] = 'imap.example.com'
        
        config_manager = ConfigManager("nonexistent.yaml")
        errors = config_manager.validate_config()
        
        assert errors == []
    
    def test_validate_config_missing_whatsapp_token(self):
        """Test validation with missing WhatsApp token"""
        test_config = {'whatsapp': {'provider': 'business_api'}}
        
        with open(self.config_file, 'w') as f:
            yaml.dump(test_config, f)
        
        config_manager = ConfigManager(self.config_file)
        errors = config_manager.validate_config()
        
        assert any("requires either 'api_token' or 'twilio_auth_token'" in error for error in errors)
    
    def test_validate_config_missing_phone_number_id(self):
        """Test validation with missing phone number ID for Business API"""
        os.environ['WHATSAPP_API_TOKEN'] = 'test_token'
        
        config_manager = ConfigManager("nonexistent.yaml")
        errors = config_manager.validate_config()
        
        assert any("requires 'phone_number_id'" in error for error in errors)
    
    def test_validate_config_missing_email_fields(self):
        """Test validation with missing email fields"""
        test_config = {
            'email': {
                'accounts': [
                    {'password': 'test_password'},  # Missing email
                    {'email': 'test@example.com'}   # Missing imap_server
                ]
            }
        }
        
        with open(self.config_file, 'w') as f:
            yaml.dump(test_config, f)
        
        config_manager = ConfigManager(self.config_file)
        errors = config_manager.validate_config()
        
        assert any("missing 'email' address" in error for error in errors)
        assert any("missing 'imap_server'" in error for error in errors)
    
    def test_validate_config_oauth2_missing_fields(self):
        """Test validation with OAuth2 missing required fields"""
        test_config = {
            'email': {
                'accounts': [{
                    'email': 'test@example.com',
                    'imap_server': 'imap.example.com',
                    'auth_method': 'oauth2',
                    'client_id': 'test_client_id'
                    # Missing client_secret and refresh_token
                }]
            }
        }
        
        with open(self.config_file, 'w') as f:
            yaml.dump(test_config, f)
        
        config_manager = ConfigManager(self.config_file)
        errors = config_manager.validate_config()
        
        assert any("'client_secret' not provided" in error for error in errors)
        assert any("'refresh_token' not provided" in error for error in errors)
    
    def test_get_env_var(self):
        """Test getting environment variable"""
        os.environ['TEST_VAR'] = 'test_value'
        
        config_manager = ConfigManager()
        value = config_manager.get_env_var('TEST_VAR')
        
        assert value == 'test_value'
        
        # Clean up
        del os.environ['TEST_VAR']
    
    def test_get_env_var_with_default(self):
        """Test getting environment variable with default"""
        config_manager = ConfigManager()
        value = config_manager.get_env_var('NONEXISTENT_VAR', 'default_value')
        
        assert value == 'default_value'
    
    def test_get_logging_config_defaults(self):
        """Test getting logging config with defaults"""
        config_manager = ConfigManager("nonexistent.yaml")
        logging_config = config_manager.get_logging_config()
        
        expected_defaults = {
            'level': 'INFO',
            'format': '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            'file_logging': True,
            'console_logging': True,
            'log_file': 'pipeline.log',
            'max_file_size': '10MB',
            'backup_count': 5
        }
        
        for key, value in expected_defaults.items():
            assert logging_config[key] == value
    
    def test_get_scheduler_config_defaults(self):
        """Test getting scheduler config with defaults"""
        config_manager = ConfigManager("nonexistent.yaml")
        scheduler_config = config_manager.get_scheduler_config()
        
        expected_defaults = {
            'enabled': False,
            'schedule_type': 'interval',
            'interval_hours': 24,
            'cron_expression': None,
            'daily_time': '02:00'
        }
        
        for key, value in expected_defaults.items():
            assert scheduler_config[key] == value
    
    def test_config_loaded_only_once(self):
        """Test that config is loaded only once"""
        test_config = {'test': 'value'}
        
        with open(self.config_file, 'w') as f:
            yaml.dump(test_config, f)
        
        config_manager = ConfigManager(self.config_file)
        
        # Load config first time
        config1 = config_manager.load_config()
        assert config_manager._loaded
        
        # Modify the file
        with open(self.config_file, 'w') as f:
            yaml.dump({'test': 'modified'}, f)
        
        # Load config second time - should return cached version
        config2 = config_manager.load_config()
        
        assert config1 == config2
        assert config2['test'] == 'value'  # Original value, not modified


if __name__ == '__main__':
    pytest.main([__file__])