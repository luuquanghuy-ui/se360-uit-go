# UIT-Go Security Implementation Guide

Complete step-by-step implementation guide for securing UIT-Go microservices architecture with Zero Trust principles.

## Prerequisites

- Azure CLI installed and configured
- Terraform installed
- kubectl installed
- Access to Azure subscription (Owner role recommended)
- Git repository with UIT-Go microservices

## Phase 1: Foundation - Network & Secrets

### 1.1 Terraform Infrastructure Setup

```bash
# Clone repository
git clone <repository-url>
cd se360-uit-go

# Initialize Terraform
cd terraform
terraform init

# Create variables file (DO NOT commit secrets)
cat > terraform.tfvars << EOF
database_password = "YourSecurePassword123!"
EOF

# Add to gitignore
echo "terraform.tfvars" >> .gitignore
```

### 1.2 Network & Security Infrastructure

```bash
# Apply network configuration
terraform apply -target=azurerm_resource_group.rg
terraform apply -target=azurerm_virtual_network.vnet
terraform apply -target=azurerm_subnet.aks_subnet
terraform apply -target=azurerm_network_security_group.aks_nsg

# Apply database configurations
terraform apply -target=azurerm_postgresql_server.postgres
terraform apply -target=azurerm_cosmosdb_account.cosmos
terraform apply -target=azurerm_redis_cache.redis
```

### 1.3 AKS Cluster Setup

```bash
# Apply AKS configuration
terraform apply -target=azurerm_kubernetes_cluster.aks

# Get cluster credentials
az aks get-credentials --resource-group rg-uitgohuy-prod --name aks-uitgohuy-prod

# Verify cluster access
kubectl get nodes
```

## Phase 2: Service Mesh & Zero Trust

### 2.1 Linkerd Service Mesh Installation

```bash
# Install Linkerd CLI
curl --proto '=https' --tlsv1.2 -sSfL https://run.linkerd.io/install | sh
export PATH=$PATH:$HOME/.linkerd2/bin

# Verify cluster requirements
linkerd check --pre

# Install Linkerd control plane
linkerd install | kubectl apply -f -

# Install Linkerd Viz for monitoring
linkerd viz install | kubectl apply -f -

# Verify installation
linkerd check
linkerd viz check

# Enable automatic injection for default namespace
kubectl annotate namespace default linkerd.io/inject=enabled
```

### 2.2 Network Policies Implementation

```bash
# Apply network policies (Zero Trust)
kubectl apply -f k8s/network-policies.yaml

# Verify network policies
kubectl get networkpolicies
```

### 2.3 Pod Security Standards

```bash
# Apply restricted Pod Security Standards
kubectl label namespace default pod-security.kubernetes.io/enforce=restricted \
  pod-security.kubernetes.io/audit=restricted \
  pod-security.kubernetes.io/warn=restricted

# Verify PSP status
kubectl describe namespace default
```

## Phase 3: CI/CD Security Integration

### 3.1 GitHub Actions Setup

The CI/CD pipeline is already configured in `.github/workflows/deploy.yml` with 6 security tools:

- **Bandit**: SAST for Python code
- **Safety**: SCA for Python dependencies
- **TruffleHog**: Secrets scanning
- **Checkov**: IaC security scanning
- **Trivy**: Container vulnerability scanning
- **OWASP ZAP**: DAST for running applications

### 3.2 Azure Container Registry Integration

```bash
# Build and push images (handled by CI/CD)
# Manual build for testing:
az acr build --registry acruithuykhoigo --image userservice:v1.0 ./userservice
az acr build --registry acruithuykhoigo --image tripservice:v1.0 ./tripservice
az acr build --registry acruithuykhoigo --image driverservice:v1.0 ./driverservice
az acr build --registry acruithuykhoigo --image locationservice:v1.0 ./locationservice
az acr build --registry acruithuykhoigo --image paymentservice:v1.0 ./paymentservice
```

## Phase 4: Application Hardening

### 4.1 Secrets Management

```bash
# Create Kubernetes secret for application secrets
kubectl create secret generic uitgo-secrets \
  --from-literal=POSTGRES_PASSWORD="YourSecurePassword123!" \
  --from-literal=JWT_SECRET_KEY="your-jwt-secret-key-here" \
  --from-literal=COSMOS_CONNECTION_STRING="your-cosmos-connection-string" \
  --from-literal=REDIS_CONNECTION_STRING="your-redis-connection-string"

# Enable Azure Key Vault Secrets Provider (already enabled)
az aks enable-addons --resource-group rg-uitgohuy-prod \
  --name aks-uitgohuy-prod --addons azure-keyvault-secrets-provider
```

### 4.2 Deploy Hardened Services

```bash
# Deploy all services with security contexts
kubectl apply -f k8s/userservice.yaml
kubectl apply -f k8s/tripservice.yaml
kubectl apply -f k8s/driverservice.yaml
kubectl apply -f k8s/locationservice.yaml
kubectl apply -f k8s/paymentservice.yaml

# Verify deployments
kubectl get deployments
kubectl get pods
```

### 4.3 Log Aggregation Setup

```bash
# Apply Fluent Bit configuration
kubectl apply -f k8s/fluent-bit.yaml

# Update secrets with actual Log Analytics credentials
kubectl get secret uitgo-secrets -o yaml

# Verify Fluent Bit pods
kubectl get pods -n kube-system -l k8s-app=fluent-bit
```

## Phase 5: Monitoring & Alerting

### 5.1 Azure Monitor Integration

```bash
# Apply monitoring configuration (included in Terraform)
terraform apply -target=azurerm_log_analytics_workspace.logs
terraform apply -target=azurerm_monitor_scheduled_query_rules_alert.aks_cpu_high
terraform apply -target=azurerm_monitor_metric_alert.cosmos_high_requests
terraform apply -target=azurerm_monitor_metric_alert.redis_cpu_high
```

### 5.2 Monitoring Tools Setup

```bash
# Linkerd monitoring dashboard
linkerd viz dashboard &

# Access dashboard at: http://localhost:50750

# Monitor real-time traffic
linkerd top deploy
```

### 5.3 Alert Configuration Verification

```bash
# List all alerts
az monitor metrics alert list --resource-group rg-uitgohuy-prod

# Test alert rules
az monitor scheduled-query list --resource-group rg-uitgohuy-prod
```

## Phase 6: Documentation & ADRs

### 6.1 Architecture Decision Records

ADRs have been created for major architectural decisions:
- [ADR-001: PostgreSQL cho UserService](../ADR/ADR-001-postgresql-for-userservice.md)
- [ADR-002: Cosmos DB cho TripService](../ADR/ADR-002-cosmosdb-for-tripservice.md)
- [ADR-003: Redis cho LocationService](../ADR/ADR-003-redis-for-locationservice.md)
- [ADR-004: Microservices Architecture](../ADR/ADR-004-microservices-architecture.md)
- [ADR-005: Kubernetes Deployment on AKS](../ADR/ADR-005-kubernetes-deployment.md)
- [ADR-006: VNet Service Endpoints](../ADR/ADR-006-vnet-service-endpoints.md)
- [ADR-007: Linkerd Service Mesh](../ADR/ADR-007-linkerd-service-mesh.md)
- [ADR-008: OSS Security Tooling trong CI/CD](../ADR/ADR-008-oss-security-tooling.md)

### 6.2 Runbooks

Security incident response runbooks are available in `docs/runbooks/`:
1. [High CPU Alert](runbooks/01-high-cpu-alert.md)
2. [Pod Restart Loop](runbooks/02-pod-restart-loop.md)
3. [mTLS Failure](runbooks/03-mtls-failure.md)
4. [Database Connection Issues](runbooks/04-database-connection.md)
5. [Suspicious Login Activity](runbooks/05-suspicious-login.md)
6. [Container Vulnerability](runbooks/06-container-vulnerability.md)

## Verification Checklist

### Network Security
- [ ] VNet created with 172.16.0.0/16 address space
- [ ] AKS subnet with service endpoints configured
- [ ] NSGs allow only HTTP/HTTPS from internet
- [ ] Network policies implement Zero Trust

### Container Security
- [ ] Pod Security Standards enforced (restricted)
- [ ] All services run as non-root user (1000)
- [ ] Read-only root filesystem enabled
- [ ] All capabilities dropped
- [ ] Resource limits configured

### Service Mesh
- [ ] Linkerd control plane installed
- [ ] Automatic injection enabled
- [ ] mTLS encryption verified
- [ ] Traffic monitoring active

### Secrets Management
- [ ] Azure Key Vault provider enabled
- [ ] Application secrets stored in Kubernetes secrets
- [ ] No secrets committed to Git

### Monitoring
- [ ] Azure Monitor alerts configured (7 alerts)
- [ ] Log Analytics workspace active
- [ ] Fluent Bit forwarding logs
- [ ] Linkerd Viz monitoring active

### CI/CD Security
- [ ] 6 security tools integrated in pipeline
- [ ] Security scans passing
- [ ] Container images scanned
- [ ] IaC security validation

## Daily Operations

### Monitoring Commands
```bash
# Check cluster health
kubectl get nodes,pods

# Check Linkerd status
linkerd check

# Monitor resource usage
kubectl top nodes
kubectl top pods

# Check network policies
kubectl get networkpolicies

# View logs
kubectl logs -f deployment/<service-name>

# Monitor traffic
linkerd top deploy
```

### Security Commands
```bash
# Check security context
kubectl get pod <pod-name> -o jsonpath='{.spec.securityContext}'

# Verify mTLS
linkerd edges deploy

# Check Pod Security Standards
kubectl get namespace default -o jsonpath='{.metadata.labels}'

# Monitor alerts
az monitor metrics alert list --resource-group rg-uitgohuy-prod
```

## Troubleshooting

### Common Issues

1. **Fluent Bit CrashLoopBackOff**
   - Verify Log Analytics credentials in secrets
   - Check workspace ID and shared key format

2. **Linkerd Injection Not Working**
   - Verify namespace annotation
   - Check linkerd proxy logs

3. **Network Policy Blocking Traffic**
   - Review policy selectors and ports
   - Check policy order (default-deny first)

4. **Pod Security Violations**
   - Check security context configuration
   - Verify PSP labels on namespace

5. **Authentication Issues**
   - Verify secret names and keys
   - Check Key Vault access policies

## Cost Optimization

Implemented cost-saving measures:
- Linkerd instead of Istio ($50-200/month savings)
- Service Endpoints instead of Private Endpoints ($15/month savings)
- Open-source security tools instead of commercial ($430-1,650/month savings)
- Azure Monitor within free tier limits

**Total Monthly Savings: $495-1,865**

## Next Steps

1. **Performance Testing**: Load test the secured application
2. **Security Audit**: Conduct third-party security assessment
3. **Compliance Validation**: Verify OWASP Top 10 coverage
4. **Disaster Recovery**: Test backup and restore procedures
5. **Scaling**: Configure auto-scaling policies
6. **Monitoring Enhancement**: Add custom application metrics

## Support

For issues and questions:
1. Check the relevant runbook in `docs/runbooks/`
2. Review ADRs for architectural decisions
3. Consult this implementation guide
4. Check Azure Monitor alerts and logs

## Security Best Practices Remembered

1. **Never commit secrets to Git**
2. **Always use read-only filesystems**
3. **Implement defense in depth**
4. **Follow principle of least privilege**
5. **Monitor and audit everything**
6. **Regular security updates**
7. **Zero Trust architecture**
8. **Encrypt data at rest and in transit**

This implementation guide provides a production-ready, enterprise-grade security architecture for UIT-Go microservices while maintaining cost efficiency.