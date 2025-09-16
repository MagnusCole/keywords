# Runbook - Keyword Finder Production Operations

**Version**: 2.0.0  
**Environment**: Production  
**Updated**: September 2025  
**Maintainer**: DevOps Team

## 🚨 Emergency Contacts

- **Primary**: Production Team (on-call)
- **Secondary**: Platform Engineering
- **Escalation**: Engineering Lead

## 📋 Service Overview

### System Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Web Interface │    │  Keyword Finder │    │    Database     │
│   (Dashboard)   │────│     Service     │────│   (SQLite)      │
└─────────────────┘    └─────────────────┘    └─────────────────┘
                                │
                                ▼
                        ┌─────────────────┐
                        │  Export System  │
                        │ (CSV/Standards) │
                        └─────────────────┘
```

### Critical Components

- **Keyword Finder Service**: Core intelligence engine
- **Google Scraper**: Data collection component
- **ML Pipeline**: Clustering and scoring
- **Export System**: Standardized output
- **Database**: SQLite with enterprise schema
- **Logging System**: Enhanced enterprise logging

## 🏥 Health Monitoring

### System Health Checks

```bash
# Service status
sudo systemctl status keyword-finder

# Resource usage
df -h /opt/keyword-finder
free -h
top -u keyword-finder

# Log health
tail -f /opt/keyword-finder/logs/production.jsonl | jq .

# Database health
sqlite3 /opt/keyword-finder/keywords.db "SELECT COUNT(*) FROM runs WHERE DATE(created_at) = DATE('now');"
```

### Key Metrics to Monitor

| Metric | Normal Range | Alert Threshold | Critical Threshold |
|--------|--------------|-----------------|-------------------|
| CPU Usage | < 30% | > 70% | > 90% |
| Memory Usage | < 1GB | > 2GB | > 4GB |
| Disk Usage | < 70% | > 85% | > 95% |
| Response Time | < 30s | > 120s | > 300s |
| Error Rate | < 1% | > 5% | > 10% |
| Log Volume | < 100MB/day | > 500MB/day | > 1GB/day |

### Automated Health Check Script

```bash
#!/bin/bash
# /opt/keyword-finder/scripts/health_check.sh

LOGFILE="/var/log/keyword-finder-health.log"
SERVICE_NAME="keyword-finder"

log() {
    echo "$(date '+%Y-%m-%d %H:%M:%S') $1" | tee -a $LOGFILE
}

# Check service status
if ! systemctl is-active --quiet $SERVICE_NAME; then
    log "CRITICAL: Service $SERVICE_NAME is not running"
    exit 2
fi

# Check disk space
DISK_USAGE=$(df /opt/keyword-finder | tail -1 | awk '{print $5}' | sed 's/%//')
if [ $DISK_USAGE -gt 90 ]; then
    log "CRITICAL: Disk usage at ${DISK_USAGE}%"
    exit 2
elif [ $DISK_USAGE -gt 80 ]; then
    log "WARNING: Disk usage at ${DISK_USAGE}%"
fi

# Check memory usage
MEM_USAGE=$(free | grep Mem | awk '{printf "%.0f", $3/$2 * 100.0}')
if [ $MEM_USAGE -gt 90 ]; then
    log "CRITICAL: Memory usage at ${MEM_USAGE}%"
    exit 2
fi

# Check recent errors in logs
ERROR_COUNT=$(tail -100 /opt/keyword-finder/logs/production.jsonl | grep '"level":"ERROR"' | wc -l)
if [ $ERROR_COUNT -gt 5 ]; then
    log "WARNING: ${ERROR_COUNT} errors in recent logs"
fi

log "OK: All health checks passed"
exit 0
```

## 🚀 Operational Procedures

### Starting the Service

```bash
# Start service
sudo systemctl start keyword-finder

# Verify startup
sudo systemctl status keyword-finder
sudo journalctl -u keyword-finder -f

# Check logs for successful startup
tail -f /opt/keyword-finder/logs/production.jsonl | grep "service_started"
```

### Stopping the Service

```bash
# Graceful shutdown
sudo systemctl stop keyword-finder

# Force stop if needed
sudo systemctl kill keyword-finder

# Verify shutdown
sudo systemctl status keyword-finder
```

### Restarting the Service

```bash
# Standard restart
sudo systemctl restart keyword-finder

# Reload configuration only
sudo systemctl reload keyword-finder

# Monitor restart
sudo journalctl -u keyword-finder -f
```

### Configuration Updates

```bash
# 1. Backup current configuration
sudo cp /opt/keyword-finder/config/config.yaml /opt/keyword-finder/config/config.yaml.backup

# 2. Update configuration
sudo nano /opt/keyword-finder/config/config.yaml

# 3. Validate configuration
cd /opt/keyword-finder
sudo -u keyword-finder python -m src.platform.settings --validate config/config.yaml

# 4. Reload service
sudo systemctl reload keyword-finder

# 5. Verify changes
tail -f /opt/keyword-finder/logs/production.jsonl | grep "config_reloaded"
```

## 📊 Performance Optimization

### Database Maintenance

```bash
#!/bin/bash
# Daily database maintenance

DB_PATH="/opt/keyword-finder/keywords.db"
BACKUP_PATH="/opt/keyword-finder/backups/db_$(date +%Y%m%d_%H%M%S).db"

# Backup database
sudo -u keyword-finder cp $DB_PATH $BACKUP_PATH

# Optimize database
sudo -u keyword-finder sqlite3 $DB_PATH "VACUUM;"
sudo -u keyword-finder sqlite3 $DB_PATH "ANALYZE;"

# Check database integrity
INTEGRITY=$(sudo -u keyword-finder sqlite3 $DB_PATH "PRAGMA integrity_check;")
if [ "$INTEGRITY" != "ok" ]; then
    echo "ERROR: Database integrity check failed: $INTEGRITY"
    exit 1
fi

echo "Database maintenance completed successfully"
```

### Cache Management

```bash
# Clear embedding cache
sudo rm -rf /opt/keyword-finder/cache/emb_*

# Clear old exports (keep last 30 days)
find /opt/keyword-finder/exports -name "*.csv" -mtime +30 -delete

# Clear old logs (keep last 90 days)
find /opt/keyword-finder/logs -name "*.jsonl" -mtime +90 -delete
```

### Resource Optimization

```bash
# Monitor top processes
top -u keyword-finder

# Check file descriptors
sudo lsof -u keyword-finder | wc -l

# Monitor network connections
sudo netstat -tulpn | grep python

# Check system limits
sudo -u keyword-finder ulimit -a
```

## 🔧 Troubleshooting Guide

### Common Issues

#### 1. Service Won't Start

**Symptoms**: `systemctl start keyword-finder` fails

**Diagnosis**:
```bash
# Check service logs
sudo journalctl -u keyword-finder --no-pager

# Check configuration
sudo -u keyword-finder python -m src.platform.settings --validate config/config.yaml

# Check permissions
sudo ls -la /opt/keyword-finder/
```

**Solutions**:
- Fix configuration syntax errors
- Restore from backup configuration
- Check file permissions: `sudo chown -R keyword-finder:keyword-finder /opt/keyword-finder`

#### 2. High Memory Usage

**Symptoms**: Memory usage > 2GB

**Diagnosis**:
```bash
# Check memory usage by process
sudo ps aux --sort=-rss | head

# Check for memory leaks
sudo -u keyword-finder python -m tracemalloc /opt/keyword-finder/main.py
```

**Solutions**:
- Restart service: `sudo systemctl restart keyword-finder`
- Reduce batch sizes in configuration
- Clear caches: `rm -rf /opt/keyword-finder/cache/*`

#### 3. Slow Performance

**Symptoms**: Response time > 120 seconds

**Diagnosis**:
```bash
# Check system load
uptime

# Check I/O wait
iostat -x 1 5

# Check database locks
sudo -u keyword-finder sqlite3 /opt/keyword-finder/keywords.db ".timeout 1000" "PRAGMA busy_timeout;"
```

**Solutions**:
- Optimize database: Run VACUUM and ANALYZE
- Increase system resources
- Enable caching in configuration

#### 4. Export Failures

**Symptoms**: Exports not generating or corrupted

**Diagnosis**:
```bash
# Check export directory permissions
ls -la /opt/keyword-finder/exports/

# Check recent logs
grep "export" /opt/keyword-finder/logs/production.jsonl | tail -10

# Test export manually
sudo -u keyword-finder python -c "from src.io.export_standards import StandardizedExporter; print('Export system OK')"
```

**Solutions**:
- Fix directory permissions: `sudo chmod 755 /opt/keyword-finder/exports`
- Clear failed exports: `rm /opt/keyword-finder/exports/*.tmp`
- Restart export service component

#### 5. Database Connection Issues

**Symptoms**: SQLite connection errors

**Diagnosis**:
```bash
# Check database file
sudo -u keyword-finder sqlite3 /opt/keyword-finder/keywords.db "SELECT 1;"

# Check file locks
sudo lsof /opt/keyword-finder/keywords.db

# Check disk space
df -h /opt/keyword-finder/
```

**Solutions**:
- Restart service to clear locks
- Free disk space if needed
- Restore from backup if corrupted

### Emergency Procedures

#### Service Recovery

```bash
#!/bin/bash
# Emergency service recovery script

SERVICE="keyword-finder"
CONFIG_PATH="/opt/keyword-finder/config/config.yaml"
BACKUP_CONFIG="/opt/keyword-finder/config/config.yaml.backup"

echo "Starting emergency recovery for $SERVICE..."

# 1. Stop service
sudo systemctl stop $SERVICE

# 2. Restore configuration from backup
if [ -f "$BACKUP_CONFIG" ]; then
    sudo cp $BACKUP_CONFIG $CONFIG_PATH
    echo "Configuration restored from backup"
fi

# 3. Clear temporary files
sudo rm -f /opt/keyword-finder/exports/*.tmp
sudo rm -f /opt/keyword-finder/cache/*.tmp

# 4. Reset permissions
sudo chown -R keyword-finder:keyword-finder /opt/keyword-finder

# 5. Start service
sudo systemctl start $SERVICE

# 6. Verify recovery
sleep 10
if systemctl is-active --quiet $SERVICE; then
    echo "Recovery successful - service is running"
else
    echo "Recovery failed - check logs"
    sudo journalctl -u $SERVICE --no-pager -n 50
fi
```

#### Data Recovery

```bash
#!/bin/bash
# Emergency data recovery

BACKUP_DIR="/opt/keyword-finder/backups"
DB_PATH="/opt/keyword-finder/keywords.db"

# Find latest backup
LATEST_BACKUP=$(ls -t $BACKUP_DIR/db_*.db | head -1)

if [ -z "$LATEST_BACKUP" ]; then
    echo "ERROR: No database backups found"
    exit 1
fi

echo "Restoring database from: $LATEST_BACKUP"

# Stop service
sudo systemctl stop keyword-finder

# Backup current (potentially corrupted) database
sudo mv $DB_PATH ${DB_PATH}.corrupted.$(date +%s)

# Restore from backup
sudo cp $LATEST_BACKUP $DB_PATH
sudo chown keyword-finder:keyword-finder $DB_PATH

# Start service
sudo systemctl start keyword-finder

echo "Database recovery completed"
```

## 🔐 Security Procedures

### Security Monitoring

```bash
# Check failed login attempts
sudo grep "Failed" /var/log/auth.log | tail -10

# Check unusual file access
sudo find /opt/keyword-finder -name "*.py" -newer /opt/keyword-finder/logs/security.log

# Monitor process execution
sudo ps aux | grep keyword-finder
```

### Security Hardening

```bash
# Update file permissions
sudo chmod 600 /opt/keyword-finder/config/config.yaml
sudo chmod 700 /opt/keyword-finder/logs/
sudo chmod 755 /opt/keyword-finder/exports/

# Check for unauthorized changes
sudo aide --check

# Update security patches
sudo apt update && sudo apt upgrade -y
```

## 📈 Capacity Planning

### Storage Requirements

| Component | Current Usage | Growth Rate | Retention |
|-----------|---------------|-------------|-----------|
| Database | 50MB | 5MB/month | 2 years |
| Logs | 100MB | 50MB/month | 90 days |
| Exports | 200MB | 100MB/month | 30 days |
| Cache | 500MB | Stable | 7 days |

### Scaling Thresholds

- **CPU**: Scale when consistently > 70%
- **Memory**: Scale when consistently > 1.5GB
- **Storage**: Scale when > 80% full
- **Response Time**: Scale when > 60s average

## 🚨 Alerting Rules

### Critical Alerts (Immediate Response)

- Service down > 5 minutes
- Error rate > 10%
- Disk usage > 95%
- Memory usage > 95%
- Database corruption detected

### Warning Alerts (24h Response)

- CPU usage > 70% for 30 minutes
- Error rate > 5%
- Disk usage > 85%
- Response time > 120 seconds
- High log volume

### Alert Configuration

```yaml
# alertmanager.yml
groups:
- name: keyword-finder
  rules:
  - alert: ServiceDown
    expr: up{job="keyword-finder"} == 0
    for: 5m
    labels:
      severity: critical
    annotations:
      summary: "Keyword Finder service is down"
      
  - alert: HighErrorRate
    expr: rate(errors_total[5m]) > 0.1
    for: 10m
    labels:
      severity: warning
    annotations:
      summary: "High error rate detected"
```

## 📚 Documentation References

- **Configuration Guide**: [CONFIGURATION.md](CONFIGURATION.md)
- **Deployment Guide**: [DEPLOYMENT.md](DEPLOYMENT.md)
- **API Reference**: [API.md](API.md)
- **Security Guide**: [SECURITY.md](SECURITY.md)

## 📞 Escalation Matrix

| Issue Severity | Response Time | Escalation Path |
|----------------|---------------|-----------------|
| Critical | 15 minutes | On-call → Team Lead → Engineering Manager |
| High | 2 hours | Team Member → Team Lead |
| Medium | 24 hours | Team Member → Backlog |
| Low | 1 week | Documentation Update |

## 🔄 Change Management

### Configuration Changes

1. **Test in staging environment**
2. **Create configuration backup**
3. **Apply changes during maintenance window**
4. **Validate functionality**
5. **Document changes**

### Service Updates

1. **Schedule maintenance window**
2. **Notify stakeholders**
3. **Create full system backup**
4. **Deploy changes**
5. **Verify deployment**
6. **Update documentation**

## 📋 Maintenance Schedule

### Daily

- Health check execution
- Log rotation
- Cache cleanup

### Weekly

- Database optimization
- Performance review
- Security scan

### Monthly

- Full backup verification
- Capacity planning review
- Documentation update

### Quarterly

- Disaster recovery test
- Security audit
- Performance optimization

---

**Document Owner**: Production Team  
**Review Cycle**: Monthly  
**Last Updated**: September 2025