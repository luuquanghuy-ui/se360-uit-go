# High CPU Alert - DoS Response

## Trigger
- **Alert**: `metric-uitgohuy-aks-cpu`
- **Threshold**: CPU > 80% for 5 minutes
- **Severity**: Medium

## Immediate Response

### 1. Assess Situation
```bash
# Check which pods are using high CPU
kubectl top pods --sort-by=cpu

# Check node CPU usage
kubectl top nodes

# Check Linkerd traffic patterns
linkerd top deploy
```

### 2. Identify Source
```bash
# Check for unusual traffic patterns
linkerd tap deploy/nginx-ingress-controller

# Check request rates per service
kubectl logs -f deployment/nginx-ingress-controller | grep "GET\|POST"

# Look for suspicious IP addresses
kubectl get ingress -o wide
```

### 3. Implement Mitigation

#### Rate Limiting (if available)
```bash
# Check if rate limiting annotations exist
kubectl get ingress -o yaml | grep "ratelimit"
```

#### Scale Resources
```bash
# Temporarily scale affected services
kubectl scale deployment userservice --replicas=3
kubectl scale deployment tripservice --replicas=3
```

#### Block Suspicious IPs
```bash
# Get client IPs from logs
kubectl logs deployment/nginx-ingress-controller | grep "client_ip" | sort | uniq -c | sort -nr

# Add IP blocking using NetworkPolicy if needed
```

## Investigation Steps

### 1. Check Application Logs
```bash
kubectl logs -f deployment/userservice
kubectl logs -f deployment/tripservice
kubectl logs -f deployment/driverservice
kubectl logs -f deployment/locationservice
kubectl logs -f deployment/paymentservice
```

### 2. Monitor Resource Usage
```bash
# Real-time monitoring
watch kubectl top pods

# Check for resource limits
kubectl describe pods | grep "Limits\|Requests"
```

### 3. Database Load
```bash
# Check CosmosDB metrics
az cosmosdb show --name cosmos-uitgohuy-prod --resource-group rg-uitgohuy-prod --query "throughput"

# Check Redis usage
az redis show --name redis-uitgohuy-prod --resource-group rg-uitgohuy-prod --query "usedMemory"
```

## Resolution Steps

### 1. Normal CPU Usage
- Monitor for 15 minutes after mitigation
- Scale back to original replicas if stable
- Document the incident

### 2. Continued High CPU
- Investigate application code for performance issues
- Consider resource optimization
- Review monitoring thresholds

## Escalation Criteria

- CPU remains > 90% for more than 15 minutes
- Multiple services affected simultaneously
- Database performance degradation detected
- Customer impact reported

## Prevention

1. **Implement Rate Limiting**
   ```yaml
   # Add to ingress annotations
   nginx.ingress.kubernetes.io/rate-limit: "100"
   ```

2. **Auto-scaling**
   ```yaml
   # Add HPA configuration
   apiVersion: autoscaling/v2
   kind: HorizontalPodAutoscaler
   ```

3. **Monitoring Enhancement**
   - Set up additional alerts for request rate
   - Implement custom metrics tracking

