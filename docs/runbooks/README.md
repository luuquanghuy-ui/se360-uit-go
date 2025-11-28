# Security Runbooks

Collection of incident response procedures for UIT-Go security monitoring.

## Available Runbooks

1. **[High CPU Alert](01-high-cpu-alert.md)** - DoS attack detection and response
2. **[Pod Restart Loop](02-pod-restart-loop.md)** - OOM investigation and troubleshooting
3. **[Service Mesh mTLS Failure](03-mtls-failure.md)** - Certificate troubleshooting
4. **[Database Connection Failures](04-database-connection.md)** - Network diagnostics
5. **[Suspicious Login Activity](05-suspicious-login.md)** - Brute force response
6. **[Container Image Vulnerability](06-container-vulnerability.md)** - CVE remediation

## Quick Reference

### Common Commands

```bash
# Check cluster resources
kubectl top nodes
kubectl top pods

# Check Linkerd status
linkerd check
linkerd viz check

# View logs
kubectl logs -f <pod-name>

# Network debugging
linkerd tap deploy/<service-name>

# Monitor alerts
az monitor metrics alert list --resource-group rg-uitgohuy-prod

# Restart services
kubectl rollout restart deployment/<service-name>
```