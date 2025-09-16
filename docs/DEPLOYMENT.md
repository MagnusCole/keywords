# Production Deployment Guide v2.0.0

This guide covers deploying the Keyword Finder system in production environments with enterprise-grade standards.

## 📋 Prerequisites

### System Requirements

**Minimum Specifications:**
- CPU: 4 cores, 2.5GHz+
- RAM: 8GB (16GB recommended)
- Storage: 50GB SSD
- Network: Stable internet, 100Mbps+

**Operating System:**
- Ubuntu 22.04 LTS (recommended)
- CentOS 8+ / RHEL 8+
- Windows Server 2019+
- macOS 12+ (development only)

**Software Dependencies:**
- Python 3.11+ 
- Git 2.30+
- systemd (Linux) or equivalent service manager
- Reverse proxy (nginx/Apache) for web interfaces
- Log aggregation system (ELK Stack, Fluentd, etc.)

### Required Services

**External APIs:**
- Google Ads API access (optional, for real volume data)
- Google Cloud Platform project (for Trends API)

**Monitoring & Observability:**
- Log aggregation system
- Application performance monitoring (APM)
- Health check endpoints
- Alerting system

## 🚀 Production Setup

### 1. System Preparation

```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install Python 3.11+
sudo apt install python3.11 python3.11-venv python3.11-dev

# Install system dependencies
sudo apt install build-essential curl git nginx

# Create application user
sudo useradd -m -s /bin/bash keyword-intel
sudo usermod -aG sudo keyword-intel
```

### 2. Application Deployment

```bash
# Switch to application user
sudo su - keyword-intel

# Clone repository
git clone https://github.com/username/keyword-finder.git
cd keyword-finder

# Create production environment
python3.11 -m venv venv-prod
source venv-prod/bin/activate

# Install dependencies
pip install --upgrade pip
pip install -r requirements.txt

# Install production-only dependencies
pip install psutil gunicorn supervisor
```

### 3. Configuration Setup

```bash
# Create production configuration
mkdir -p /opt/keyword-intel/config
cp config/config.yaml /opt/keyword-intel/config/

# Set production profile
export KEYWORD_INTEL_PROFILE=production
export ENVIRONMENT=production
```

**Production Configuration (`/opt/keyword-intel/config/config.yaml`):**

```yaml
project:
  name: "keyword-intel"
  version: "2.0.0"

# Production run settings
run:
  geo: "PE"
  language: "es"
  target:
    raw: 5000
    filtered: 1000
    clusters: 50

# Performance optimization
expansion:
  limit_per_seed: 500
  parallel_workers: 4
  batch_size: 100

# Production data sources
sources:
  trends: true
  ads_volume: true
  rate_limit_enabled: true
  cache_ttl: 3600

# Strict filtering
filters:
  min_score: 50
  max_competition: 0.6
  quality_threshold: 70

# Production logging
logging:
  level: "INFO"
  json_format: true
  console_enabled: false
  file_enabled: true
  filepath: "/var/log/keyword-intel/app.jsonl"
  rotation_size: "100MB"
  backup_count: 10
  correlation_enabled: true
  performance_metrics: true

# Export settings
exports:
  directory: "/var/data/keyword-intel/exports"
  format: "csv"
  transparency_mode: false
  compression: true
  retention_days: 30

# Database configuration
database:
  path: "/var/data/keyword-intel/keywords.db"
  backup_enabled: true
  backup_interval: "daily"
  backup_retention: 7
  wal_mode: true
  foreign_keys: true

# ML pipeline optimization
ml:
  embeddings:
    model_name: "sentence-transformers/all-MiniLM-L6-v2"
    cache_enabled: true
    cache_path: "/var/cache/keyword-intel/embeddings"
  clustering:
    deterministic: true
    random_state: 42
```

### 4. Directory Structure

```bash
# Create production directories
sudo mkdir -p /opt/keyword-intel/{config,data,logs,cache,exports}
sudo mkdir -p /var/log/keyword-intel
sudo mkdir -p /var/data/keyword-intel/{exports,backups}
sudo mkdir -p /var/cache/keyword-intel

# Set permissions
sudo chown -R keyword-intel:keyword-intel /opt/keyword-intel
sudo chown -R keyword-intel:keyword-intel /var/log/keyword-intel
sudo chown -R keyword-intel:keyword-intel /var/data/keyword-intel
sudo chown -R keyword-intel:keyword-intel /var/cache/keyword-intel
```

### 5. Environment Variables

Create `/opt/keyword-intel/.env`:

```bash
# Application settings
ENVIRONMENT=production
KEYWORD_INTEL_PROFILE=production
KEYWORD_INTEL_CONFIG=/opt/keyword-intel/config/config.yaml

# Google Ads API (if enabled)
GOOGLE_ADS_DEVELOPER_TOKEN=your_token_here
GOOGLE_ADS_CLIENT_ID=your_client_id
GOOGLE_ADS_CLIENT_SECRET=your_client_secret
GOOGLE_ADS_REFRESH_TOKEN=your_refresh_token
GOOGLE_ADS_CUSTOMER_ID=your_customer_id

# Performance optimization
PYTHONOPTIMIZE=1
PYTHONUNBUFFERED=1

# Logging
LOG_LEVEL=INFO
LOG_FORMAT=json

# Security
UMASK=0027
```

## 🔧 Service Management

### 1. Systemd Service

Create `/etc/systemd/system/keyword-intel.service`:

```ini
[Unit]
Description=Keyword Intel Service
After=network.target
Wants=network.target

[Service]
Type=simple
User=keyword-intel
Group=keyword-intel
WorkingDirectory=/opt/keyword-intel
Environment=PATH=/opt/keyword-intel/venv-prod/bin
EnvironmentFile=/opt/keyword-intel/.env
ExecStart=/opt/keyword-intel/venv-prod/bin/python main.py --profile production
ExecReload=/bin/kill -HUP $MAINPID
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal
SyslogIdentifier=keyword-intel

# Security settings
NoNewPrivileges=yes
PrivateTmp=yes
ProtectSystem=strict
ProtectHome=yes
ReadWritePaths=/var/log/keyword-intel /var/data/keyword-intel /var/cache/keyword-intel

[Install]
WantedBy=multi-user.target
```

### 2. Service Operations

```bash
# Enable and start service
sudo systemctl enable keyword-intel
sudo systemctl start keyword-intel

# Check status
sudo systemctl status keyword-intel

# View logs
sudo journalctl -u keyword-intel -f

# Restart service
sudo systemctl restart keyword-intel

# Stop service
sudo systemctl stop keyword-intel
```

## 📊 Monitoring & Observability

### 1. Health Checks

Create health check endpoint:

```python
# health_check.py
#!/opt/keyword-intel/venv-prod/bin/python

import json
import sys
from pathlib import Path
from src.db.database import KeywordDatabase
from src.platform.enhanced_logging import get_structured_logger

def health_check():
    """Comprehensive health check for production monitoring."""
    logger = get_structured_logger(__name__)
    health_status = {
        "status": "healthy",
        "timestamp": "2025-09-16T10:43:27Z",
        "version": "2.0.0",
        "checks": {}
    }
    
    try:
        # Database connectivity
        db = KeywordDatabase()
        db_stats = db.get_stats()
        health_status["checks"]["database"] = {
            "status": "healthy",
            "total_keywords": db_stats.get("total_keywords", 0),
            "last_run": db_stats.get("last_run_time")
        }
        
        # Disk space
        import shutil
        disk_usage = shutil.disk_usage("/var/data/keyword-intel")
        free_gb = disk_usage.free / (1024**3)
        health_status["checks"]["disk_space"] = {
            "status": "healthy" if free_gb > 10 else "warning",
            "free_gb": round(free_gb, 2)
        }
        
        # Memory usage
        import psutil
        memory = psutil.virtual_memory()
        health_status["checks"]["memory"] = {
            "status": "healthy" if memory.percent < 80 else "warning",
            "usage_percent": memory.percent
        }
        
        # Log file accessibility
        log_path = Path("/var/log/keyword-intel/app.jsonl")
        health_status["checks"]["logging"] = {
            "status": "healthy" if log_path.exists() else "error",
            "log_file_exists": log_path.exists()
        }
        
    except Exception as e:
        health_status["status"] = "unhealthy"
        health_status["error"] = str(e)
        logger.error("Health check failed", error=str(e))
    
    return health_status

if __name__ == "__main__":
    health = health_check()
    print(json.dumps(health, indent=2))
    sys.exit(0 if health["status"] == "healthy" else 1)
```

### 2. Log Rotation

Configure logrotate (`/etc/logrotate.d/keyword-intel`):

```bash
/var/log/keyword-intel/*.log /var/log/keyword-intel/*.jsonl {
    daily
    rotate 30
    compress
    delaycompress
    missingok
    notifempty
    create 0644 keyword-intel keyword-intel
    postrotate
        systemctl reload keyword-intel > /dev/null 2>&1 || true
    endscript
}
```

### 3. Monitoring Metrics

Key metrics to monitor:

```yaml
# Application metrics
- keywords_processed_per_hour
- clustering_success_rate
- scoring_accuracy
- export_completion_rate

# Performance metrics  
- response_time_p95
- memory_usage_percent
- disk_usage_percent
- cpu_utilization

# Error metrics
- error_rate_per_hour
- network_timeout_count
- database_error_count
- api_failure_rate

# Business metrics
- keyword_quality_score
- cluster_distribution
- market_coverage
- data_freshness
```

## 🔐 Security Hardening

### 1. File Permissions

```bash
# Secure configuration files
sudo chmod 600 /opt/keyword-intel/.env
sudo chmod 640 /opt/keyword-intel/config/config.yaml

# Secure log files
sudo chmod 640 /var/log/keyword-intel/*.log

# Secure data directory
sudo chmod 750 /var/data/keyword-intel
```

### 2. Network Security

```bash
# Firewall configuration (ufw)
sudo ufw allow 22/tcp      # SSH
sudo ufw allow 80/tcp      # HTTP (if web interface)
sudo ufw allow 443/tcp     # HTTPS (if web interface)
sudo ufw enable

# Fail2ban for SSH protection
sudo apt install fail2ban
sudo systemctl enable fail2ban
```

### 3. API Security

```yaml
# In config.yaml
security:
  api_rate_limiting: true
  request_timeout: 30
  max_connections: 100
  ip_whitelist:
    - "10.0.0.0/8"
    - "192.168.0.0/16"
```

## 🔄 Backup & Recovery

### 1. Database Backup

Create backup script (`/opt/keyword-intel/scripts/backup.sh`):

```bash
#!/bin/bash

BACKUP_DIR="/var/data/keyword-intel/backups"
DB_PATH="/var/data/keyword-intel/keywords.db"
DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="$BACKUP_DIR/keywords_backup_$DATE.db"

# Create backup
sqlite3 "$DB_PATH" ".backup '$BACKUP_FILE'"

# Compress backup
gzip "$BACKUP_FILE"

# Cleanup old backups (keep last 7 days)
find "$BACKUP_DIR" -name "keywords_backup_*.db.gz" -mtime +7 -delete

echo "Backup completed: $BACKUP_FILE.gz"
```

### 2. Automated Backups

Add to crontab:

```bash
# Daily backup at 2 AM
0 2 * * * /opt/keyword-intel/scripts/backup.sh

# Weekly configuration backup
0 3 * * 0 tar -czf /var/data/keyword-intel/backups/config_$(date +\%Y\%m\%d).tar.gz /opt/keyword-intel/config/
```

### 3. Recovery Procedures

```bash
# Database recovery
sudo systemctl stop keyword-intel
gunzip /var/data/keyword-intel/backups/keywords_backup_YYYYMMDD_HHMMSS.db.gz
cp /var/data/keyword-intel/backups/keywords_backup_YYYYMMDD_HHMMSS.db /var/data/keyword-intel/keywords.db
sudo systemctl start keyword-intel

# Configuration recovery
tar -xzf /var/data/keyword-intel/backups/config_YYYYMMDD.tar.gz -C /
sudo systemctl restart keyword-intel
```

## 📈 Performance Optimization

### 1. Python Optimization

```bash
# Use optimized Python
export PYTHONOPTIMIZE=2

# Precompile bytecode
python -m compileall /opt/keyword-intel/src/

# Enable garbage collection optimization
export PYTHONGC=1
```

### 2. Database Optimization

```sql
-- SQLite optimization
PRAGMA journal_mode = WAL;
PRAGMA synchronous = NORMAL;
PRAGMA cache_size = -64000;  -- 64MB cache
PRAGMA temp_store = MEMORY;
PRAGMA mmap_size = 268435456; -- 256MB mmap
```

### 3. System Optimization

```bash
# Increase file descriptor limits
echo "keyword-intel soft nofile 65536" >> /etc/security/limits.conf
echo "keyword-intel hard nofile 65536" >> /etc/security/limits.conf

# Optimize kernel parameters
echo "vm.swappiness = 10" >> /etc/sysctl.conf
echo "net.core.somaxconn = 1024" >> /etc/sysctl.conf
```

## 🚨 Troubleshooting

### Common Issues

1. **Memory exhaustion**:
   ```bash
   # Check memory usage
   free -h
   ps aux --sort=-%mem | head -10
   
   # Reduce batch size in config
   processing:
     batch_size: 50  # Reduce from 100
   ```

2. **Database locks**:
   ```bash
   # Check for long-running transactions
   sqlite3 keywords.db ".timeout 30000"
   
   # Enable WAL mode
   sqlite3 keywords.db "PRAGMA journal_mode=WAL;"
   ```

3. **API rate limits**:
   ```yaml
   # Increase delays in config
   sources:
     rate_limit_delay: 2.0  # Increase from 1.0
     max_retries: 5
   ```

### Log Analysis

```bash
# View recent errors
journalctl -u keyword-intel --since "1 hour ago" | grep ERROR

# Monitor performance
tail -f /var/log/keyword-intel/app.jsonl | jq '.performance'

# Count error types
grep ERROR /var/log/keyword-intel/app.jsonl | jq '.error.category' | sort | uniq -c
```

### Recovery Commands

```bash
# Emergency restart
sudo systemctl restart keyword-intel

# Force stop and cleanup
sudo systemctl stop keyword-intel
sudo killall python
sudo systemctl start keyword-intel

# Reset to known good state
sudo systemctl stop keyword-intel
cp /var/data/keyword-intel/backups/latest_good_config.yaml /opt/keyword-intel/config/config.yaml
sudo systemctl start keyword-intel
```

## 📋 Deployment Checklist

### Pre-deployment

- [ ] System requirements verified
- [ ] Dependencies installed
- [ ] Configuration validated
- [ ] Security hardening applied
- [ ] Backup procedures tested
- [ ] Monitoring configured

### Deployment

- [ ] Application deployed
- [ ] Service configured and enabled
- [ ] Health checks passing
- [ ] Logs flowing properly
- [ ] Performance within targets
- [ ] Security scan completed

### Post-deployment

- [ ] End-to-end testing completed
- [ ] Monitoring alerts configured
- [ ] Documentation updated
- [ ] Team trained on operations
- [ ] Runbook validated
- [ ] Rollback plan verified

## 📞 Support & Maintenance

### Regular Maintenance

**Daily:**
- Check service status
- Review error logs
- Verify backup completion

**Weekly:**
- Performance review
- Disk space cleanup
- Security updates

**Monthly:**
- Full system backup
- Performance optimization
- Dependency updates

### Emergency Contacts

- **System Administrator**: admin@company.com
- **Development Team**: dev-team@company.com  
- **Business Owner**: business@company.com

### Documentation

- **API Reference**: `/docs/API.md`
- **Configuration Guide**: `/docs/CONFIGURATION.md`
- **Troubleshooting**: `/docs/TROUBLESHOOTING.md`
- **Runbook**: `/docs/RUNBOOK.md`