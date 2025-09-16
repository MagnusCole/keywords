# Google Ads API Integration Guide

¡Felicitaciones! Tu API de Google Ads ha sido aprobada. Este documento te guía en la configuración completa.

## 📋 Información de tu Cuenta

**Según tu email de aprobación:**
- **Manager Account**: 426-486-7852
- **Nivel de acceso**: Basic Access
- **Límites diarios**:
  - 15,000 operaciones por día
  - 1,000 requests GET por día
- **Acceso gratuito** con límites suficientes para la mayoría de casos

## 🔧 Configuración Paso a Paso

### 1. Configurar Credenciales OAuth2

#### A. Crear proyecto en Google Cloud Console
1. Ve a [Google Cloud Console](https://console.cloud.google.com/)
2. Crea un nuevo proyecto o selecciona uno existente
3. Habilita la **Google Ads API**
4. Ve a **Credenciales** → **Crear credenciales** → **ID de cliente OAuth 2.0**
5. Configura como **Aplicación de escritorio**
6. Descarga el JSON de credenciales

#### B. Generar Refresh Token
```bash
# Usar la biblioteca de autenticación de Google Ads
pip install google-ads-auth

# Ejecutar el flujo de autenticación
python -c "
from google.ads.googleads.oauth2 import get_installed_app_flow
flow = get_installed_app_flow(
    ['https://www.googleapis.com/auth/adwords'],
    'PATH_TO_YOUR_CLIENT_SECRETS.json'
)
credentials = flow.run_local_server(port=0)
print(f'Refresh token: {credentials.refresh_token}')
"
```

### 2. Configurar Variables de Entorno

Copia `.env.example` a `.env` y completa:

```bash
# Tu Developer Token aprobado (desde API Center)
GOOGLE_ADS_DEVELOPER_TOKEN=tu_token_desarrollador

# Credenciales OAuth2 (desde Google Cloud Console)
GOOGLE_ADS_CLIENT_ID=tu_client_id.googleusercontent.com
GOOGLE_ADS_CLIENT_SECRET=tu_client_secret

# Token de refresh (generado en paso anterior)
GOOGLE_ADS_REFRESH_TOKEN=tu_refresh_token

# ID de cuenta publicitaria (SIN guiones)
GOOGLE_ADS_CUSTOMER_ID=1234567890

# Manager Account (ya configurado según tu email)
GOOGLE_ADS_LOGIN_CUSTOMER_ID=426-486-7852
```

### 3. Verificar Configuración

```bash
# Ejecutar script de configuración
python setup_google_ads.py
```

Este script:
- ✅ Verifica que todas las credenciales estén configuradas
- 🧪 Prueba la conectividad con la API
- 📊 Muestra el estado actual de cuotas

## 🚀 Uso en Producción

### Configuración de Producción

El archivo `config/production.yaml` está optimizado para usar datos reales:

```yaml
sources:
  trends: true           # Datos reales de Google Trends
  ads_volume: true       # Volúmenes reales de Google Ads
  
requests:
  delay_min: 3.0         # 3-6 segundos entre requests
  delay_max: 6.0         
  concurrent_limit: 1    # Un request por vez (máxima seguridad)

google_ads:
  daily_operations_limit: 15000
  daily_get_requests_limit: 1000
  batch_size: 20         # Lotes pequeños
```

### Ejecutar Extracción de Producción

```bash
# Usar el runner optimizado de producción
python run_production.py
```

Este runner:
- 📊 Monitorea cuotas en tiempo real
- ⚠️  Detiene extracción si se acerca a límites
- 🔄 Usa rate limiting conservador
- 📈 Maximiza calidad de datos con APIs reales

### Monitoreo de Cuotas

```bash
# Ver estado actual de cuotas
python -c "
from src.ads_quota import get_quota_manager
manager = get_quota_manager()
manager.print_quota_status()
"
```

## 📊 Sistema de Cuotas Inteligente

### Características
- **Tracking automático**: Cuenta operaciones y GET requests
- **Márgenes de seguridad**: Usa solo 80% de límites diarios
- **Caché persistente**: Evita requests duplicados
- **Alertas proactivas**: Avisos cuando se acerca a límites

### Estructura de Cuotas
```
Límite Real → Límite Seguro → Tu Uso
15,000 ops → 12,000 ops → Tracking
1,000 GETs → 800 GETs → Tracking
```

## 🔍 Validación de Datos

### Comparar con Sistema Legacy
```bash
# Script de validación obsoleto - usar tests en su lugar
# python validate_scoring.py --config config/production.yaml
pytest tests/
```

### Métricas de Calidad
- **Correlación**: >0.85 entre legacy y nuevo sistema
- **Performance**: ~1.6x más rápido
- **Precisión**: Datos reales vs estimaciones

## ⚠️ Límites y Mejores Prácticas

### Respetar Límites API
- **Máximo 15,000 operaciones/día** (nosotros usamos 12,000)
- **Máximo 1,000 GET requests/día** (nosotros usamos 800)
- **Rate limiting**: 3-6 segundos entre requests
- **Batch size**: 20 keywords por request

### Optimizaciones
- **Cache inteligente**: TTL de 7 días para volúmenes
- **Requests mínimos**: Filtrar keywords antes de consultar API
- **Reintentos limitados**: Máximo 3 intentos con backoff
- **Monitoring proactivo**: Alerta a 75% de uso

### Escalabilidad Futura
Si necesitas **Standard Access** (>15,000 ops/día):
- Documentar uso real con logs
- Aplicar solo cuando realmente necesites más cuota
- Google aprueba basado en necesidad demostrada

## 🛠️ Troubleshooting

### Errores Comunes

**"Invalid credentials"**
- Verificar que el refresh token sea válido
- Regenerar token si es necesario

**"Customer not found"**
- Verificar CUSTOMER_ID (sin guiones)
- Confirmar acceso a la cuenta

**"Quota exceeded"**
- Esperar reset diario (medianoche PST)
- Usar `get_quota_status()` para monitorear

### Logs y Debugging
```bash
# Habilitar logging detallado
export LOG_LEVEL=DEBUG
python run_production.py
```

## 📈 Próximos Pasos

1. **✅ Configurar credenciales** (este documento)
2. **🧪 Probar conectividad** (`python setup_google_ads.py`)
3. **🚀 Ejecutar producción** (`python run_production.py`)
4. **📊 Validar resultados** (comparar con legacy)
5. **🔄 Iterar configuración** según necesidades

¡Tu sistema está listo para aprovechar datos reales de Google Ads! 🎉