# ECS Auto Scaling Configuration Guide

## Overview

El autoscaling de ECS permite que tu aplicación escale automáticamente el número de tareas (contenedores) en función de métricas como CPU, memoria y número de peticiones. Esto optimiza costes (escala hacia abajo cuando hay poca carga) y garantiza rendimiento (escala hacia arriba cuando hay alta demanda).

## Arquitectura

```
┌─────────────────────────────────────────────────────────────┐
│                   Application Load Balancer                │
│                     (api.apuntador.io)                      │
└───────────────────┬─────────────────────────────────────────┘
                    │
                    ├─── ECS Task 1 (mínimo: 2)
                    ├─── ECS Task 2 
                    ├─── ECS Task 3 (escala según demanda)
                    ├─── ...
                    └─── ECS Task N (máximo: 10)
                           │
                           ↓
                    ┌──────────────────┐
                    │  Auto Scaling    │
                    │    Políticas:    │
                    │  - CPU > 70%     │
                    │  - Memory > 80%  │
                    │  - Requests/task │
                    └──────────────────┘
```

## Variables de Configuración

### `enable_autoscaling`
- **Tipo**: `bool`
- **Default**: `false`
- **Descripción**: Activa o desactiva completamente el autoscaling
- **Ejemplo**:
  ```hcl
  enable_autoscaling = true   # Activa autoscaling
  enable_autoscaling = false  # Desactiva autoscaling (solo usa desired_count)
  ```

### `autoscaling_min_capacity`
- **Tipo**: `number`
- **Default**: `2`
- **Descripción**: Número mínimo de tareas que deben estar ejecutándose
- **Recomendación**: Mínimo 2 para alta disponibilidad
- **Ejemplo**:
  ```hcl
  autoscaling_min_capacity = 2  # Siempre al menos 2 tareas corriendo
  ```

### `autoscaling_max_capacity`
- **Tipo**: `number`
- **Default**: `10`
- **Descripción**: Número máximo de tareas permitidas
- **Recomendación**: Basado en tu presupuesto y carga esperada
- **Coste**: Cada tarea 256 CPU/512 MB = ~$5.30/mes (running 24/7)
- **Ejemplo**:
  ```hcl
  autoscaling_max_capacity = 10  # Permite hasta 10 tareas en picos
  ```

### `autoscaling_cpu_target`
- **Tipo**: `number`
- **Default**: `70`
- **Descripción**: Porcentaje objetivo de uso de CPU
- **Funcionamiento**:
  - Si CPU > 70%: Escala **hacia arriba** (añade tareas)
  - Si CPU < 70%: Escala **hacia abajo** (elimina tareas)
- **Recomendación**: 60-80% para balance entre rendimiento y costes
- **Ejemplo**:
  ```hcl
  autoscaling_cpu_target = 70  # Mantén CPU alrededor del 70%
  ```

### `autoscaling_memory_target`
- **Tipo**: `number`
- **Default**: `80`
- **Descripción**: Porcentaje objetivo de uso de memoria
- **Funcionamiento**:
  - Si Memory > 80%: Escala **hacia arriba**
  - Si Memory < 80%: Escala **hacia abajo**
- **Recomendación**: 75-85% para evitar OOM kills
- **Ejemplo**:
  ```hcl
  autoscaling_memory_target = 80  # Mantén memoria alrededor del 80%
  ```

### `autoscaling_request_count_target`
- **Tipo**: `number`
- **Default**: `1000`
- **Descripción**: Número objetivo de peticiones por tarea
- **Funcionamiento**:
  - Si requests/task > 1000: Escala **hacia arriba**
  - Si requests/task < 1000: Escala **hacia abajo**
- **Recomendación**: Basado en benchmarks de tu aplicación
- **Cálculo**: Si tienes 5000 req/min y target=1000, escalará a 5 tareas
- **Ejemplo**:
  ```hcl
  autoscaling_request_count_target = 1000  # 1000 requests por tarea
  ```

### `autoscaling_scale_in_cooldown`
- **Tipo**: `number`
- **Default**: `300` (5 minutos)
- **Descripción**: Tiempo de espera (segundos) antes de permitir otra reducción de tareas
- **Propósito**: Evitar "flapping" (escalar arriba/abajo rápidamente)
- **Recomendación**: 300-600 segundos para reducir costes de transición
- **Ejemplo**:
  ```hcl
  autoscaling_scale_in_cooldown = 300  # Espera 5 min antes de reducir otra tarea
  ```

### `autoscaling_scale_out_cooldown`
- **Tipo**: `number`
- **Default**: `60` (1 minuto)
- **Descripción**: Tiempo de espera (segundos) antes de permitir otro aumento de tareas
- **Propósito**: Dar tiempo a que las nuevas tareas comiencen a procesar carga
- **Recomendación**: 60-120 segundos (más corto que scale-in para responder rápido)
- **Ejemplo**:
  ```hcl
  autoscaling_scale_out_cooldown = 60  # Espera 1 min antes de añadir otra tarea
  ```

## Políticas de Escalado Implementadas

El módulo crea **3 políticas de auto scaling** que trabajan en paralelo:

### 1. **CPU-based Scaling**
```hcl
Target: 70% CPU utilization
Type: TargetTrackingScaling
```
- Escala cuando el promedio de CPU de todas las tareas excede el 70%
- Útil para aplicaciones CPU-intensive (procesamiento, compresión, etc.)

### 2. **Memory-based Scaling**
```hcl
Target: 80% Memory utilization
Type: TargetTrackingScaling
```
- Escala cuando el promedio de memoria de todas las tareas excede el 80%
- Útil para aplicaciones memory-intensive (cache, grandes payloads, etc.)

### 3. **Request Count Scaling**
```hcl
Target: 1000 requests per task
Type: TargetTrackingScaling
Metric: ALBRequestCountPerTarget
```
- Escala basado en el número de peticiones HTTP que recibe cada tarea
- Útil para aplicaciones web con tráfico variable
- **Métrica más precisa** para aplicaciones API REST

## Ejemplo de Configuración por Entorno

### Desarrollo (Dev)
```hcl
enable_autoscaling = false  # No necesario en dev
desired_count      = 1      # 1 tarea fija
```

### Staging
```hcl
enable_autoscaling               = true
autoscaling_min_capacity         = 1
autoscaling_max_capacity         = 3
autoscaling_cpu_target           = 75
autoscaling_memory_target        = 85
autoscaling_request_count_target = 500
```

### Producción (Alta Disponibilidad)
```hcl
enable_autoscaling               = true
autoscaling_min_capacity         = 2   # Mínimo 2 para HA
autoscaling_max_capacity         = 10
autoscaling_cpu_target           = 70
autoscaling_memory_target        = 80
autoscaling_request_count_target = 1000
autoscaling_scale_in_cooldown    = 300
autoscaling_scale_out_cooldown   = 60
```

### Producción (Alta Carga)
```hcl
enable_autoscaling               = true
autoscaling_min_capacity         = 5   # Base más alta
autoscaling_max_capacity         = 50  # Escala masiva
autoscaling_cpu_target           = 60  # Escala antes
autoscaling_memory_target        = 75
autoscaling_request_count_target = 2000  # Más requests/task
autoscaling_scale_in_cooldown    = 600   # 10 min para reducir
autoscaling_scale_out_cooldown   = 30    # 30 seg para aumentar
```

## Cómo Funciona el Auto Scaling

### Ciclo de Evaluación

1. **CloudWatch Metrics**: AWS recoge métricas cada 1 minuto
   - ECSServiceAverageCPUUtilization
   - ECSServiceAverageMemoryUtilization
   - ALBRequestCountPerTarget

2. **Comparación con Target**: Auto Scaling compara valores actuales vs targets
   ```
   Actual CPU: 85% > Target: 70% → SCALE OUT ⬆️
   Actual CPU: 45% < Target: 70% → SCALE IN  ⬇️
   ```

3. **Cooldown Period**: Espera el tiempo configurado antes de siguiente acción
   ```
   Scale Out → Wait 60s → Can scale out again
   Scale In  → Wait 300s → Can scale in again
   ```

4. **Capacity Limits**: Respeta siempre min/max capacity
   ```
   Current: 8 tasks
   Scale Out: 8 + 2 = 10 (max) ✅
   Scale Out: 10 + 2 = 12 ❌ (blocked by max_capacity=10)
   ```

### Ejemplo de Escalado en Tiempo Real

```
Time    | CPU  | Memory | Requests/task | Tasks | Action
--------|------|--------|---------------|-------|------------------
09:00   | 45%  | 60%    | 400          | 2     | (stable)
09:15   | 75%  | 72%    | 1200         | 2     | Scale OUT → 3 tasks
09:20   | 68%  | 65%    | 950          | 3     | (stable, within cooldown)
09:30   | 82%  | 88%    | 1500         | 3     | Scale OUT → 5 tasks
10:00   | 55%  | 60%    | 600          | 5     | (stable, within cooldown)
10:30   | 40%  | 50%    | 400          | 5     | Scale IN → 3 tasks
11:00   | 35%  | 45%    | 300          | 3     | Scale IN → 2 tasks
```

## Monitoreo del Auto Scaling

### CloudWatch Alarms

El auto scaling crea alarmas automáticamente:

```bash
# Ver alarmas de auto scaling
aws cloudwatch describe-alarms \
  --alarm-name-prefix "TargetTracking-service/prod-apuntador-cluster/prod-apuntador-service"
```

### Métricas Clave

```bash
# Ver actividad de scaling
aws application-autoscaling describe-scaling-activities \
  --service-namespace ecs \
  --resource-id "service/prod-apuntador-cluster/prod-apuntador-service"

# Ver capacidad actual
aws application-autoscaling describe-scalable-targets \
  --service-namespace ecs \
  --resource-ids "service/prod-apuntador-cluster/prod-apuntador-service"
```

### Dashboard en CloudWatch

Crea un dashboard con estas métricas:
- `ECS > ClusterName > ServiceName > CPUUtilization`
- `ECS > ClusterName > ServiceName > MemoryUtilization`
- `ApplicationELB > TargetGroup > RequestCountPerTarget`
- `ECS > ClusterName > ServiceName > DesiredTaskCount`
- `ECS > ClusterName > ServiceName > RunningTaskCount`

## Troubleshooting

### Problema: No escala hacia arriba

**Verificaciones**:
1. ¿`enable_autoscaling = true`?
2. ¿Has alcanzado `max_capacity`?
3. ¿Estás dentro del período de cooldown?
4. ¿Las métricas realmente exceden los targets?

```bash
# Ver estado actual
aws ecs describe-services \
  --cluster prod-apuntador-cluster \
  --services prod-apuntador-service \
  --query 'services[0].{desired:desiredCount,running:runningCount}'
```

### Problema: No escala hacia abajo

**Causas comunes**:
1. Dentro del `scale_in_cooldown` (300s default)
2. Ya estás en `min_capacity`
3. Alguna política de protección activa

```bash
# Ver actividad reciente
aws application-autoscaling describe-scaling-activities \
  --service-namespace ecs \
  --resource-id "service/prod-apuntador-cluster/prod-apuntador-service" \
  --max-results 10
```

### Problema: "Flapping" (escala arriba/abajo constantemente)

**Soluciones**:
- Aumenta `scale_in_cooldown` a 600s
- Ajusta targets (ej: CPU target de 70% → 65%)
- Revisa si hay tareas fallando (health checks)

## Costes de Auto Scaling

### Coste Base (min_capacity = 2)
```
2 tasks × 256 CPU/512 MB × $5.30/mes = $10.60/mes
```

### Coste Promedio (escala 2-5 tasks)
```
Promedio 3.5 tasks × $5.30/mes = $18.55/mes
```

### Coste Máximo (max_capacity = 10)
```
10 tasks × 256 CPU/512 MB × $5.30/mes = $53.00/mes
```

### Coste Real (variable según tráfico)
```
Hora Pico (10:00-18:00):    8 tasks  → $2.83/día
Hora Normal (18:00-22:00):  3 tasks  → $0.66/día
Hora Valle (22:00-10:00):   2 tasks  → $0.35/día
                                      ────────────
                           TOTAL:     $3.84/día ≈ $115/mes
```

**Ahorro con Auto Scaling**:
- Sin auto scaling (8 tasks fijas): $42.40/mes
- Con auto scaling (promedio 3 tasks): $15.90/mes
- **Ahorro: $26.50/mes (62%)**

## Mejores Prácticas

1. **Empieza conservador**: Targets altos (CPU 80%, Memory 85%)
2. **Monitorea durante 1 semana**: Ajusta basado en patrones reales
3. **Cooldown generoso**: `scale_in_cooldown` > `scale_out_cooldown`
4. **Mínimo 2 tasks**: Para alta disponibilidad en producción
5. **Alarmas de límites**: Notifica cuando llegas a max_capacity
6. **Testing de carga**: Simula tráfico alto para validar escalado

## Referencias

- [AWS ECS Auto Scaling](https://docs.aws.amazon.com/AmazonECS/latest/developerguide/service-auto-scaling.html)
- [Target Tracking Scaling](https://docs.aws.amazon.com/autoscaling/application/userguide/application-auto-scaling-target-tracking.html)
- [CloudWatch Metrics for ECS](https://docs.aws.amazon.com/AmazonECS/latest/developerguide/cloudwatch-metrics.html)
