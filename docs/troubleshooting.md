# Troubleshooting Guide

This comprehensive troubleshooting guide helps you resolve common issues with the Data Extraction Pipeline. Issues are organized by category with step-by-step solutions.

## Table of Contents

1. [Installation Issues](#installation-issues)
2. [Configuration Problems](#configuration-problems)
3. [Authentication Errors](#authentication-errors)
4. [Connection Issues](#connection-issues)
5. [Data Extraction Problems](#data-extraction-problems)
6. [Storage and File Issues](#storage-and-file-issues)
7. [Performance Issues](#performance-issues)
8. [Scheduling Problems](#scheduling-problems)
9. [Logging and Debug Issues](#logging-and-debug-issues)
10. [Platform-Specific Issues](#platform-specific-issues)

## Installation Issues

### Issue: pip install fails with dependency conflicts

**Symptoms:**
```
ERROR: pip's dependency resolver does not currently consider all the packages that are installed
```

**Solutions:**
1. **Use a virtual environment:**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   pip install -r requirements.txt
   ```

2. **Update pip and setuptools:**
   ```bash
   pip install --upgrade pip setuptools wheel
   pip install -r requirements.txt
   ```

3. **Install with --force-reinstall:**
   ```bash
   pip install --force-reinstall -r requirements.txt
   ```

### Issue: Python version compatibility errors

**Symptoms:**
```
ERROR: Package requires a different Python version
```

**Solutions:**
1. **Check Python version:**
   ```bash
   python --version  # Should be 3.8 or higher
   ```

2. **Use pyenv to manage Python versions:**
   ```bash
   pyenv install 3.11.0
   pyenv local 3.11.0
   ```

3. **Update requirements for older Python:**
   - For Python 3.7, add `pathlib2>=2.3.7` to requirements.txt

### Issue: Missing system dependencies

**Symptoms:**
```
error: Microsoft Visual C++ 14.0 is required (Windows)
error: command 'gcc' failed (Linux)
```

**Solutions:**

**Windows:**
- Install Microsoft C++ Build Tools
- Or install Visual Studio Community with C++ workload

**Linux (Ubuntu/Debian):**
```bash
sudo apt-get update
sudo apt-get install build-essential python3-dev
```

**macOS:**
```bash
xcode-select --install
```

## Configuration Problems

### Issue: Configuration file not found

**Symptoms:**
```
FileNotFoundError: [Errno 2] No such file or directory: 'config.yaml'
```

**Solutions:**
1. **Copy template configuration:**
   ```bash
   cp config.yaml.example config.yaml
   ```

2. **Specify config file path:**
   ```bash
   python -m pipeline.main --config /path/to/config.yaml
   ```

3. **Check current directory:**
   ```bash
   ls -la config.yaml
   pwd
   ```

### Issue: Invalid YAML syntax

**Symptoms:**
```
yaml.scanner.ScannerError: mapping values are not allowed here
```

**Solutions:**
1. **Validate YAML syntax:**
   ```bash
   python -c "import yaml; yaml.safe_load(open('config.yaml'))"
   ```

2. **Common YAML issues:**
   - Use spaces, not tabs for indentation
   - Ensure proper spacing after colons
   - Quote strings with special characters
   - Check for missing closing brackets/quotes

3. **Use online YAML validator:**
   - Copy your config to https://yamlchecker.com/

### Issue: Environment variables not loaded

**Symptoms:**
```
KeyError: 'WHATSAPP_ACCESS_TOKEN'
```

**Solutions:**
1. **Check .env file exists:**
   ```bash
   ls -la .env
   ```

2. **Copy from template:**
   ```bash
   cp .env.example .env
   nano .env  # Edit with your credentials
   ```

3. **Verify environment variables:**
   ```bash
   python -c "import os; print(os.getenv('WHATSAPP_ACCESS_TOKEN', 'NOT_SET'))"
   ```

4. **Load .env manually:**
   ```bash
   export $(cat .env | xargs)
   python -m pipeline.main
   ```

## Authentication Errors

### Issue: WhatsApp Business API authentication failed

**Symptoms:**
```
Error: (#100) Invalid parameter
Error: Invalid access token
```

**Solutions:**
1. **Verify access token:**
   ```bash
   curl -X GET "https://graph.facebook.com/v18.0/me" \
     -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
   ```

2. **Check token expiration:**
   - Temporary tokens expire in 24 hours
   - Generate a permanent token for production use

3. **Verify phone number ID:**
   ```bash
   curl -X GET "https://graph.facebook.com/v18.0/YOUR_PHONE_NUMBER_ID" \
     -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
   ```

4. **Check app permissions:**
   - Ensure WhatsApp Business Management permission is granted
   - Verify app is approved for production use

### Issue: Gmail OAuth2 authentication failed

**Symptoms:**
```
Error: invalid_grant: Token has been expired or revoked
```

**Solutions:**
1. **Regenerate refresh token:**
   ```bash
   python scripts/generate_gmail_token.py
   ```

2. **Check OAuth2 credentials:**
   - Verify client ID and secret are correct
   - Ensure Gmail API is enabled in Google Cloud Console

3. **Update OAuth consent screen:**
   - Add your email as a test user
   - Publish the app if needed

4. **Check scopes:**
   - Ensure `https://www.googleapis.com/auth/gmail.readonly` is included

### Issue: Email app password authentication failed

**Symptoms:**
```
Error: [AUTHENTICATIONFAILED] Invalid credentials
```

**Solutions:**
1. **Verify 2FA is enabled:**
   - Gmail: Google Account > Security > 2-Step Verification
   - Outlook: Microsoft Account > Security > Two-step verification

2. **Regenerate app password:**
   - Delete old app password
   - Generate new one specifically for this application

3. **Check email settings:**
   - Ensure IMAP is enabled in email account settings
   - Verify "Less secure app access" is disabled (use app passwords instead)

4. **Test with manual connection:**
   ```python
   import imaplib
   mail = imaplib.IMAP4_SSL('imap.gmail.com', 993)
   mail.login('your.email@gmail.com', 'your_app_password')
   ```

## Connection Issues

### Issue: Network connection timeouts

**Symptoms:**
```
requests.exceptions.ConnectTimeout: HTTPSConnectionPool
socket.timeout: The read operation timed out
```

**Solutions:**
1. **Check internet connection:**
   ```bash
   ping google.com
   curl -I https://graph.facebook.com
   ```

2. **Increase timeout values:**
   ```yaml
   # config.yaml
   performance:
     api_timeout_seconds: 60
     connection_timeout_seconds: 30
   ```

3. **Check firewall/proxy settings:**
   - Ensure ports 443 (HTTPS) and 993 (IMAPS) are open
   - Configure proxy settings if needed

4. **Use different DNS servers:**
   ```bash
   # Temporarily use Google DNS
   echo "nameserver 8.8.8.8" | sudo tee /etc/resolv.conf
   ```

### Issue: IMAP connection refused

**Symptoms:**
```
Error: [Errno 111] Connection refused
socket.error: [Errno 10061] No connection could be made
```

**Solutions:**
1. **Verify IMAP settings:**
   - Gmail: imap.gmail.com:993 (SSL)
   - Outlook: outlook.office365.com:993 (SSL)
   - Yahoo: imap.mail.yahoo.com:993 (SSL)

2. **Check IMAP is enabled:**
   - Gmail: Settings > Forwarding and POP/IMAP > Enable IMAP
   - Outlook: Settings > Mail > Sync email > IMAP settings

3. **Test manual connection:**
   ```bash
   telnet imap.gmail.com 993
   openssl s_client -connect imap.gmail.com:993
   ```

4. **Check corporate firewall:**
   - Contact IT department about IMAP access
   - Try from different network (mobile hotspot)

### Issue: Rate limiting errors

**Symptoms:**
```
Error: (#4) Application request limit reached
Error: 429 Too Many Requests
```

**Solutions:**
1. **Wait for rate limit reset:**
   - WhatsApp: Usually resets every hour
   - Gmail: Varies by quota type

2. **Reduce extraction frequency:**
   ```yaml
   # config.yaml
   whatsapp:
     rate_limit:
       requests_per_minute: 30  # Reduce from default 60
   ```

3. **Implement exponential backoff:**
   ```yaml
   error_handling:
     retry:
       max_attempts: 5
       backoff_factor: 3
   ```

4. **Check API quotas:**
   - Facebook Developer Console > App Dashboard > Usage
   - Google Cloud Console > APIs & Services > Quotas

## Data Extraction Problems

### Issue: No messages extracted

**Symptoms:**
```
INFO: Extraction completed. Messages extracted: 0
```

**Solutions:**
1. **Check date range:**
   ```yaml
   email:
     accounts:
       - date_range_days: 0  # 0 = all emails, increase if needed
   ```

2. **Verify folder names:**
   ```yaml
   email:
     accounts:
       - folders: ["INBOX", "Sent"]  # Check exact folder names
   ```

3. **Check unread_only setting:**
   ```yaml
   email:
     accounts:
       - unread_only: false  # Set to false to get all emails
   ```

4. **Test with debug mode:**
   ```bash
   DEBUG_MODE=true python -m pipeline.main
   ```

### Issue: Media downloads failing

**Symptoms:**
```
Error: Failed to download media file
HTTP 403: Forbidden
```

**Solutions:**
1. **Check media URL expiration:**
   - WhatsApp media URLs expire after a certain time
   - Extract and download media immediately

2. **Verify file size limits:**
   ```yaml
   storage:
     media:
       max_file_size_mb: 100  # Increase if needed
   ```

3. **Check allowed extensions:**
   ```yaml
   storage:
     media:
       allowed_extensions: [".jpg", ".pdf", ".mp4"]  # Add needed types
   ```

4. **Test manual download:**
   ```bash
   curl -O "MEDIA_URL_HERE"
   ```

### Issue: Incomplete data extraction

**Symptoms:**
- Missing fields in output
- Partial message content

**Solutions:**
1. **Check API permissions:**
   - Ensure all necessary scopes are granted
   - Verify business verification status

2. **Update API version:**
   ```yaml
   whatsapp:
     business_api:
       api_version: "v18.0"  # Use latest version
   ```

3. **Increase batch size:**
   ```yaml
   performance:
     batch_size: 50  # Reduce if memory issues
   ```

4. **Check message type support:**
   - Some message types may not be fully supported
   - Check API documentation for limitations

## Storage and File Issues

### Issue: Permission denied writing files

**Symptoms:**
```
PermissionError: [Errno 13] Permission denied: './data/'
```

**Solutions:**
1. **Check directory permissions:**
   ```bash
   ls -la ./data/
   chmod 755 ./data/
   ```

2. **Create directory manually:**
   ```bash
   mkdir -p ./data/whatsapp ./data/email
   chmod 755 ./data/whatsapp ./data/email
   ```

3. **Change storage location:**
   ```yaml
   storage:
     base_path: "/tmp/pipeline_data"  # Use writable location
   ```

4. **Run with elevated permissions:**
   ```bash
   sudo python -m pipeline.main  # Not recommended for production
   ```

### Issue: Disk space full

**Symptoms:**
```
OSError: [Errno 28] No space left on device
```

**Solutions:**
1. **Check disk space:**
   ```bash
   df -h
   du -sh ./data/
   ```

2. **Clean old extractions:**
   ```bash
   find ./data/ -type f -mtime +30 -delete  # Delete files older than 30 days
   ```

3. **Configure cleanup:**
   ```yaml
   storage:
     cleanup:
       enabled: true
       retention_days: 30
   ```

4. **Use external storage:**
   ```yaml
   storage:
     base_path: "/mnt/external_drive/pipeline_data"
   ```

### Issue: File encoding problems

**Symptoms:**
```
UnicodeDecodeError: 'utf-8' codec can't decode byte
```

**Solutions:**
1. **Set explicit encoding:**
   ```python
   # In config or code
   encoding: "utf-8"
   ```

2. **Handle different encodings:**
   ```yaml
   storage:
     encoding: "utf-8-sig"  # Handles BOM
   ```

3. **Clean problematic characters:**
   ```yaml
   storage:
     clean_unicode: true
   ```

## Performance Issues

### Issue: Slow extraction speed

**Symptoms:**
- Extraction takes very long time
- High memory usage

**Solutions:**
1. **Reduce batch size:**
   ```yaml
   performance:
     batch_size: 50  # Reduce from default 100
   ```

2. **Limit concurrent operations:**
   ```yaml
   performance:
     max_concurrent_accounts: 2
     max_concurrent_downloads: 3
   ```

3. **Optimize date range:**
   ```yaml
   email:
     accounts:
       - date_range_days: 7  # Only recent emails
   ```

4. **Disable unnecessary features:**
   ```yaml
   storage:
     formats:
       csv: false  # Only save JSON
     media:
       download_enabled: false  # Skip media downloads
   ```

### Issue: Memory usage too high

**Symptoms:**
```
MemoryError: Unable to allocate memory
```

**Solutions:**
1. **Set memory limits:**
   ```yaml
   performance:
     max_memory_usage_mb: 256
   ```

2. **Process in smaller batches:**
   ```yaml
   performance:
     batch_size: 25
   ```

3. **Enable streaming mode:**
   ```yaml
   performance:
     streaming_mode: true
   ```

4. **Monitor memory usage:**
   ```bash
   top -p $(pgrep -f "python.*pipeline")
   ```

## Scheduling Problems

### Issue: Cron job not running

**Symptoms:**
- Scheduled extraction doesn't execute
- No log entries at scheduled time

**Solutions:**
1. **Check cron syntax:**
   ```bash
   crontab -l
   # Verify cron expression: 0 2 * * * (daily at 2 AM)
   ```

2. **Test cron job manually:**
   ```bash
   # Add to crontab for testing
   * * * * * /usr/bin/python3 /path/to/pipeline/main.py >> /tmp/pipeline_cron.log 2>&1
   ```

3. **Check cron service:**
   ```bash
   sudo systemctl status cron
   sudo systemctl start cron
   ```

4. **Use absolute paths:**
   ```bash
   0 2 * * * cd /path/to/pipeline && /usr/bin/python3 -m pipeline.main
   ```

### Issue: Scheduler not starting

**Symptoms:**
```
Error: Scheduler failed to start
```

**Solutions:**
1. **Check scheduler configuration:**
   ```yaml
   scheduler:
     enabled: true
     schedule_type: "daily"
     daily_time: "02:00"
   ```

2. **Verify timezone settings:**
   ```yaml
   scheduler:
     timezone: "UTC"  # Or your local timezone
   ```

3. **Test scheduler manually:**
   ```python
   from pipeline.main import PipelineOrchestrator
   pipeline = PipelineOrchestrator('config.yaml')
   pipeline.start_scheduler()
   ```

4. **Check for conflicting processes:**
   ```bash
   ps aux | grep pipeline
   ```

## Logging and Debug Issues

### Issue: No log output

**Symptoms:**
- Log files are empty
- No console output

**Solutions:**
1. **Check logging configuration:**
   ```yaml
   logging:
     level: "DEBUG"  # Increase verbosity
     console:
       enabled: true
     file:
       enabled: true
   ```

2. **Verify log directory permissions:**
   ```bash
   mkdir -p ./logs
   chmod 755 ./logs
   ```

3. **Test logging manually:**
   ```python
   from pipeline.utils.logger import PipelineLogger
   logger = PipelineLogger({'level': 'DEBUG'})
   logger.setup_logging()
   ```

4. **Enable debug mode:**
   ```bash
   DEBUG_MODE=true python -m pipeline.main
   ```

### Issue: Log files too large

**Symptoms:**
- Log files consuming too much disk space
- Performance degradation

**Solutions:**
1. **Configure log rotation:**
   ```yaml
   logging:
     file:
       max_size_mb: 10
       backup_count: 5
   ```

2. **Reduce log level:**
   ```yaml
   logging:
     level: "WARNING"  # Only warnings and errors
   ```

3. **Clean old logs:**
   ```bash
   find ./logs/ -name "*.log.*" -mtime +7 -delete
   ```

4. **Use external log management:**
   ```yaml
   logging:
     external:
       enabled: true
       endpoint: "https://logs.example.com/api"
   ```

## Platform-Specific Issues

### Windows Issues

**Issue: Path separator problems**
```
FileNotFoundError: [Errno 2] No such file or directory: 'data\\whatsapp\\file.json'
```

**Solutions:**
1. **Use forward slashes in config:**
   ```yaml
   storage:
     base_path: "./data"  # Not ".\\data"
   ```

2. **Use pathlib in code:**
   ```python
   from pathlib import Path
   path = Path("data") / "whatsapp" / "file.json"
   ```

**Issue: PowerShell execution policy**
```
cannot be loaded because running scripts is disabled on this system
```

**Solutions:**
```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

### macOS Issues

**Issue: SSL certificate verification failed**
```
ssl.SSLCertVerificationError: certificate verify failed
```

**Solutions:**
1. **Update certificates:**
   ```bash
   /Applications/Python\ 3.x/Install\ Certificates.command
   ```

2. **Install certificates manually:**
   ```bash
   pip install --upgrade certifi
   ```

### Linux Issues

**Issue: Missing system packages**
```
ImportError: No module named '_ssl'
```

**Solutions:**
```bash
# Ubuntu/Debian
sudo apt-get install python3-dev libssl-dev libffi-dev

# CentOS/RHEL
sudo yum install python3-devel openssl-devel libffi-devel

# Arch Linux
sudo pacman -S python python-pip openssl libffi
```

## Getting Additional Help

### Enable Debug Mode

For any issue, first enable debug mode to get detailed information:

```bash
# Method 1: Environment variable
DEBUG_MODE=true python -m pipeline.main

# Method 2: Command line flag
python -m pipeline.main --debug

# Method 3: Configuration file
# config.yaml
development:
  debug_mode: true
```

### Collect System Information

When reporting issues, include this information:

```bash
# System information
python --version
pip list | grep -E "(pyyaml|requests|schedule|google)"
uname -a  # Linux/macOS
systeminfo  # Windows

# Pipeline information
python -c "from pipeline.utils.config import ConfigManager; print('Config loaded successfully')"
ls -la config.yaml .env
```

### Test Individual Components

Test components separately to isolate issues:

```python
# Test configuration loading
from pipeline.utils.config import ConfigManager
config = ConfigManager('config.yaml')
print("Config validation:", config.validate_config())

# Test WhatsApp connection
from pipeline.whatsapp.whatsapp_extractor import WhatsAppExtractor
extractor = WhatsAppExtractor(config.get_whatsapp_config())
print("WhatsApp auth:", extractor.authenticate())

# Test email connection
from pipeline.email.email_extractor import EmailExtractor
for email_config in config.get_email_configs():
    extractor = EmailExtractor(email_config)
    print(f"Email {email_config['name']}:", extractor.connect())
```

### Contact Support

If you're still experiencing issues:

1. **Check existing issues:** [GitHub Issues](https://github.com/yourusername/data-extraction-pipeline/issues)
2. **Create new issue:** Include debug output, configuration (without credentials), and system information
3. **Join discussions:** [GitHub Discussions](https://github.com/yourusername/data-extraction-pipeline/discussions)

### Emergency Recovery

If the pipeline is completely broken:

1. **Reset configuration:**
   ```bash
   cp config.yaml.example config.yaml
   cp .env.example .env
   ```

2. **Clean installation:**
   ```bash
   pip uninstall data-extraction-pipeline
   rm -rf venv/
   python -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   ```

3. **Minimal test:**
   ```bash
   python -c "import pipeline; print('Pipeline module loaded successfully')"
   ```