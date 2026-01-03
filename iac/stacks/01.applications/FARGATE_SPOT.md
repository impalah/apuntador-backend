# Fargate Spot - Guía Completa

## ¿Qué es Fargate Spot?

Fargate Spot es una opción de precio para AWS Fargate que ofrece **hasta 70% de descuento** sobre el precio normal de Fargate. A cambio, AWS puede **interrumpir** tus tareas con un aviso de 2 minutos cuando necesite recuperar la capacidad.

## Ahorro de Costes

### Comparación de Precios (256 CPU / 512 MB)

| Tipo | Precio/hora | Precio/mes (24/7) | Ahorro |
|------|-------------|-------------------|---------|
| **Fargate Normal** | $0.00737 | $5.30 | - |
| **Fargate Spot** | $0.00295 | $2.12 | **60%** |

### Escenarios Reales

#### Escenario 1: Solo Fargate Spot (máximo ahorro, máximo riesgo)
```
10 tareas × $2.12/mes = $21.20/mes
Ahorro vs Fargate normal: $31.80/mes (60%)

⚠️ PROBLEMA: Si AWS interrumpe todas las tareas → DOWNTIME TOTAL
```

#### Escenario 2: Mix 50/50 (balance)
```
5 tareas Fargate normal: 5 × $5.30 = $26.50/mes
5 tareas Fargate Spot:   5 × $2.12 = $10.60/mes
                         TOTAL:      $37.10/mes
Ahorro vs todo Fargate normal: $15.90/mes (30%)

✅ MEJOR: Siempre tienes 50% de capacidad garantizada
```

#### Escenario 3: Base + Burst con Auto Scaling (configuración recomendada)
```
Configuración:
- Base: 2 tareas Fargate normal (SIEMPRE)
- Burst: Escala hasta 10 tareas (mix 1:3 → 75% Spot)

Tráfico bajo (2 tareas):
  2 × $5.30 = $10.60/mes

Tráfico medio (5 tareas):
  2 Fargate + 3 Spot = (2 × $5.30) + (3 × $2.12) = $16.96/mes

Tráfico alto (10 tareas):
  4 Fargate + 6 Spot = (4 × $5.30) + (6 × $2.12) = $33.92/mes

Promedio mensual (asumiendo 40% del tiempo en tráfico alto):
  ($10.60 × 0.4) + ($16.96 × 0.3) + ($33.92 × 0.3) = $19.50/mes

Ahorro vs todo Fargate normal: $33.50/mes (63% de ahorro)
✅✅ RECOMENDADO: Máximo ahorro con garantía de disponibilidad
```

## Cómo Funciona

### Capacity Provider Strategy

AWS ECS distribuye tareas entre FARGATE y FARGATE_SPOT usando:

1. **Base**: Número mínimo de tareas en Fargate normal
2. **Weight**: Proporción de distribución entre proveedores

```hcl
# Configuración actual (configuration.application.tfvars)
enable_fargate_spot = true
fargate_spot_min_fargate_tasks = 2  # Base: 2 tareas SIEMPRE en Fargate normal
fargate_spot_base_capacity = 1      # Weight Fargate normal: 1
fargate_spot_weight = 3             # Weight Fargate Spot: 3
```

### Ejemplo con 10 Tareas

```
Total desired: 10 tareas
Base Fargate:  2 tareas (garantizadas)
Remaining:     8 tareas

Distribución por weight (1:3):
  Fargate:      8 × (1/4) = 2 tareas
  Fargate Spot: 8 × (3/4) = 6 tareas

RESULTADO FINAL:
  Fargate normal: 2 (base) + 2 (weight) = 4 tareas
  Fargate Spot:   0 (base) + 6 (weight) = 6 tareas
```

## Interrupciones: Cómo se Manejan

### Proceso de Interrupción

1. **AWS decide interrumpir**: Cuando necesita la capacidad
2. **Señal SIGTERM**: Tu contenedor recibe SIGTERM (no SIGKILL inmediato)
3. **2 minutos de gracia**: Tienes 120 segundos para:
   - Terminar requests en curso
   - Guardar estado si es necesario
   - Shutdown graceful
4. **Nueva tarea**: ECS automáticamente lanza nueva tarea (puede ser Fargate normal o Spot)

### Implementación de Graceful Shutdown

```python
# src/apuntador/main.py
import signal
import sys
from loguru import logger

def sigterm_handler(signum, frame):
    """Handle SIGTERM from Fargate Spot interruption."""
    logger.warning("Received SIGTERM - Fargate Spot interruption detected")
    logger.info("Starting graceful shutdown (120 seconds max)...")
    
    # 1. Stop accepting new connections
    # 2. Wait for current requests to finish (with timeout)
    # 3. Close database connections
    # 4. Exit cleanly
    
    sys.exit(0)

# Register SIGTERM handler
signal.signal(signal.SIGTERM, sigterm_handler)
```

### Health Checks y Reemplazo Automático

```hcl
# 01.api.tf - Ya configurado
load_balancer {
  target_group_arn = aws_lb_target_group.apuntador.arn
  container_name   = "apuntador-backend"
  container_port   = 8000
}

health_check_grace_period_seconds = 60
```

**Flujo de reemplazo**:
1. Tarea Spot es interrumpida → Estado `STOPPED`
2. ECS detecta: `runningCount < desiredCount`
3. ECS lanza nueva tarea inmediatamente
4. Health check valida nueva tarea (60s grace period)
5. ALB comienza a enviar tráfico a nueva tarea
6. **Downtime**: Solo durante el tiempo de arranque (~30-60 segundos)

## Problemas Potenciales

### 1. Interrupción de Todas las Tareas Spot Simultáneamente

**Escenario**: AWS interrumpe 6 tareas Spot al mismo tiempo

**Impacto**:
- De 10 tareas → 4 tareas Fargate normal
- Capacidad se reduce al 40%
- CPU/memoria en tareas restantes sube significativamente
- Puede causar latencia alta o errores 5xx

**Mitigación**:
- Auto Scaling detecta alta CPU → Escala hacia arriba
- Nuevas tareas se lanzan en ~60 segundos
- `fargate_spot_min_fargate_tasks = 2` garantiza mínimo de servicio

### 2. No hay Capacidad Spot Disponible

**Escenario**: Picos de demanda AWS, no hay Spot disponible

**Síntoma**:
```
ECS Service Event: (service prod-apuntador-service) was unable to place a task 
because no container instance met all of its requirements. 
Reason: No capacity available for FARGATE_SPOT.
```

**Impacto**:
- Nuevas tareas quedan en `PENDING`
- Auto Scaling no puede escalar
- Servicio funciona con capacidad reducida

**Mitigación**:
- ECS automáticamente retrocede a FARGATE normal después de varios intentos
- Configurar alarm para capacidad insuficiente
- Aumentar `fargate_spot_base_capacity` (más peso a Fargate normal)

### 3. Cascading Failures

**Escenario**:
1. Interrupciones Spot durante pico de tráfico
2. Tareas restantes sobrecargadas
3. Health checks fallan → ALB las marca unhealthy
4. Aún menos tareas disponibles → más carga → más fallos

**Mitigación**:
```hcl
# configuration.application.tfvars
autoscaling_scale_out_cooldown = 30  # Escala rápido (30s en vez de 60s)
autoscaling_cpu_target = 60          # Escala antes (60% en vez de 70%)
fargate_spot_min_fargate_tasks = 4   # Más base capacity (4 en vez de 2)
```

### 4. Costes Inesperados por Fallback

**Escenario**:
- Configuras todo para Spot
- No hay capacidad Spot disponible durante 1 semana
- Todas las tareas corren en Fargate normal

**Impacto**:
```
Esperado: 10 tareas Spot = $21.20/mes
Real:     10 tareas Fargate = $53/mes
Diferencia: +$31.80/mes (150% más)
```

**Mitigación**:
- CloudWatch Alarm cuando >50% de tareas en Fargate normal
- Budget alerts en AWS Budgets

## Cuándo Usar Fargate Spot

### ✅ Casos de Uso Ideales

1. **Desarrollo y Staging**
   ```hcl
   enable_fargate_spot = true
   fargate_spot_min_fargate_tasks = 0  # Todo puede ser Spot
   fargate_spot_weight = 1             # 100% Spot
   ```

2. **Producción con Auto Scaling y Alta Redundancia**
   ```hcl
   enable_fargate_spot = true
   fargate_spot_min_fargate_tasks = 2  # Mínimo 2 tareas garantizadas
   fargate_spot_weight = 3             # 75% de burst capacity en Spot
   autoscaling_min_capacity = 2
   autoscaling_max_capacity = 20       # Puede escalar mucho
   ```

3. **Batch Jobs y Workers Asíncronos**
   - Procesamiento de imágenes
   - ETL jobs
   - Envío de emails
   - Todo lo que puede reintentar sin afectar usuarios

### ❌ Casos Donde NO Usar Fargate Spot

1. **Aplicaciones Críticas sin Redundancia**
   - Si solo tienes 2 tareas y ambas en Spot → riesgo alto

2. **Workloads Stateful sin Persistencia**
   - Si mantienes estado en memoria y no lo guardas
   - WebSockets de larga duración sin reconexión automática

3. **SLA Estrictos (<99.9%)**
   - Si tu SLA no tolera interrupciones ocasionales

4. **Aplicaciones sin Health Checks Robustos**
   - Si no puedes detectar y reemplazar tareas fallidas rápidamente

## Configuraciones Recomendadas por Entorno

### Desarrollo
```hcl
enable_fargate_spot = true
desired_count = 1
fargate_spot_min_fargate_tasks = 0
fargate_spot_weight = 1  # 100% Spot

# No autoscaling en dev
enable_autoscaling = false
```
**Coste**: ~$2.12/mes (1 tarea Spot)  
**Ahorro vs Fargate**: $3.18/mes (60%)

### Staging
```hcl
enable_fargate_spot = true
desired_count = 2
fargate_spot_min_fargate_tasks = 1   # 1 tarea garantizada
fargate_spot_weight = 1              # 50% Spot

enable_autoscaling = true
autoscaling_min_capacity = 1
autoscaling_max_capacity = 5
```
**Coste promedio**: ~$13/mes (mix 1.5 Fargate + 0.5 Spot)  
**Ahorro vs Fargate**: ~$3/mes (23%)

### Producción (Configuración Actual)
```hcl
enable_fargate_spot = true
desired_count = 2
fargate_spot_min_fargate_tasks = 2   # 2 tareas SIEMPRE en Fargate
fargate_spot_base_capacity = 1
fargate_spot_weight = 3              # 75% de burst en Spot

enable_autoscaling = true
autoscaling_min_capacity = 2
autoscaling_max_capacity = 10
```
**Coste promedio**: ~$25/mes (asumiendo 5 tareas promedio: 3 Fargate + 2 Spot)  
**Ahorro vs Fargate**: ~$11.50/mes (31%)

### Producción (Alta Disponibilidad)
```hcl
enable_fargate_spot = true
desired_count = 4
fargate_spot_min_fargate_tasks = 4   # 4 tareas base Fargate
fargate_spot_base_capacity = 2       # Más peso a Fargate
fargate_spot_weight = 3              # Spot solo para burst

enable_autoscaling = true
autoscaling_min_capacity = 4
autoscaling_max_capacity = 20
```
**Coste promedio**: ~$48/mes (asumiendo 10 tareas promedio: 6 Fargate + 4 Spot)  
**Ahorro vs Fargate**: ~$17/mes (26%)

## Monitoreo y Alertas

### CloudWatch Metrics

```bash
# Ver distribución de tareas (Fargate vs Spot)
aws ecs describe-services \
  --cluster prod-apuntador-cluster \
  --services prod-apuntador-service \
  --query 'services[0].capacityProviderStrategy'

# Ver tareas en ejecución
aws ecs list-tasks \
  --cluster prod-apuntador-cluster \
  --service-name prod-apuntador-service

# Describir tareas para ver capacity provider
aws ecs describe-tasks \
  --cluster prod-apuntador-cluster \
  --tasks <task-arn> \
  --query 'tasks[*].capacityProviderName'
```

### Alarmas Recomendadas

```hcl
# Alarma: Demasiadas tareas en Fargate normal (posible falta de Spot)
resource "aws_cloudwatch_metric_alarm" "too_many_fargate_tasks" {
  alarm_name          = "prod-apuntador-too-many-fargate-tasks"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = "2"
  metric_name         = "RunningTaskCount"
  namespace           = "AWS/ECS"
  period              = "300"
  statistic           = "Average"
  threshold           = "6"  # Alerta si >6 tareas en Fargate normal
  alarm_description   = "Too many tasks on FARGATE (expected mostly FARGATE_SPOT)"
  
  dimensions = {
    ClusterName = "prod-apuntador-cluster"
    ServiceName = "prod-apuntador-service"
  }
}

# Alarma: Tareas pending (no se pueden lanzar)
resource "aws_cloudwatch_metric_alarm" "tasks_pending" {
  alarm_name          = "prod-apuntador-tasks-pending"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = "2"
  metric_name         = "PendingTaskCount"
  namespace           = "AWS/ECS"
  period              = "60"
  statistic           = "Average"
  threshold           = "0"
  alarm_description   = "Tasks stuck in pending state (capacity issue?)"
  
  dimensions = {
    ClusterName = "prod-apuntador-cluster"
    ServiceName = "prod-apuntador-service"
  }
}
```

## Mejores Prácticas

1. **Siempre configura `fargate_spot_min_fargate_tasks ≥ 2`**
   - Garantiza alta disponibilidad mínima
   - Evita downtime total si Spot no está disponible

2. **Weight ratio 1:3 (Fargate:Spot) es óptimo**
   - Balance entre ahorro (75% Spot) y disponibilidad (25% Fargate)

3. **Combina con Auto Scaling**
   - Base capacity en Fargate normal
   - Burst capacity principalmente en Spot

4. **Implementa graceful shutdown**
   - Maneja SIGTERM correctamente
   - Cierra conexiones limpias en 120 segundos

5. **Monitorea capacidad**
   - Alarmas cuando >50% tareas en Fargate normal
   - Dashboard con distribución Fargate vs Spot

6. **Testing**
   - Prueba interrupciones en staging
   - Simula falta de capacidad Spot

7. **SLA Considerations**
   - Documenta SLA esperado (ej: 99.5% con Spot vs 99.9% sin Spot)
   - Comunica a stakeholders el trade-off coste/disponibilidad

## Migración desde Fargate Normal

### Paso 1: Activar en Staging
```bash
# Editar configuration.application.tfvars
enable_fargate_spot = true
fargate_spot_min_fargate_tasks = 1
fargate_spot_weight = 1

# Aplicar
terraform apply -var-file=configuration.application.tfvars
```

### Paso 2: Monitorear 1 Semana
- Verificar logs de interrupciones
- Medir tiempo de reemplazo de tareas
- Validar que health checks funcionan correctamente

### Paso 3: Activar en Producción Gradualmente
```hcl
# Semana 1: Conservador (solo 25% Spot)
fargate_spot_min_fargate_tasks = 3
fargate_spot_weight = 1

# Semana 2: Balance (50% Spot)
fargate_spot_min_fargate_tasks = 2
fargate_spot_weight = 2

# Semana 3+: Óptimo (75% Spot)
fargate_spot_min_fargate_tasks = 2
fargate_spot_weight = 3
```

### Paso 4: Optimizar
- Ajustar weights basado en interrupciones reales
- Tunear auto scaling cooldowns
- Revisar costes reales vs esperados

## Resumen Ejecutivo

| Aspecto | Fargate Normal | Fargate Spot (Configuración Actual) |
|---------|----------------|-------------------------------------|
| **Coste** | $53/mes (10 tareas) | ~$34/mes (4 Fargate + 6 Spot) |
| **Ahorro** | - | **36% ($19/mes)** |
| **Disponibilidad** | 99.99% | 99.5-99.9% (depende de interrupciones) |
| **Interrupciones** | Ninguna | Ocasionales (2 min aviso) |
| **Complejidad** | Baja | Media (requiere graceful shutdown) |
| **Recomendado para** | Aplicaciones críticas | Producción con redundancia + Dev/Staging |

**Veredicto**: ✅ **ÚSALO en producción con configuración mixta (base Fargate + burst Spot)**
- Ahorro significativo sin sacrificar disponibilidad
- Configuración actual (2 base Fargate + 75% Spot burst) es óptima
- Riesgo controlado con auto scaling y health checks
