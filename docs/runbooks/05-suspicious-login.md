# Suspicious Login Activity

## Trigger
- **Alert**: `sq-uitgohuy-auth-bruteforce`
- **Signal**: Elevated 401/429 responses, anomalous IPs, Azure AD risky sign-ins
- **Severity**: High when affecting production auth endpoints

## Immediate Response

### 1. Snapshot Metrics
```bash
# HTTP status distribution
kubectl logs deployment/userservice | grep -E "401|429" | tail -100

# Ingress rate
linkerd top deploy/userservice
```

### 2. Pull Auth Logs
```bash
az monitor log-analytics query -w <workspace-id> \
  --analytics-query "AppRequests | where ResultCode == '401' | summarize count() by ClientIP_s"
```

## Investigation Steps

1. **Identify offending IPs / ASNs**
   ```bash
   kubectl logs deployment/nginx-ingress-controller | awk '{print $1}' | sort | uniq -c | sort -nr | head
   ```
2. **Check account impact**
   ```bash
   kubectl logs deployment/userservice | grep "username=" | tail -50
   ```
3. **Verify MFA / lock status**
   - Review user records in PostgreSQL.
4. **Look for leaked tokens**
   - Search TruffleHog / Git history in CI artifacts.

## Containment

### 1. Rate Limiting / WAF
```yaml
nginx.ingress.kubernetes.io/limit-rpm: "60"
```
Apply via `kubectl annotate ingress api-gateway ...`.

### 2. Temporary Blocklist
```bash
kubectl apply -f k8s/network-policies.yaml  # includes deny lists
```

### 3. Force Logout / Token Revoke
```bash
# Invalidate Redis session if used
redis-cli KEYS "session:*" | xargs redis-cli DEL
```

### 4. Disable Self-Service Login (if needed)
```bash
kubectl scale deployment/userservice --replicas=0
```

## Resolution Criteria
- 401/429 rate back to baseline for 1 hour.
- No new suspicious IPs detected.
- Impacted accounts have password reset and MFA enabled.

## Post-Incident Actions
- Notify affected users.
- Rotate JWT secret (`JWT_SECRET_KEY`) and restart services.
- Add IP reputation checks to ingress.

## Escalation
- Credential stuffing confirmed with successful login events.
- PaymentService tokens potentially abused.
- Regulatory notification required.

## Prevention
- Implement CAPTCHA on login.
- Add anomaly detection to CI pipeline.
- Enforce MFA for admin/driver accounts.

## Contacts
- **Security**: soc@uitgo.example
- **Support**: support@uitgo.example

