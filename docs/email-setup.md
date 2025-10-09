# Email API Setup Guide

This guide walks you through setting up email credentials for the data extraction pipeline. The pipeline supports multiple email providers including Gmail, Outlook, Yahoo, and any IMAP-compatible email service.

## Authentication Methods

The pipeline supports two authentication methods:

1. **OAuth2** (Recommended for Gmail) - More secure, token-based authentication
2. **App Passwords** - Simpler setup, works with most providers

## Gmail Setup

### Option 1: OAuth2 Authentication (Recommended)

OAuth2 is the most secure method for Gmail access and is recommended for production use.

#### Prerequisites

- A Google account with Gmail enabled
- Access to Google Cloud Console

#### Step 1: Create Google Cloud Project

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Click "Select a project" > "New Project"
3. Enter project details:
   - **Project Name**: "Data Extraction Pipeline" (or your preferred name)
   - **Organization**: Select your organization (if applicable)
4. Click "Create"

#### Step 2: Enable Gmail API

1. In the Google Cloud Console, ensure your project is selected
2. Navigate to "APIs & Services" > "Library"
3. Search for "Gmail API"
4. Click on "Gmail API" and then "Enable"

#### Step 3: Configure OAuth Consent Screen

1. Go to "APIs & Services" > "OAuth consent screen"
2. Choose "External" user type (unless you have a Google Workspace account)
3. Fill in the required information:
   - **App name**: "Data Extraction Pipeline"
   - **User support email**: Your email address
   - **Developer contact information**: Your email address
4. Click "Save and Continue"
5. Skip the "Scopes" section for now (click "Save and Continue")
6. Add test users if needed, then "Save and Continue"

#### Step 4: Create OAuth2 Credentials

1. Go to "APIs & Services" > "Credentials"
2. Click "Create Credentials" > "OAuth 2.0 Client IDs"
3. Choose "Desktop application" as the application type
4. Enter a name: "Data Extraction Pipeline Client"
5. Click "Create"
6. Download the credentials JSON file and save it securely

#### Step 5: Generate Refresh Token

Create a script to generate your refresh token:

```python
# scripts/generate_gmail_token.py
import json
from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow

# Scopes required for Gmail access
SCOPES = ['https://www.googleapis.com/auth/gmail.readonly']

def generate_refresh_token(credentials_file):
    """Generate refresh token for Gmail OAuth2."""
    flow = InstalledAppFlow.from_client_secrets_file(
        credentials_file, SCOPES)
    
    # Run the OAuth flow
    creds = flow.run_local_server(port=0)
    
    # Print the credentials
    print("Add these to your .env file:")
    print(f"GMAIL_CLIENT_ID={creds.client_id}")
    print(f"GMAIL_CLIENT_SECRET={creds.client_secret}")
    print(f"GMAIL_REFRESH_TOKEN={creds.refresh_token}")
    
    return creds

if __name__ == "__main__":
    # Replace with your downloaded credentials file
    credentials_file = "path/to/your/credentials.json"
    generate_refresh_token(credentials_file)
```

Run the script:

```bash
python scripts/generate_gmail_token.py
```

#### Step 6: Configure Environment Variables

Add the OAuth2 credentials to your `.env` file:

```bash
# Gmail OAuth2 Configuration
GMAIL_CLIENT_ID=your_client_id.apps.googleusercontent.com
GMAIL_CLIENT_SECRET=your_client_secret
GMAIL_REFRESH_TOKEN=your_refresh_token

# Primary email account
EMAIL_PRIMARY_ADDRESS=your.email@gmail.com
```

### Option 2: App Password Authentication

App passwords are easier to set up but less secure than OAuth2.

#### Prerequisites

- 2-factor authentication enabled on your Google account

#### Step 1: Enable 2-Factor Authentication

1. Go to [Google Account Security](https://myaccount.google.com/security)
2. Under "Signing in to Google", click "2-Step Verification"
3. Follow the setup process to enable 2FA

#### Step 2: Generate App Password

1. Go to [Google Account Security](https://myaccount.google.com/security)
2. Under "Signing in to Google", click "App passwords"
3. Select "Mail" as the app and "Other" as the device
4. Enter "Data Extraction Pipeline" as the device name
5. Click "Generate"
6. Copy the 16-character app password

#### Step 3: Configure Environment Variables

Add the app password to your `.env` file:

```bash
# Gmail App Password Configuration
EMAIL_PRIMARY_ADDRESS=your.email@gmail.com
EMAIL_PRIMARY_PASSWORD=your_16_character_app_password
```

## Outlook/Hotmail Setup

### App Password Method

#### Step 1: Enable 2-Factor Authentication

1. Go to [Microsoft Account Security](https://account.microsoft.com/security)
2. Click "Advanced security options"
3. Under "Two-step verification", click "Set up two-step verification"
4. Follow the setup process

#### Step 2: Generate App Password

1. In Microsoft Account Security, click "App passwords"
2. Click "Create a new app password"
3. Enter "Data Extraction Pipeline" as the name
4. Copy the generated password

#### Step 3: Configure Environment Variables

```bash
# Outlook Configuration
EMAIL_WORK_ADDRESS=your.email@outlook.com
EMAIL_WORK_PASSWORD=your_app_password
```

#### Step 4: Update Configuration

In your `config.yaml`:

```yaml
email:
  accounts:
    - name: "outlook_account"
      provider: "outlook"
      email: ""  # Will be read from EMAIL_WORK_ADDRESS
      auth_method: "app_password"
      imap_server: "outlook.office365.com"
      imap_port: 993
      use_ssl: true
```

## Yahoo Mail Setup

### App Password Method

#### Step 1: Enable 2-Factor Authentication

1. Go to [Yahoo Account Security](https://login.yahoo.com/account/security)
2. Click "Two-step verification" and follow the setup

#### Step 2: Generate App Password

1. In Yahoo Account Security, click "Generate app password"
2. Select "Other app" and enter "Data Extraction Pipeline"
3. Click "Generate password"
4. Copy the generated password

#### Step 3: Configure Environment Variables

```bash
# Yahoo Configuration
EMAIL_PERSONAL_ADDRESS=your.email@yahoo.com
EMAIL_PERSONAL_PASSWORD=your_app_password
```

#### Step 4: Update Configuration

```yaml
email:
  accounts:
    - name: "yahoo_account"
      provider: "yahoo"
      email: ""  # Will be read from EMAIL_PERSONAL_ADDRESS
      auth_method: "app_password"
      imap_server: "imap.mail.yahoo.com"
      imap_port: 993
      use_ssl: true
```

## Generic IMAP Setup

For other email providers, you can use generic IMAP settings.

### Step 1: Find IMAP Settings

Common IMAP settings for popular providers:

| Provider | IMAP Server | Port | SSL |
|----------|-------------|------|-----|
| Gmail | imap.gmail.com | 993 | Yes |
| Outlook | outlook.office365.com | 993 | Yes |
| Yahoo | imap.mail.yahoo.com | 993 | Yes |
| Apple iCloud | imap.mail.me.com | 993 | Yes |
| Zoho | imap.zoho.com | 993 | Yes |

### Step 2: Configure Account

```yaml
email:
  accounts:
    - name: "custom_provider"
      provider: "custom"
      email: "your.email@provider.com"
      auth_method: "app_password"
      imap_server: "imap.provider.com"
      imap_port: 993
      use_ssl: true
      folders: ["INBOX", "Sent"]
      date_range_days: 30
```

## Multiple Account Configuration

You can configure multiple email accounts:

```yaml
email:
  enabled: true
  accounts:
    # Primary Gmail account with OAuth2
    - name: "primary_gmail"
      provider: "gmail"
      email: ""  # From EMAIL_PRIMARY_ADDRESS
      auth_method: "oauth2"
      oauth2:
        client_id: ""     # From GMAIL_CLIENT_ID
        client_secret: "" # From GMAIL_CLIENT_SECRET
        refresh_token: "" # From GMAIL_REFRESH_TOKEN
      imap_server: "imap.gmail.com"
      imap_port: 993
      use_ssl: true
      folders: ["INBOX", "Sent"]
      date_range_days: 30
      unread_only: false
    
    # Work Outlook account with app password
    - name: "work_outlook"
      provider: "outlook"
      email: ""  # From EMAIL_WORK_ADDRESS
      auth_method: "app_password"
      app_password: ""  # From EMAIL_WORK_PASSWORD
      imap_server: "outlook.office365.com"
      imap_port: 993
      use_ssl: true
      folders: ["INBOX"]
      date_range_days: 7
      unread_only: true
```

## Environment Variables Reference

Complete `.env` file example:

```bash
# Gmail OAuth2 (Primary Account)
GMAIL_CLIENT_ID=123456789.apps.googleusercontent.com
GMAIL_CLIENT_SECRET=your_client_secret
GMAIL_REFRESH_TOKEN=your_refresh_token
EMAIL_PRIMARY_ADDRESS=primary@gmail.com

# Work Email (App Password)
EMAIL_WORK_ADDRESS=work@company.com
EMAIL_WORK_PASSWORD=app_password_here

# Personal Email (App Password)
EMAIL_PERSONAL_ADDRESS=personal@yahoo.com
EMAIL_PERSONAL_PASSWORD=yahoo_app_password
```

## Testing Your Setup

### Test Individual Account

```python
# Test Gmail OAuth2
from pipeline.email.email_extractor import EmailExtractor
from pipeline.utils.config import ConfigManager

config = ConfigManager('config.yaml')
email_configs = config.get_email_configs()

for email_config in email_configs:
    extractor = EmailExtractor(email_config)
    if extractor.connect() and extractor.authenticate():
        print(f"✓ {email_config['name']} connection successful")
    else:
        print(f"✗ {email_config['name']} connection failed")
```

### Test with Pipeline

```bash
# Test all email connections
python -c "
from pipeline.main import PipelineOrchestrator
pipeline = PipelineOrchestrator('config.yaml')
# This will test connections during initialization
"
```

## Troubleshooting

### Common Issues

**1. OAuth2 Authentication Failed**
```
Error: invalid_grant: Token has been expired or revoked
```
- Regenerate your refresh token using the script above
- Ensure your OAuth2 credentials are correct
- Check that the Gmail API is enabled in Google Cloud Console

**2. App Password Authentication Failed**
```
Error: [AUTHENTICATIONFAILED] Invalid credentials
```
- Verify 2-factor authentication is enabled
- Regenerate the app password
- Ensure you're using the app password, not your regular password

**3. IMAP Connection Failed**
```
Error: [Errno 111] Connection refused
```
- Check IMAP server address and port
- Verify SSL/TLS settings
- Ensure IMAP is enabled in your email account settings

**4. Permission Denied**
```
Error: [AUTHENTICATIONFAILED] Please log in via your web browser
```
- This usually indicates 2FA is required
- Set up app passwords or OAuth2 authentication
- Check if "Less secure app access" needs to be enabled (not recommended)

### Debug Mode

Enable debug logging to see detailed connection information:

```bash
# Enable debug mode
DEBUG_MODE=true python -m pipeline.main

# Or in config.yaml
development:
  debug_mode: true
```

### Connection Testing Script

Create a simple test script:

```python
# test_email_connection.py
import imaplib
import ssl

def test_imap_connection(server, port, email, password, use_ssl=True):
    try:
        if use_ssl:
            mail = imaplib.IMAP4_SSL(server, port)
        else:
            mail = imaplib.IMAP4(server, port)
        
        mail.login(email, password)
        mail.select('INBOX')
        
        # Get message count
        status, messages = mail.search(None, 'ALL')
        message_count = len(messages[0].split()) if messages[0] else 0
        
        mail.logout()
        
        print(f"✓ Connection successful! Found {message_count} messages in INBOX")
        return True
        
    except Exception as e:
        print(f"✗ Connection failed: {e}")
        return False

# Test your configuration
if __name__ == "__main__":
    # Replace with your settings
    test_imap_connection(
        server="imap.gmail.com",
        port=993,
        email="your.email@gmail.com",
        password="your_app_password",
        use_ssl=True
    )
```

## Security Best Practices

### Credential Management

1. **Never commit credentials to version control**
2. **Use environment variables for all sensitive data**
3. **Regularly rotate app passwords and tokens**
4. **Use OAuth2 when available (more secure than passwords)**

### Access Control

1. **Use least-privilege principle** - only request necessary scopes
2. **Monitor account access logs** regularly
3. **Enable account security notifications**
4. **Use dedicated email accounts** for automation when possible

### Data Protection

1. **Encrypt stored data** when possible
2. **Implement proper data retention policies**
3. **Follow local privacy regulations** (GDPR, CCPA, etc.)
4. **Secure log files** containing email metadata