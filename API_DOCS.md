# 🏢 Enterprise API Documentation

## 🌐 REST API Endpoints

### 🔍 Keyword Generation

**POST /api/v1/keywords/generate**

Generate keywords with advanced scoring and geo-targeting.

```json
{
  "seeds": ["seo tools", "marketing software"],
  "country": "PE",
  "intent": "transactional",
  "limit": 50,
  "min_score": 0.6,
  "advanced_scoring": true
}
```

**Response:**
```json
{
  "status": "success",
  "data": {
    "keywords": [
      {
        "keyword": "herramientas seo peru",
        "score": 0.87,
        "intent": "transactional",
        "search_volume": "medium",
        "competition": "low",
        "geo_relevance": 0.92,
        "serp_difficulty": 0.34
      }
    ],
    "metadata": {
      "total_generated": 50,
      "processing_time_ms": 2340,
      "country": "PE",
      "http2_used": true
    }
  }
}
```

### 📊 Scoring Analysis

**POST /api/v1/keywords/score**

Analyze existing keywords with advanced scoring.

```json
{
  "keywords": ["seo tools", "herramientas seo"],
  "country": "PE",
  "intent": "transactional"
}
```

### 🌍 Geo-Targeting

**GET /api/v1/countries**

Get supported countries and their configurations.

```json
{
  "countries": {
    "PE": {"name": "Peru", "hl": "es", "gl": "PE", "lr": "lang_es"},
    "ES": {"name": "Spain", "hl": "es", "gl": "ES", "lr": "lang_es"},
    "MX": {"name": "Mexico", "hl": "es", "gl": "MX", "lr": "lang_es"}
  }
}
```

### 📈 Analytics & Reports

**GET /api/v1/analytics/reliability**

Get system reliability metrics.

```json
{
  "reliability_score": 0.87,
  "confidence_level": "high",
  "metrics": {
    "data_source_quality": 0.92,
    "scoring_consistency": 0.85,
    "geo_accuracy": 0.89,
    "intent_accuracy": 0.84
  },
  "recommendations": [
    "System ready for production use",
    "Monitor scoring consistency weekly"
  ]
}
```

## 🔧 Client Libraries

### Python Client

```python
import requests

class KeywordFinderClient:
    def __init__(self, base_url="http://localhost:8000"):
        self.base_url = base_url
    
    def generate_keywords(self, seeds, country="PE", intent="transactional", limit=50):
        response = requests.post(f"{self.base_url}/api/v1/keywords/generate", json={
            "seeds": seeds,
            "country": country,
            "intent": intent,
            "limit": limit,
            "advanced_scoring": True
        })
        return response.json()
    
    def get_reliability_metrics(self):
        response = requests.get(f"{self.base_url}/api/v1/analytics/reliability")
        return response.json()

# Usage
client = KeywordFinderClient()
result = client.generate_keywords(["seo tools"], country="PE")
print(f"Generated {len(result['data']['keywords'])} keywords")
```

### JavaScript Client

```javascript
class KeywordFinderAPI {
    constructor(baseUrl = 'http://localhost:8000') {
        this.baseUrl = baseUrl;
    }
    
    async generateKeywords(seeds, options = {}) {
        const response = await fetch(`${this.baseUrl}/api/v1/keywords/generate`, {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({
                seeds,
                country: options.country || 'PE',
                intent: options.intent || 'transactional',
                limit: options.limit || 50,
                advanced_scoring: true
            })
        });
        return response.json();
    }
    
    async getReliabilityMetrics() {
        const response = await fetch(`${this.baseUrl}/api/v1/analytics/reliability`);
        return response.json();
    }
}

// Usage
const api = new KeywordFinderAPI();
const result = await api.generateKeywords(['seo tools'], {country: 'PE'});
console.log(`Generated ${result.data.keywords.length} keywords`);
```

### cURL Examples

```bash
# Generate keywords
curl -X POST http://localhost:8000/api/v1/keywords/generate \
  -H "Content-Type: application/json" \
  -d '{
    "seeds": ["seo tools"],
    "country": "PE",
    "intent": "transactional",
    "limit": 20
  }'

# Get reliability metrics
curl http://localhost:8000/api/v1/analytics/reliability

# Get supported countries
curl http://localhost:8000/api/v1/countries
```

## 🔐 Authentication & Security

### API Key Authentication

```bash
# Set API key in header
curl -H "X-API-Key: your-api-key-here" \
     -X POST http://localhost:8000/api/v1/keywords/generate
```

### Rate Limiting

```json
{
  "rate_limit": {
    "requests_per_minute": 60,
    "burst_limit": 10,
    "current_usage": 15,
    "reset_time": "2024-01-15T10:30:00Z"
  }
}
```

## 📊 Response Formats

### Success Response

```json
{
  "status": "success",
  "data": { /* response data */ },
  "metadata": {
    "timestamp": "2024-01-15T10:15:30Z",
    "version": "1.0.0",
    "processing_time_ms": 1250
  }
}
```

### Error Response

```json
{
  "status": "error",
  "error": {
    "code": "INVALID_COUNTRY",
    "message": "Country 'XX' is not supported",
    "details": {
      "supported_countries": ["PE", "ES", "MX", "AR", "CO", "CL", "US"]
    }
  },
  "metadata": {
    "timestamp": "2024-01-15T10:15:30Z",
    "request_id": "req_123456789"
  }
}
```

## 🎯 Use Cases & Examples

### E-commerce Keyword Research

```python
# Generate transactional keywords for Peru market
keywords = client.generate_keywords(
    seeds=["zapatos deportivos", "ropa fitness"],
    country="PE",
    intent="transactional",
    limit=100
)

# Filter high-value keywords
high_value = [k for k in keywords['data']['keywords'] if k['score'] > 0.8]
```

### Content Marketing

```python
# Generate informational keywords for blog content
keywords = client.generate_keywords(
    seeds=["marketing digital", "seo tips"],
    country="ES",
    intent="informational",
    limit=50
)
```

### Multi-Country Analysis

```python
# Compare keyword opportunities across countries
countries = ["PE", "MX", "AR", "CO"]
results = {}

for country in countries:
    results[country] = client.generate_keywords(
        seeds=["software empresarial"],
        country=country,
        intent="commercial"
    )
```

## 📈 Performance Metrics

### Benchmarks

```json
{
  "performance": {
    "avg_response_time_ms": 1850,
    "keywords_per_second": 7.2,
    "success_rate": 89.4,
    "http2_adoption": 100,
    "memory_usage_mb": 45,
    "concurrent_requests": 5
  }
}
```

### SLA Targets

- **Availability**: 99.5%
- **Response Time**: < 3 seconds (95th percentile)
- **Success Rate**: > 85%
- **Throughput**: > 5 keywords/second

## 🔄 Webhooks & Integrations

### Webhook Configuration

```json
{
  "webhook_url": "https://your-app.com/webhook",
  "events": ["keyword_batch_complete", "system_alert"],
  "secret": "webhook_secret_key"
}
```

### Slack Integration

```python
# Send results to Slack
import requests

def send_to_slack(keywords, webhook_url):
    message = {
        "text": f"🎯 Generated {len(keywords)} new keywords",
        "attachments": [{
            "color": "good",
            "fields": [
                {"title": "Top Keyword", "value": keywords[0]['keyword'], "short": True},
                {"title": "Score", "value": f"{keywords[0]['score']:.2f}", "short": True}
            ]
        }]
    }
    requests.post(webhook_url, json=message)
```

---

**Enterprise API Documentation v1.0** | **Production Ready**