# Deployment Guide

This guide provides instructions for deploying the StorySpark Agent to production environments.

## Prerequisites

- Python 3.10 or higher
- Access to target deployment environment
- Google Gemini API key

## Deployment Options

### 1. Deploy to a Linux Server

#### Setup Environment

```bash
# Clone the repository
git clone https://github.com/Nazuna-io/storyspark-agent.git
cd storyspark-agent

# Create virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

#### Configure Environment Variables

```bash
# Create .env file
cp .env.example .env

# Edit .env and add your API key
nano .env
```

#### Set Up systemd Service

Create a systemd service file:

```bash
sudo nano /etc/systemd/system/storyspark-agent.service
```

Add the following content:

```ini
[Unit]
Description=StorySpark Agent
After=network.target

[Service]
Type=simple
User=your-username
WorkingDirectory=/path/to/storyspark-agent
Environment="PATH=/path/to/storyspark-agent/.venv/bin"
ExecStart=/path/to/storyspark-agent/.venv/bin/python /path/to/storyspark-agent/src/main.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

Enable and start the service:

```bash
sudo systemctl enable storyspark-agent
sudo systemctl start storyspark-agent
sudo systemctl status storyspark-agent
```

### 2. Deploy to Docker

#### Create Dockerfile

```dockerfile
FROM python:3.10-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["python", "src/main.py"]
```

#### Build and Run

```bash
# Build the image
docker build -t storyspark-agent .

# Run the container
docker run -d \
  --name storyspark-agent \
  -e GOOGLE_API_KEY=your-api-key \
  -v $(pwd)/data:/app/data \
  -v $(pwd)/logs:/app/logs \
  -v $(pwd)/config.yaml:/app/config.yaml \
  storyspark-agent
```

### 3. Deploy to Cloud Services

#### AWS EC2

1. Launch an EC2 instance (t2.micro is sufficient)
2. SSH into the instance
3. Follow the Linux server deployment steps above
4. Configure security groups to allow outbound HTTPS traffic

#### Google Cloud Run

1. Create a container image using the Dockerfile above
2. Push to Google Container Registry
3. Deploy to Cloud Run:

```bash
gcloud run deploy storyspark-agent \
  --image gcr.io/your-project/storyspark-agent \
  --set-env-vars GOOGLE_API_KEY=your-api-key \
  --region us-central1
```

#### Heroku

1. Create a `Procfile`:
```
worker: python src/main.py
```

2. Deploy:
```bash
heroku create storyspark-agent
heroku config:set GOOGLE_API_KEY=your-api-key
git push heroku main
heroku ps:scale worker=1
```

## Configuration

### Production Config

Update `config.yaml` for production:

```yaml
agent:
  run_immediately_on_start: false
  schedule_interval_minutes: 60  # Run every hour
  max_sparks_per_cycle: 10

logging:
  level: INFO
  log_file: logs/storyspark_production.log

sources:
  rss_feeds:
    - url: "https://techcrunch.com/feed/"
    - url: "https://www.theverge.com/rss/index.xml"
  subreddits:
    - name: "technology"
    - name: "science"
```

### Monitoring

#### Log Monitoring

Monitor the application logs:

```bash
# For systemd service
sudo journalctl -u storyspark-agent -f

# For Docker
docker logs -f storyspark-agent

# Application logs
tail -f logs/storyspark_production.log
```

#### Health Checks

Add a health check endpoint or monitoring script:

```python
# health_check.py
import os
import json
from datetime import datetime, timedelta

def check_health():
    # Check if the agent has run recently
    state_file = 'data/fetcher_state.json'

    if not os.path.exists(state_file):
        return False, "State file not found"

    with open(state_file) as f:
        state = json.load(f)

    # Check if any source was updated in the last 2 hours
    cutoff = datetime.now() - timedelta(hours=2)
    for timestamp in state.get('last_timestamps', {}).values():
        if timestamp and datetime.fromisoformat(timestamp) > cutoff:
            return True, "Agent is running"

    return False, "Agent has not updated recently"

if __name__ == "__main__":
    healthy, message = check_health()
    print(f"Health: {'OK' if healthy else 'ERROR'} - {message}")
    exit(0 if healthy else 1)
```

### Backup and Recovery

#### Backup Data

Regularly backup the data directory:

```bash
# Create backup
tar -czf backup-$(date +%Y%m%d).tar.gz data/

# Copy to S3 or other storage
aws s3 cp backup-*.tar.gz s3://your-backup-bucket/
```

#### Restore from Backup

```bash
# Download backup
aws s3 cp s3://your-backup-bucket/backup-20240101.tar.gz .

# Extract
tar -xzf backup-20240101.tar.gz

# Restart service
sudo systemctl restart storyspark-agent
```

## Security

### Network Security

- Use HTTPS for all external API calls (already implemented)
- Restrict outbound traffic to required domains only
- Use a firewall to block unnecessary ports

### API Key Management

For production, consider using:
- AWS Secrets Manager
- Google Secret Manager
- Hashicorp Vault
- Environment-specific key rotation

### File Permissions

```bash
# Restrict permissions on sensitive files
chmod 600 .env
chmod 600 config.yaml
chmod 700 data/
```

## Troubleshooting

### Common Issues

1. **Agent not running**
   - Check logs for errors
   - Verify API key is set correctly
   - Ensure network connectivity

2. **High memory usage**
   - Reduce history window in config
   - Limit number of sources
   - Add memory limits to Docker container

3. **API rate limits**
   - Increase schedule interval
   - Reduce number of sources
   - Implement exponential backoff

### Debug Mode

Enable debug logging for troubleshooting:

```yaml
logging:
  level: DEBUG
```

## Performance Optimization

### Scaling

For high-volume processing:

1. Run multiple instances with different source configurations
2. Use a message queue (Redis/RabbitMQ) for distributed processing
3. Implement caching for frequent API calls

### Resource Limits

Set resource limits for containers:

```bash
docker run -d \
  --memory="512m" \
  --cpus="0.5" \
  storyspark-agent
```

## Maintenance

### Regular Tasks

1. **Weekly**: Check logs for errors
2. **Monthly**: Update dependencies (`pip-audit`)
3. **Quarterly**: Review and update source configurations
4. **Yearly**: Major version updates and security audit

### Monitoring Checklist

- [ ] Service is running
- [ ] Logs show successful runs
- [ ] Output files are being generated
- [ ] API rate limits are not exceeded
- [ ] Disk space is sufficient
- [ ] Memory usage is stable

## Support

For issues or questions:
1. Check logs for error messages
2. Review configuration settings
3. Consult the main README
4. Submit issues on GitHub
