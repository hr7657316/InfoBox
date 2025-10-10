# Data Extraction Pipeline - Deployment Guide

## Overview

This guide covers the deployment of the Data Extraction Pipeline using Docker and the provided deployment scripts.

## Prerequisites

- Docker and Docker Compose installed
- Python 3.8+ (for local development)
- Valid API credentials for WhatsApp and/or Email services

## Quick Start

### 1. Setup Environment

```bash
# Clone and setup the project
git clone <repository-url>
cd data-extraction-pipeline

# Run setup script
./scripts/setup.sh
```

### 2. Configure Credentials

```bash
# Copy environment template
cp .env.example .env

# Edit .env with your actual credentials
nano .env
```

### 3. Deploy with Docker

```bash
# Full deployment
./scripts/deploy.sh

# Or individual commands
./scripts/deploy.sh build    # Build image only
./scripts/deploy.sh start    # Start containers
./scripts/deploy.sh test     # Run test extraction
```

## Configuration

### Environment Variables

Key environment variables to configure in `.env`:

```bash
# WhatsApp Business API
WHATSAPP_ACCESS_TOKEN=your_token_here
WHATSAPP_PHONE_NUMBER_ID=your_phone_id_here

# Gmail OAuth2
GMAIL_CLIENT_ID=your_client_id_here
GMAIL_CLIENT_SECRET=your_client_secret_here
GMAIL_REFRESH_TOKEN=your_refresh_token_here

# Email Account
EMAIL_PRIMARY_ADDRESS=your.email@gmail.com
```

### Configuration File

Edit `config.yaml` to customize:

- Data sources (WhatsApp/Email)
- Storage settings
- Logging configuration
- Notification preferences
- Error handling behavior

## Deployment Options

### Docker Compose (Recommended)

```bash
# Start all services
docker-compose up -d

# View logs
docker-compose logs -f

# Stop services
docker-compose down
```

### Manual Docker

```bash
# Build image
docker build -t data-extraction-pipeline .

# Run container
docker run -d \
  --name pipeline \
  -v $(pwd)/data:/app/data \
  -v $(pwd)/logs:/app/logs \
  -v $(pwd)/config.yaml:/app/config.yaml:ro \
  -v $(pwd)/.env:/app/.env:ro \
  data-extraction-pipeline
```

### Local Python

```bash
# Activate virtual environment
source venv/bin/activate

# Run pipeline
python run_pipeline.py --config config.yaml
```

## Validation and Testing

### Configuration Validation

```bash
# Test configuration
python run_pipeline.py --config config.yaml --validate-only

# Test with mock data
python run_pipeline.py --config config.test.yaml --mock-mode
```

### Docker Testing

```bash
# Test deployment
./scripts/deploy.sh test

# Check container health
docker-compose ps
docker-compose exec pipeline python run_pipeline.py --validate-only
```

## Monitoring and Maintenance

### Logs

```bash
# View application logs
tail -f logs/pipeline.log

# View Docker logs
docker-compose logs -f pipeline
```

### Health Checks

The pipeline includes built-in health checks:

- Container health check every 30 seconds
- Configuration validation on startup
- Graceful error handling and recovery

### Data Management

```bash
# Data is stored in ./data directory
ls -la data/

# Backup data
tar -czf backup-$(date +%Y%m%d).tar.gz data/

# Clean old data (optional)
find data/ -type f -mtime +30 -delete
```

## Troubleshooting

### Common Issues

1. **Authentication Failures**
   - Verify API credentials in `.env`
   - Check token expiration
   - Validate OAuth2 setup

2. **Permission Errors**
   - Ensure data/logs directories are writable
   - Check Docker volume permissions

3. **Network Issues**
   - Verify internet connectivity
   - Check firewall settings
   - Validate API endpoints

### Debug Mode

```bash
# Enable debug logging
export LOG_LEVEL=DEBUG

# Run with verbose output
python run_pipeline.py --config config.yaml --validate-only
```

### Support

- Check logs in `logs/pipeline.log`
- Review configuration validation errors
- Consult API documentation for credential setup
- Use mock mode for testing without real credentials

## Security Considerations

- Never commit `.env` file to version control
- Use strong, unique API tokens
- Regularly rotate credentials
- Monitor access logs
- Use read-only mounts for configuration files
- Run containers as non-root user (default)

## Performance Tuning

### Resource Limits

Adjust in `docker-compose.yml`:

```yaml
deploy:
  resources:
    limits:
      memory: 512M
      cpus: '0.5'
```

### Batch Processing

Configure in `config.yaml`:

```yaml
performance:
  batch_size: 100
  max_concurrent_accounts: 3
  max_concurrent_downloads: 5
```

## Scaling

### Multiple Instances

```bash
# Scale pipeline service
docker-compose up -d --scale pipeline=3
```

### Scheduled Execution

```bash
# Add to crontab for regular execution
0 2 * * * cd /path/to/pipeline && ./scripts/deploy.sh test
```

## Backup and Recovery

### Data Backup

```bash
# Automated backup script
#!/bin/bash
DATE=$(date +%Y%m%d_%H%M%S)
tar -czf "backup_${DATE}.tar.gz" data/ logs/ config.yaml
```

### Configuration Backup

```bash
# Backup configuration
cp config.yaml "config.backup.$(date +%Y%m%d).yaml"
cp .env ".env.backup.$(date +%Y%m%d)"
```

## Updates and Maintenance

### Updating the Pipeline

```bash
# Pull latest changes
git pull origin main

# Rebuild and redeploy
./scripts/deploy.sh

# Or manual update
docker-compose down
docker-compose build --no-cache
docker-compose up -d
```

### Maintenance Tasks

- Regular log rotation
- Data cleanup (if needed)
- Credential rotation
- Dependency updates
- Security patches