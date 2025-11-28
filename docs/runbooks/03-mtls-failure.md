# Service Mesh mTLS Failure

## Trigger
- **Alert**: `sq-uitgohuy-mesh-mtls`
- **Signal**: Linkerd `unauthorized` or `tls handshake error`
- **Severity**: High (service-to-service traffic degraded)

## Immediate Response

### 1. Verify Linkerd Control Plane
```bash
linkerd check
linkerd viz check
kubectl get pods -n linkerd
```

### 2. Inspect Edge Connections
```bash
# Show TLS status between deployments
linkerd edges deploy

# Inspect live traffic for failed TLS handshakes
linkerd tap deploy/<service-name> -o wide | grep -i tls
```

### 3. Confirm Injection
```bash
# Ensure workloads have the proxy sidecar
kubectl get pods -o jsonpath='{.items[*].spec.containers[*].name}' | grep linkerd-proxy

# Check namespace annotation
kubectl get ns default -o jsonpath='{.metadata.annotations}'
```

## Investigation Steps

1. **Certificate Expiry**
   ```bash
   linkerd identity list | grep -E "default\..*expire"
   ```
2. **Clock Skew**
   ```bash
   kubectl exec -it <pod> -- date
   ```
3. **Policy Denies**
   ```bash
   kubectl get serverauthorizations.policy.linkerd.io -A
   ```
4. **Sidecar Version Drift**
   ```bash
   linkerd version
   kubectl get deploy userservice -o jsonpath='{.spec.template.metadata.annotations.linkerd\.io/proxy-version}'
   ```

## Remediation

### 1. Restart Affected Workloads
```bash
kubectl rollout restart deployment/userservice
kubectl rollout restart deployment/tripservice
```

### 2. Rotate Trust Anchors (if expired)
```bash
linkerd upgrade --identity-external-issuer | kubectl apply -f -
```

### 3. Re-enable Injection
```bash
kubectl annotate namespace default linkerd.io/inject=enabled --overwrite
kubectl delete pod <pod-without-proxy>
```

### 4. Clear Policy Conflicts
```bash
kubectl describe serverauthorizations.policy.linkerd.io <name>
kubectl delete serverauthorizations.policy.linkerd.io <conflicting-name>
```

## Resolution Criteria
- `linkerd check` passes without TLS warnings.
- `linkerd edges deploy` shows `True` for `TLS`.
- Application SLOs back to normal (no 5xx / timeout spikes for 30 min).

## Escalation
- Control plane components crash-loop.
- Certificates already rotated but errors persist.
- Impacted services: PaymentService or UserService auth endpoints.

## Prevention
- Schedule monthly `linkerd check --proxy` in CI.
- Monitor certificate expiry with cron/alert.
- Keep control plane and proxies on the same release via GitHub Actions.

## Contacts
- **Platform**: platform@uitgo.example
- **Security**: security@uitgo.example

