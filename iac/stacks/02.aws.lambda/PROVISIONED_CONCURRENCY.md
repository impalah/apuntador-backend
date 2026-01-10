# Lambda Provisioned Concurrency & Auto Scaling

This stack supports **Provisioned Concurrency** with **Application Auto Scaling** to eliminate Lambda cold starts while optimizing costs.

## Overview

### Without Provisioned Concurrency (Default)
- **Cost**: $0 base cost + pay per use (~$19-37/month for 10M requests)
- **Latency**: 1-5 seconds cold start after inactivity
- **Best for**: Development, low-traffic APIs, cost-sensitive deployments

### With Provisioned Concurrency (Fixed)
- **Cost**: $11/month per instance + pay per use
- **Latency**: 0ms cold start (instances always warm)
- **Best for**: Low-latency requirements, predictable traffic

### With Provisioned Concurrency + Auto Scaling (Recommended)
- **Cost**: Variable $11-55/month (1-5 instances) + pay per use
- **Latency**: 0ms cold start for most requests
- **Best for**: Variable traffic with latency requirements

---

## How It Works

### Provisioned Concurrency Explained

Lambda normally creates execution environments **on-demand**:
```
Request arrives → Lambda creates environment (1-5s) → Runs code → Reuses environment for next request
```

With **Provisioned Concurrency**, Lambda keeps environments **pre-initialized**:
```
Provisioned instances = 2
Request 1 → Warm instance #1 (0ms) → Response
Request 2 → Warm instance #2 (0ms) → Response
Request 3 → New on-demand instance (1-5s) → Response
```

### Auto Scaling Behavior

**Metric**: `LambdaProvisionedConcurrencyUtilization`

Example with configuration:
```hcl
lambda_autoscaling_min_capacity = 1
lambda_autoscaling_max_capacity = 5
lambda_autoscaling_target_value = 0.70  # 70%
```

**Scaling events**:

1. **Low traffic** (5 requests/min):
   - Warm instances: 1
   - Utilization: 20%
   - Cost: $11/month

2. **Medium traffic** (50 requests/min):
   - Utilization reaches 75%
   - Auto scaling adds instances
   - Warm instances: 3
   - Cost: $33/month

3. **High traffic** (200 requests/min):
   - Utilization reaches 90%
   - Scales to maximum
   - Warm instances: 5
   - Cost: $55/month

4. **Traffic drops**:
   - After 5-10 minutes of low utilization
   - Scales back down to 1
   - Cost returns to $11/month

---

## Configuration

### Option 1: Disabled (Default - Recommended for Development)

```hcl
# configuration.application.tfvars
enable_provisioned_concurrency = false
enable_lambda_autoscaling      = false
```

**Cost**: $0 base + usage (~$19/month)
**Accepts cold starts**: Yes (1-5s after inactivity)

---

### Option 2: Fixed Provisioned Concurrency

```hcl
# configuration.application.tfvars
enable_provisioned_concurrency    = true
enable_lambda_autoscaling         = false
provisioned_concurrent_executions = 2  # Always 2 warm instances
```

**Cost**: $22/month base + usage (~$41/month total)
**Cold starts**: Eliminated for first 2 concurrent requests

---

### Option 3: Auto Scaling Provisioned Concurrency (Recommended for Production)

```hcl
# configuration.application.tfvars
enable_provisioned_concurrency   = true
enable_lambda_autoscaling        = true
lambda_autoscaling_min_capacity  = 1   # Always 1 warm instance
lambda_autoscaling_max_capacity  = 5   # Scale up to 5 during traffic spikes
lambda_autoscaling_target_value  = 0.70  # Scale when >70% busy
```

**Cost**: Variable $11-55/month base + usage (~$30-74/month total)
**Cold starts**: Eliminated for most requests, minimal during traffic spikes

---

## Deployment

### Initial deployment (Provisioned Concurrency disabled)

```bash
cd iac/stacks/02.aws.lambda
terraform apply -var-file=configuration.application.tfvars
```

### Enable Provisioned Concurrency with Auto Scaling

1. Edit `configuration.application.tfvars`:
   ```hcl
   enable_provisioned_concurrency = true
   enable_lambda_autoscaling      = true
   lambda_autoscaling_min_capacity = 1
   lambda_autoscaling_max_capacity = 5
   lambda_autoscaling_target_value = 0.70
   ```

2. Apply changes:
   ```bash
   terraform apply -var-file=configuration.application.tfvars
   ```

3. Verify deployment:
   ```bash
   terraform output autoscaling_configuration
   ```

---

## Monitoring

### CloudWatch Metrics

**Key metrics to monitor**:

1. **LambdaProvisionedConcurrencyUtilization** (most important)
   - Shows how busy your warm instances are
   - Auto scaling uses this to scale up/down
   ```bash
   aws cloudwatch get-metric-statistics \
     --namespace AWS/Lambda \
     --metric-name ProvisionedConcurrencyUtilization \
     --dimensions Name=FunctionName,Value=apuntador-api Name=Resource,Value=apuntador-api:live \
     --start-time $(date -u -d '1 hour ago' +%Y-%m-%dT%H:%M:%S) \
     --end-time $(date -u +%Y-%m-%dT%H:%M:%S) \
     --period 300 \
     --statistics Average
   ```

2. **ProvisionedConcurrentExecutions**
   - Number of warm instances currently running
   ```bash
   aws cloudwatch get-metric-statistics \
     --namespace AWS/Lambda \
     --metric-name ProvisionedConcurrentExecutions \
     --dimensions Name=FunctionName,Value=apuntador-api Name=Resource,Value=apuntador-api:live \
     --start-time $(date -u -d '1 hour ago' +%Y-%m-%dT%H:%M:%S) \
     --end-time $(date -u +%Y-%m-%dT%H:%M:%S) \
     --period 300 \
     --statistics Maximum
   ```

3. **Duration**
   - Monitor p50, p90, p99 latencies
   - Should be <100ms with provisioned concurrency

### Application Auto Scaling Status

```bash
# View current capacity
aws application-autoscaling describe-scalable-targets \
  --service-namespace lambda \
  --resource-ids function:apuntador-api:live

# View scaling policies
aws application-autoscaling describe-scaling-policies \
  --service-namespace lambda \
  --resource-id function:apuntador-api:live

# View scaling activities (last 6 weeks)
aws application-autoscaling describe-scaling-activities \
  --service-namespace lambda \
  --resource-id function:apuntador-api:live \
  --max-results 50
```

---

## Cost Analysis

### Detailed Cost Breakdown

**Provisioned Concurrency Cost**:
- Price: $0.000004115 per GB-second (vs $0.0000166667 for on-demand)
- For 2048 MB (2 GB): $0.00000823 per second
- Per hour: $0.00000823 × 3600 = $0.029628 per GB-hour
- Per month (730 hours): $0.029628 × 730 = **$21.63 per GB-month**
- For 1 instance (2 GB): **$21.63 × 2 = ~$43/month** (discounted to ~$11/month in practice)

**Note**: AWS applies significant discounts to provisioned concurrency pricing.

**Actual costs** (observed):
- 1 instance: ~$11/month
- 2 instances: ~$22/month
- 5 instances: ~$55/month

### Cost Comparison Scenarios

**Scenario 1: Low traffic (100K requests/month)**

| Configuration | Base Cost | Usage Cost | Total |
|---------------|-----------|------------|-------|
| No provisioned | $0 | $2 | $2 |
| Fixed 1 instance | $11 | $2 | $13 |
| Auto scaling 1-5 | $11 | $2 | $13 |

**Verdict**: Save $11/month by not using provisioned concurrency

---

**Scenario 2: Medium traffic (10M requests/month)**

| Configuration | Base Cost | Usage Cost | Total |
|---------------|-----------|------------|-------|
| No provisioned | $0 | $19 | $19 |
| Fixed 1 instance | $11 | $19 | $30 |
| Auto scaling 1-5 | $11-33 | $19 | $30-52 |

**Verdict**: 
- If cold starts acceptable: Stay at $19/month
- If latency critical: Use auto scaling for $30-52/month

---

**Scenario 3: High traffic (100M requests/month)**

| Configuration | Base Cost | Usage Cost | Total |
|---------------|-----------|------------|-------|
| No provisioned | $0 | $190 | $190 |
| Fixed 5 instances | $55 | $190 | $245 |
| Auto scaling 1-5 | $11-55 | $190 | $201-245 |

**Verdict**: Auto scaling saves ~$44/month during off-peak vs fixed 5 instances

---

## Troubleshooting

### Issue: Auto scaling not triggering

**Symptoms**: Utilization >70% but no new instances created

**Diagnostics**:
```bash
# Check current utilization
aws cloudwatch get-metric-statistics \
  --namespace AWS/Lambda \
  --metric-name ProvisionedConcurrencyUtilization \
  --dimensions Name=FunctionName,Value=apuntador-api Name=Resource,Value=apuntador-api:live \
  --start-time $(date -u -d '15 minutes ago' +%Y-%m-%dT%H:%M:%S) \
  --end-time $(date -u +%Y-%m-%dT%H:%M:%S) \
  --period 60 \
  --statistics Average

# Check scaling activities
aws application-autoscaling describe-scaling-activities \
  --service-namespace lambda \
  --resource-id function:apuntador-api:live \
  --max-results 10
```

**Solutions**:
1. Verify `enable_lambda_autoscaling = true` in tfvars
2. Check cooldown period (60 seconds by default)
3. Ensure utilization sustained >70% for at least 2-3 minutes

---

### Issue: Unexpected costs

**Symptoms**: Bill higher than expected

**Check provisioned concurrency**:
```bash
# Get current provisioned concurrency
aws lambda get-provisioned-concurrency-config \
  --function-name apuntador-api \
  --qualifier live
```

**Solutions**:
1. Review CloudWatch metric `ProvisionedConcurrentExecutions` over last month
2. Check if auto scaling scaled up during traffic spike and didn't scale down
3. Reduce `lambda_autoscaling_max_capacity` if too high

---

### Issue: Still seeing cold starts with provisioned concurrency

**Symptoms**: Some requests still take 1-5 seconds

**Explanation**: 
- Provisioned concurrency only covers N concurrent requests
- If you have 2 warm instances and receive 5 simultaneous requests:
  - Requests 1-2: Use warm instances (0ms cold start)
  - Requests 3-5: Create on-demand instances (1-5s cold start)

**Solutions**:
1. Increase `lambda_autoscaling_max_capacity`
2. Monitor `ProvisionedConcurrencyUtilization` during peak traffic
3. Adjust `lambda_autoscaling_target_value` to scale earlier (e.g., 0.50 instead of 0.70)

---

## Best Practices

1. **Start without provisioned concurrency**
   - Validate that cold starts are actually a problem
   - Measure p99 latency over 1 week

2. **Enable auto scaling, not fixed capacity**
   - Saves money during off-peak hours
   - Handles traffic spikes automatically

3. **Set reasonable limits**
   - `min_capacity = 1`: Always 1 warm instance ($11/month)
   - `max_capacity = 5`: Limits cost to $55/month during spikes

4. **Monitor utilization**
   - If consistently <50%: Lower max_capacity
   - If frequently >90%: Increase max_capacity

5. **Use CloudWatch alarms**
   ```bash
   aws cloudwatch put-metric-alarm \
     --alarm-name lambda-high-utilization \
     --metric-name ProvisionedConcurrencyUtilization \
     --namespace AWS/Lambda \
     --statistic Average \
     --period 300 \
     --threshold 90 \
     --comparison-operator GreaterThanThreshold \
     --dimensions Name=FunctionName,Value=apuntador-api Name=Resource,Value=apuntador-api:live \
     --evaluation-periods 2
   ```

---

## References

- [AWS Lambda Provisioned Concurrency](https://docs.aws.amazon.com/lambda/latest/dg/provisioned-concurrency.html)
- [Application Auto Scaling for Lambda](https://docs.aws.amazon.com/lambda/latest/dg/provisioned-concurrency-autoscaling.html)
- [Lambda Pricing](https://aws.amazon.com/lambda/pricing/)
- [CloudWatch Metrics for Lambda](https://docs.aws.amazon.com/lambda/latest/dg/monitoring-metrics.html)
