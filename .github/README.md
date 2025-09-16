# GitHub Actions Workflows

This directory contains the CI/CD pipeline configuration for the Keyword Finder project.

## 🚀 Workflows Overview

### 1. CI/CD Pipeline (`ci-cd-production.yml`)

**Triggers**: Push to main/develop, Pull Requests, Daily schedule

**Stages**:
- **Quality Assurance**: Ruff linting, Black formatting, MyPy type checking
- **Security Scanning**: Safety, Bandit, Semgrep vulnerability detection
- **Testing**: Unit tests across Python 3.10-3.12, Integration tests
- **Production Validation**: Configuration validation, performance benchmarks
- **Documentation**: Markdown linting, link checking
- **Deployment**: Staging and production deployment with releases

### 2. Security & Maintenance (`security-maintenance.yml`)

**Triggers**: Push to main, Pull Requests, Daily schedule

**Components**:
- **CodeQL Analysis**: GitHub's semantic code analysis
- **Dependency Review**: Vulnerability scanning for dependencies
- **Supply Chain Security**: SBOM (Software Bill of Materials) generation
- **License Compliance**: Automated license compatibility checking

### 3. Dependabot (`dependabot.yml`)

**Schedule**: Weekly on Mondays

**Updates**:
- Python dependencies with grouped PRs
- GitHub Actions with automated updates
- Docker images (if applicable)

## 🔧 Configuration

### Environment Variables

The workflows use the following environment variables:

```yaml
PYTHON_VERSION: '3.11'  # Primary Python version for production
```

### Secrets

Required GitHub secrets:
- `GITHUB_TOKEN`: Automatically provided by GitHub

### Quality Gates

All workflows enforce quality gates:

| Stage | Requirement | Failure Action |
|-------|-------------|----------------|
| Linting | Zero Ruff violations | Block merge |
| Type Checking | MyPy passes strict mode | Block merge |
| Security | No critical vulnerabilities | Block merge |
| Tests | 100% test pass rate | Block merge |
| Performance | < 5s for 100 keyword scoring | Alert only |

## 📊 Workflow Status

### Production Deployment

Deployments only trigger on:
- ✅ All quality gates passed
- ✅ Security scans completed
- ✅ Documentation validated
- ✅ Performance benchmarks met

### Release Process

Automated releases created with:
- **Tag**: `v2.0.0-{build_number}`
- **Artifacts**: Source code, SBOM, test reports
- **Notes**: Automated changelog with features and metrics

## 🔍 Monitoring

### Key Metrics Tracked

- **Build Success Rate**: Target > 95%
- **Test Coverage**: Target > 80%
- **Security Vulnerabilities**: Target = 0 critical
- **Performance**: < 5s for standard operations
- **Dependency Health**: < 5 outdated major versions

### Alert Conditions

Pipeline failures trigger alerts for:
- Security vulnerabilities (Critical/High)
- Test failures (> 1% failure rate)
- Performance regressions (> 20% slower)
- Build failures (> 2 consecutive failures)

## 🛠️ Local Development

### Running Checks Locally

Before pushing, run the same checks locally:

```bash
# Linting and formatting
ruff check --fix .
black .

# Type checking
mypy src --strict

# Security scanning
bandit -r src/
safety check

# Testing
pytest -v --cov=src

# Performance benchmark
python -c "
from src.core.standardized_scoring import StandardizedScorer
import time
scorer = StandardizedScorer()
start = time.time()
keywords = [{'keyword': f'test_{i}', 'volume': 100, 'competition': 0.5, 'trend_score': 50} for i in range(100)]
scored, _ = scorer.score_batch(keywords, 'PE', 'es')
print(f'Performance: {time.time() - start:.2f}s')
"
```

### Debug Workflow Issues

Common workflow issues:

#### 1. Import Errors
```bash
# Check Python path locally
python -c "import sys; print(sys.path)"
pip list | grep -E "(requests|aiohttp|pandas)"
```

#### 2. Test Failures
```bash
# Run specific test
pytest tests/test_specific.py -v

# Run with detailed output
pytest --tb=long --capture=no
```

#### 3. Security Alerts
```bash
# Check for secrets
git log --all --grep="password\|token\|key" --oneline

# Audit dependencies
pip-audit --requirement requirements.txt
```

## 📋 Workflow Templates

### Adding New Workflow

1. **Create workflow file**: `.github/workflows/new-workflow.yml`
2. **Define triggers**: on push, PR, schedule
3. **Set up steps**: checkout, setup Python, install deps
4. **Add quality gates**: tests, linting, security
5. **Configure artifacts**: logs, reports, metrics

### Workflow Best Practices

- ✅ **Fail Fast**: Run quick checks first
- ✅ **Parallel Execution**: Run independent jobs in parallel
- ✅ **Caching**: Cache dependencies and build artifacts
- ✅ **Artifacts**: Save logs and reports for debugging
- ✅ **Security**: Never commit secrets, use GitHub secrets
- ✅ **Documentation**: Comment complex workflow logic

## 🔄 Maintenance

### Weekly Tasks

- [ ] Review Dependabot PRs
- [ ] Check workflow success rates
- [ ] Update outdated actions
- [ ] Review security alerts

### Monthly Tasks  

- [ ] Performance benchmark review
- [ ] Workflow optimization analysis
- [ ] Security posture assessment
- [ ] Documentation updates

### Quarterly Tasks

- [ ] Complete workflow audit
- [ ] Update to latest GitHub Actions versions
- [ ] Security tool updates
- [ ] Performance threshold review

---

**Maintained by**: DevOps Team  
**Last Updated**: September 2025  
**Next Review**: October 2025