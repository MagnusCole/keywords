# 📦 Deployment Guide - Enterprise Production

## 🚀 Deployment Options

### Option 1: Docker Container (Recommended)

```dockerfile
# Dockerfile
FROM python:3.11-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .
EXPOSE 8000

CMD ["python", "main.py", "--api-mode"]
```

```bash
# Build and deploy
docker build -t keyword-finder:enterprise .
docker run -d -p 8000:8000 --env-file .env keyword-finder:enterprise
```

### Option 2: Cloud Deployment (AWS/Azure/GCP)

```yaml
# docker-compose.yml
version: '3.8'
services:
  keyword-finder:
    build: .
    ports:
      - "8000:8000"
    environment:
      - DEFAULT_COUNTRY=PE
      - TARGET_INTENT=transactional
    volumes:
      - ./exports:/app/exports
      - ./keywords.db:/app/keywords.db
```

### Option 3: Local Enterprise Server

```bash
# Production setup
python -m venv .venv-prod
.venv-prod\Scripts\activate
pip install -r requirements.txt
cp .env.example .env

# Configure production settings in .env
# Run as service
python main.py --server-mode
```

## 🔧 Production Configuration

### Environment Variables
```bash
# .env production
DEFAULT_COUNTRY=PE
TARGET_INTENT=transactional
PARALLEL_SEMAPHORE_LIMIT=5
HTTP2_ENABLED=true
BROTLI_COMPRESSION=true

# Performance tuning
REQUEST_DELAY_MIN=0.5
REQUEST_DELAY_MAX=1.5
MAX_RETRIES=3
```

### Database Configuration
```python
# Production SQLite settings
DATABASE_PATH=/data/keywords_prod.db
BACKUP_INTERVAL=3600  # 1 hour
MAX_DB_SIZE_MB=500
```

## 📊 Monitoring & Observability

### Health Checks
```bash
# Basic health check
curl http://localhost:8000/health

# Detailed status
python reliability_analysis.py --json > health_status.json
```

### Performance Monitoring
```python
# Built-in metrics
{
    "keywords_per_second": 7.2,
    "http2_active": true,
    "memory_usage_mb": 45,
    "success_rate": 0.89,
    "avg_response_time_ms": 850
}
```

### Logging Configuration
```python
# Production logging
import logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(levelname)s %(name)s %(message)s',
    handlers=[
        logging.FileHandler('/var/log/keyword-finder.log'),
        logging.StreamHandler()
    ]
)
```

## 🔒 Security Hardening

### Rate Limiting
```python
# Built-in rate limiting
RATE_LIMIT_REQUESTS_PER_MINUTE = 60
RATE_LIMIT_BURST = 10
```

### Input Validation
```python
# Automatic input sanitization
- SQL injection protection
- XSS prevention
- File path traversal protection
- Rate limiting per IP
```

### Network Security
```bash
# Firewall rules
iptables -A INPUT -p tcp --dport 8000 -s trusted_network -j ACCEPT
iptables -A INPUT -p tcp --dport 8000 -j DROP

# SSL/TLS (recommended)
nginx reverse proxy with SSL certificate
```

## 📈 Scaling & Performance

### Horizontal Scaling
```yaml
# Kubernetes deployment
apiVersion: apps/v1
kind: Deployment
metadata:
  name: keyword-finder
spec:
  replicas: 3
  selector:
    matchLabels:
      app: keyword-finder
  template:
    spec:
      containers:
      - name: keyword-finder
        image: keyword-finder:enterprise
        resources:
          requests:
            memory: "512Mi"
            cpu: "500m"
          limits:
            memory: "1Gi"
            cpu: "1000m"
```

### Load Balancing
```nginx
# nginx.conf
upstream keyword_finder {
    server 127.0.0.1:8001;
    server 127.0.0.1:8002;
    server 127.0.0.1:8003;
}

server {
    listen 80;
    location / {
        proxy_pass http://keyword_finder;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

## 🔄 CI/CD Pipeline

### GitHub Actions
```yaml
# .github/workflows/deploy.yml
name: Deploy to Production
on:
  push:
    branches: [main]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
    - uses: actions/checkout@v3
    - name: Set up Python
      uses: actions/setup-python@v4
      with:
        python-version: '3.11'
    - name: Install dependencies
      run: pip install -r requirements-dev.txt
    - name: Run tests
      run: |
        ruff check .
        black --check .
        python test_improvements.py
        python reliability_analysis.py
    - name: Deploy
      if: success()
      run: |
        docker build -t keyword-finder:${{ github.sha }} .
        docker push registry/keyword-finder:${{ github.sha }}
```

## 🛠️ Maintenance & Operations

### Backup Strategy
```bash
# Daily backup
#!/bin/bash
DATE=$(date +%Y%m%d)
cp keywords.db backups/keywords_$DATE.db
tar -czf backups/exports_$DATE.tar.gz exports/

# Cleanup old backups (keep 30 days)
find backups/ -name "*.db" -mtime +30 -delete
```

### Health Monitoring
```bash
# Monitoring script
#!/bin/bash
RESPONSE=$(curl -s -o /dev/null -w "%{http_code}" http://localhost:8000/health)
if [ $RESPONSE -ne 200 ]; then
    echo "Service down, restarting..."
    systemctl restart keyword-finder
fi
```

### Performance Tuning
```python
# Production optimizations
- HTTP/2 connection pooling
- Async semaphore tuning: 3-7 concurrent requests
- Memory usage monitoring
- Database connection pooling
- Response caching for repeated queries
```

## 🚨 Troubleshooting

### Common Issues
```bash
# Memory issues
# Solution: Reduce PARALLEL_SEMAPHORE_LIMIT

# Rate limiting
# Solution: Increase REQUEST_DELAY_MIN/MAX

# Database locks
# Solution: Enable WAL mode in SQLite

# Network timeouts
# Solution: Adjust HTTP timeout settings
```

### Debug Mode
```bash
# Enable debug logging
export LOG_LEVEL=DEBUG
python main.py --debug --seeds "test"

# Performance profiling
python -m cProfile main.py --seeds "test" > profile.txt
```

---

**Enterprise Deployment Guide v1.0** | **Production Ready**