# Pod Restart Loop - OOM Investigation

## Trigger
- **Alert**: `sq-uitgohuy-pod-restart`
- **Threshold**: Pod status not "Running" for 10 minutes
- **Severity**: Medium

## Immediate Response

### 1. Identify Affected Pods
```bash
# Check pod restart counts
kubectl get pods --sort-by=.status.restartCount

# Find pods in CrashLoopBackOff
kubectl get pods | grep "CrashLoopBackOff\|Error\|ImagePullBackOff"

# Check recent events
kubectl get events --sort-by=.metadata.creationTimestamp | tail -20
```

### 2. Investigate Pod Status
```bash
# Get detailed pod information
kubectl describe pod <pod-name>

# Check pod logs
kubectl logs <pod-name> --previous
kubectl logs <pod-name> --tail=50
```

### 3. Common Issues to Check

#### Out of Memory (OOM)
```bash
# Look for OOMKilled events
kubectl get events | grep "OOMKilled"

# Check memory usage
kubectl top pods --sort-by=memory

# Review memory limits
kubectl describe pod <pod-name> | grep -A 10 "Limits\|Requests"
```

#### Image Issues
```bash
# Check if image exists in ACR
az acr repository show --name acruithuykhoigo --repository userservice

# Test image pull
kubectl run test-pod --image=acruithuykhoigo.azurecr.io/userservice:latest --dry-run=client -o yaml
```

#### Configuration Issues
```bash
# Check ConfigMaps
kubectl get configmap
kubectl describe configmap <configmap-name>

# Check Secrets
kubectl get secret
kubectl describe secret <secret-name>

# Check environment variables
kubectl get pod <pod-name> -o yaml | grep -A 10 "env:"
```

## Resolution Steps

### 1. Memory Issues
```bash
# Increase memory limits in deployment
kubectl patch deployment <deployment-name> -p '{"spec":{"template":{"spec":{"containers":[{"name":"<container-name>","resources":{"limits":{"memory":"512Mi"}}}]}}}}'

# Or scale down to free resources
kubectl scale deployment <deployment-name> --replicas=0
kubectl scale deployment <deployment-name> --replicas=1
```

### 2. Image Issues
```bash
# Force pull new image
kubectl patch deployment <deployment-name> -p '{"spec":{"template":{"spec":{"containers":[{"name":"<container-name>","imagePullPolicy":"Always"}]}}}}'

# Restart deployment
kubectl rollout restart deployment <deployment-name>
```

### 3. Configuration Issues
```bash
# Update ConfigMaps/Secrets
kubectl apply -f <config-file>

# Restart affected deployments
kubectl rollout restart deployment <deployment-name>
```

## Investigation Commands

### Memory Analysis
```bash
# Check node memory usage
kubectl describe nodes | grep -A 5 "Allocated resources\|Capacity"

# Check all pod memory usage
kubectl top pods --all-namespaces | sort -k3 -nr

# Look for memory leaks
watch "kubectl top pods | grep <pod-name>"
```

### Resource Quotas
```bash
# Check resource quotas
kubectl get resourcequota -o yaml

# Check limit ranges
kubectl get limitrange -o yaml
```

### Persistent Storage Issues
```bash
# Check PVC status
kubectl get pvc

# Check storage class
kubectl get storageclass
```

## Prevention

### 1. Proper Resource Limits
```yaml
resources:
  requests:
    memory: "128Mi"
    cpu: "100m"
  limits:
    memory: "256Mi"
    cpu: "200m"
```

### 2. Health Checks
```yaml
livenessProbe:
  httpGet:
    path: /health
    port: 8000
  initialDelaySeconds: 30
  periodSeconds: 10

readinessProbe:
  httpGet:
    path: /health
    port: 8000
  initialDelaySeconds: 5
  periodSeconds: 5
```

### 3. Resource Monitoring
- Set up memory usage alerts
- Implement HPA (Horizontal Pod Autoscaler)
- Regular resource usage review

## Escalation Criteria

- Multiple pods failing simultaneously
- Critical services (auth, payment) affected
- Database connection issues
- Customer impact reported

## Contacts

- **Infrastructure Team**: [Contact]
- **Development Team**: [Contact]
- **On-call Engineer**: [Contact]