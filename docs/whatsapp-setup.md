# WhatsApp API Setup Guide

This guide walks you through setting up WhatsApp API credentials for the data extraction pipeline. The pipeline supports both WhatsApp Business API (Meta/Facebook) and Twilio WhatsApp API.

## Option 1: WhatsApp Business API (Recommended)

The WhatsApp Business API is the official API provided by Meta (Facebook) and offers the most reliable access to WhatsApp data.

### Prerequisites

- A Facebook Developer account
- A verified business phone number
- WhatsApp Business account

### Step 1: Create Facebook Developer Account

1. Go to [Facebook Developers](https://developers.facebook.com/)
2. Click "Get Started" and log in with your Facebook account
3. Complete the developer account verification process

### Step 2: Create a New App

1. Click "Create App" in the Facebook Developer dashboard
2. Select "Business" as the app type
3. Fill in your app details:
   - **App Name**: Choose a descriptive name (e.g., "Data Extraction Pipeline")
   - **App Contact Email**: Your business email
   - **Business Account**: Select or create a business account

### Step 3: Add WhatsApp Product

1. In your app dashboard, click "Add Product"
2. Find "WhatsApp" and click "Set Up"
3. You'll be redirected to the WhatsApp setup page

### Step 4: Configure WhatsApp Business API

1. **Add Phone Number**:
   - Click "Add phone number"
   - Enter your business phone number
   - Verify the number via SMS or call

2. **Get Phone Number ID**:
   - After verification, you'll see your Phone Number ID
   - Copy this ID - you'll need it for configuration

3. **Generate Access Token**:
   - In the WhatsApp setup page, find the "Access Tokens" section
   - Click "Generate Token"
   - Copy the temporary token (valid for 24 hours)

### Step 5: Create Permanent Access Token

For production use, you need a permanent access token:

1. Go to "App Settings" > "Basic"
2. Copy your App ID and App Secret
3. Use the Graph API Explorer or make a direct API call:

```bash
curl -X GET "https://graph.facebook.com/v18.0/oauth/access_token" \
  -d "grant_type=client_credentials" \
  -d "client_id=YOUR_APP_ID" \
  -d "client_secret=YOUR_APP_SECRET"
```

### Step 6: Set Up Webhook (Optional)

If you want real-time message notifications:

1. In WhatsApp setup, go to "Configuration"
2. Add your webhook URL
3. Set a verify token (you'll use this in configuration)
4. Subscribe to message events

### Step 7: Configure Environment Variables

Add these to your `.env` file:

```bash
# WhatsApp Business API Configuration
WHATSAPP_ACCESS_TOKEN=your_permanent_access_token_here
WHATSAPP_PHONE_NUMBER_ID=your_phone_number_id_here
WHATSAPP_WEBHOOK_VERIFY_TOKEN=your_webhook_verify_token_here
```

### Step 8: Test Your Setup

Test your configuration with a simple API call:

```bash
curl -X GET "https://graph.facebook.com/v18.0/YOUR_PHONE_NUMBER_ID" \
  -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
```

## Option 2: Twilio WhatsApp API

Twilio provides an alternative WhatsApp API that's easier to set up but may have different limitations.

### Prerequisites

- A Twilio account
- A verified phone number

### Step 1: Create Twilio Account

1. Go to [Twilio Console](https://console.twilio.com/)
2. Sign up for a new account or log in
3. Complete phone number verification

### Step 2: Set Up WhatsApp Sandbox

1. In the Twilio Console, navigate to "Messaging" > "Try it out" > "Send a WhatsApp message"
2. Follow the sandbox setup instructions
3. Send "join [sandbox-name]" to the Twilio WhatsApp number from your phone

### Step 3: Get API Credentials

1. In the Twilio Console, go to "Account" > "API keys & tokens"
2. Copy your Account SID and Auth Token
3. Note the Twilio WhatsApp sandbox number (usually +1 415 523 8886)

### Step 4: Configure Environment Variables

Add these to your `.env` file:

```bash
# Twilio WhatsApp API Configuration
TWILIO_ACCOUNT_SID=your_account_sid_here
TWILIO_AUTH_TOKEN=your_auth_token_here
TWILIO_WHATSAPP_NUMBER=whatsapp:+14155238886
```

### Step 5: Update Configuration

In your `config.yaml`, set the API provider to Twilio:

```yaml
whatsapp:
  enabled: true
  api_provider: "twilio"
```

### Step 6: Test Your Setup

Test with the Twilio API:

```bash
curl -X GET "https://api.twilio.com/2010-04-01/Accounts/YOUR_ACCOUNT_SID/Messages.json" \
  -u "YOUR_ACCOUNT_SID:YOUR_AUTH_TOKEN"
```

## Configuration Examples

### Complete WhatsApp Configuration

```yaml
# config.yaml
whatsapp:
  enabled: true
  api_provider: "business_api"  # or "twilio"
  
  business_api:
    api_version: "v18.0"
    base_url: "https://graph.facebook.com"
  
  twilio:
    base_url: "https://api.twilio.com/2010-04-01"
  
  rate_limit:
    requests_per_minute: 60
    retry_attempts: 3
    backoff_factor: 2
```

## Troubleshooting

### Common Issues

**1. Invalid Access Token**
```
Error: (#100) Invalid parameter
```
- Verify your access token is correct and not expired
- Ensure you're using a permanent token, not a temporary one
- Check that your app has the necessary permissions

**2. Phone Number Not Verified**
```
Error: Phone number not verified
```
- Complete the phone number verification process in Facebook Developer Console
- Ensure the phone number is associated with a WhatsApp Business account

**3. Rate Limiting**
```
Error: (#4) Application request limit reached
```
- You've exceeded the API rate limits
- Wait for the rate limit to reset (usually 1 hour)
- Consider upgrading your Facebook app for higher limits

**4. Webhook Verification Failed**
```
Error: Webhook verification failed
```
- Check that your webhook URL is accessible from the internet
- Verify that your webhook verify token matches the configuration
- Ensure your webhook endpoint returns the challenge correctly

### Testing Your Setup

Use the pipeline's built-in test functionality:

```bash
# Test WhatsApp connection
python -c "
from pipeline.whatsapp.whatsapp_extractor import WhatsAppExtractor
from pipeline.utils.config import ConfigManager

config = ConfigManager('config.yaml')
extractor = WhatsAppExtractor(config.get_whatsapp_config())
if extractor.authenticate():
    print('WhatsApp authentication successful!')
else:
    print('WhatsApp authentication failed!')
"
```

## Rate Limits and Best Practices

### WhatsApp Business API Limits

- **Messages**: 1,000 messages per day (can be increased)
- **API Calls**: 4,000 calls per hour per app
- **Media Downloads**: Limited by file size and frequency

### Twilio Limits

- **Sandbox**: Limited number of pre-approved recipients
- **Production**: Based on your Twilio plan
- **API Calls**: Rate limited based on account type

### Best Practices

1. **Use Permanent Tokens**: Always use permanent access tokens for production
2. **Implement Rate Limiting**: The pipeline includes built-in rate limiting
3. **Handle Errors Gracefully**: The pipeline automatically retries failed requests
4. **Monitor Usage**: Keep track of your API usage in the respective consoles
5. **Secure Credentials**: Never commit API credentials to version control

## Production Considerations

### Security

- Store credentials in environment variables, never in code
- Use HTTPS for all webhook endpoints
- Regularly rotate access tokens
- Monitor for unauthorized API usage

### Scaling

- Consider using multiple phone numbers for higher throughput
- Implement proper error handling and retry logic
- Monitor API quotas and upgrade plans as needed
- Use webhook subscriptions for real-time processing

### Compliance

- Ensure compliance with WhatsApp Business Policy
- Implement proper data retention policies
- Handle user privacy and consent appropriately
- Follow local data protection regulations (GDPR, CCPA, etc.)