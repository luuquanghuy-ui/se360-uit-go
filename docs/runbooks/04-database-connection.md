# Database Connection Failures

## Trigger
- **Alert**: `sq-uitgohuy-db-connection`
- **Signal**: Spike in 5xx from services or health checks failing
- **Severity**: High for UserService/PaymentService, Medium for others

## Immediate Response

### 1. Confirm Scope
```bash
kubectl logs deployment/userservice | grep -i "connection"
kubectl logs deployment/paymentservice | grep -i "timeout"
```

### 2. Check Azure Resource Health
```bash
az postgres flexible-server show -n <server> -g <rg> --query "state"
az cosmosdb show -n <cosmos-account> -g <rg> --query "status"
az redis show -n <redis-name> -g <rg> --query "provisioningState"
```

## Investigation Steps

### 1. Network / NSG
```bash
az network vnet subnet show -g <rg> -n snet-postgres-prod --vnet-name vnet-<prefix>-prod --query "networkSecurityGroup"
kubectl exec -it debug -- nc -vz postgres.internal 5432
```

### 2. Secrets & Config
```bash
kubectl get secret uitgo-secrets -o yaml | grep -E "POSTGRES|COSMOS|REDIS"
kubectl describe deployment userservice | grep -A5 "env:"
```

### 3. Connection Saturation
```bash
az postgres flexible-server parameter show -n <server> -g <rg> --parameter-name max_connections
az cosmosdb restorable-database-account list -g <rg> | jq '.[] | {name,status}'
```

### 4. Service Metrics
```bash
linkerd top deploy/userservice
kubectl top pod userservice-xxxx
```

## Remediation

### 1. Reset Secret / Connection String
```bash
kubectl create secret generic uitgo-secrets \
  --from-literal=POSTGRES_HOST="postgres.internal" \
  --from-literal=POSTGRES_USER="uitgo_app" \
  --from-literal=POSTGRES_PASSWORD="<new-password>" \
  --from-literal=COSMOS_CONNECTION_STRING="<conn>" \
  --dry-run=client -o yaml | kubectl apply -f -
kubectl rollout restart deployment/userservice
```

### 2. Failover / Scale
```bash
az cosmosdb failover-priority-change -g <rg> -n <account> --failover-policies region2=0 region1=1
az postgres flexible-server restart -n <server> -g <rg>
```

### 3. Temporary Bypass
- Switch TripService read-model to cached data for 10 minutes.
- Use `kubectl scale deployment/tripservice --replicas=0` if cascading failures.

## Resolution Criteria
- Health endpoints return 200 for 15 minutes.
- Application logs show successful DB connections.
- Azure metrics: connection success rate > 99%.

## Escalation
- Database service outage > 30 minutes.
- Data corruption suspicion (failed migrations, inconsistent reads).
- Multiple services across databases failing simultaneously.

## Prevention
- Enable connection pooling (pgbouncer) for Postgres.
- Configure retry policies in Motor/SQLAlchemy.
- Monitor connection counts via Azure Monitor metric alert.

## Contacts
- **DBA**: dba@uitgo.example
- **Platform**: platform@uitgo.example

