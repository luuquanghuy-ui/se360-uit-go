# ADR-005: Sử dụng Kubernetes (AKS) cho Deployment

**Ngày:** 2025-10-12
**Trạng thái:** Accepted
**Người quyết định:** UIT-GO Development Team

## Context (Bối cảnh)

UIT-GO có 5 microservices cần deploy và quản lý:
- Cần orchestration để manage 5 containers
- Cần auto-scaling theo traffic
- Cần zero-downtime deployment
- Cần load balancing
- Cần health checks và auto-restart
- Team đã quen với Docker
- Budget có Azure credits (student/startup)

## Decision (Quyết định)

Chọn **Azure Kubernetes Service (AKS)** làm deployment platform.

## Alternatives Considered (Các phương án đã xem xét)

### 1. Docker Compose trên VM
**Ưu điểm:**
- Đơn giản, dễ setup
- Chi phí thấp (1 VM)
- Team đã biết Docker Compose

**Nhược điểm:**
- Không auto-scaling
- Không HA (VM crash → app die)
- Không load balancing built-in
- Không rolling updates
- Manual deployment
- Khó manage 5 services

### 2. Azure Container Instances (ACI)
**Ưu điểm:**
- Serverless containers
- Pay-per-second
- Đơn giản hơn K8s

**Nhược điểm:**
- Không orchestration tốt
- Không auto-scaling advanced
- Không service discovery tốt
- Khó inter-service networking
- Không phù hợp cho microservices

### 3. Azure App Service (Containers)
**Ưu điểm:**
- PaaS, managed
- Auto-scaling tốt
- Easy deployment

**Nhược điểm:**
- Chi phí cao hơn AKS
- Ít control hơn
- Không phù hợp cho complex microservices
- Khó customize networking

### 4. AWS ECS/EKS
**Ưu điểm:**
- Mature platform
- ECS đơn giản hơn K8s

**Nhược điểm:**
- Vendor lock-in AWS
- Team đã có Azure credits
- Phải học AWS ecosystem
- EKS đắt hơn AKS

### 5. Self-managed Kubernetes
**Ưu điểm:**
- Full control
- Không vendor lock-in
- Rẻ hơn managed K8s

**Nhược điểm:**
- Phải manage control plane
- Phải lo security patches
- Phải lo HA cho master nodes
- Time-consuming
- Team chưa có exp manage K8s cluster

## Consequences (Hậu quả/Trade-offs)

### Ưu điểm:
- ✅ **Container orchestration**: Auto-manage 5 services, restart khi crash
- ✅ **Auto-scaling**: HPA (Horizontal Pod Autoscaling) theo CPU/Memory
- ✅ **Load balancing**: Service + Ingress built-in
- ✅ **Rolling updates**: Zero-downtime deployment
- ✅ **Service discovery**: Services tìm nhau bằng DNS (userservice:8000)
- ✅ **Secrets management**: Kubernetes Secrets cho DB credentials
- ✅ **Health checks**: Liveness + Readiness probes
- ✅ **Managed**: Azure lo control plane, upgrades, security
- ✅ **CI/CD friendly**: kubectl, helm, GitHub Actions integration
- ✅ **Industry standard**: K8s skills transferable, good for CV
- ✅ **Azure integration**: ACR, Azure Database, Load Balancer

### Nhược điểm:
- ❌ **Learning curve**: Team phải học K8s concepts (Pods, Services, Deployments, Ingress)
- ❌ **Complexity**: YAML files, kubectl commands
- ❌ **Chi phí**: AKS nodes + Load Balancer ($50-100/month minimum)
- ❌ **Overkill**: K8s phức tạp cho 5 services nhỏ
- ❌ **Debugging khó**: Pod logs, networking issues

### Risks:
- **Risk**: Team chưa quen K8s → deploy sai
  - **Mitigation**:
    - Training K8s basics
    - Start with simple configs
    - Use managed services (Azure Database, Redis)
    - Document everything

- **Risk**: K8s costs vượt ngân sách
  - **Mitigation**:
    - Use 1-2 node cluster (dev/staging)
    - Auto-scale down khi idle
    - Use Azure credits
    - Monitor costs weekly

- **Risk**: Deployment complexity tăng
  - **Mitigation**:
    - Automate với CI/CD (GitHub Actions)
    - Template YAML files
    - Health checks rõ ràng

## Architecture

```
Azure AKS Cluster (aks-uitgo-prod)
├── Ingress Controller (NGINX)
│   ├── Public IP: 135.171.210.33
│   ├── Routes: /api/users, /api/trips, /ws
│
├── Deployments
│   ├── userservice (replicas: 1-3)
│   ├── driverservice (replicas: 1-2)
│   ├── tripservice (replicas: 1-3)
│   ├── locationservice (replicas: 1-2)
│   └── paymentservice (replicas: 1)
│
├── Services (ClusterIP)
│   ├── userservice:80
│   ├── driverservice:8000
│   ├── tripservice:8000
│   ├── locationservice:8000
│   └── paymentservice:8000
│
├── Secrets
│   └── uitgo-secrets (DB, Redis, JWT, VNPay)
│
└── External Services
    ├── PostgreSQL (Azure)
    ├── Cosmos DB (Azure)
    └── Redis Cache (Azure)
```

## Implementation Notes

### Cluster Config
- **Node count**: 1-3 nodes (auto-scale)
- **Node size**: Standard_B2s (2 vCPU, 4GB RAM) → cheap
- **Kubernetes version**: 1.32+
- **Network**: Azure CNI

### Deployment Strategy
- **Rolling update**: maxUnavailable=0, maxSurge=1
- **Health checks**:
  - Liveness: `/health` every 10s
  - Readiness: `/health` initial 15s
- **Resources**:
  - UserService: 256Mi-512Mi RAM, 0.25-0.5 CPU
  - TripService: 512Mi-1Gi RAM, 0.5-1 CPU
  - LocationService: 256Mi RAM, 0.25 CPU (lightweight)

### Auto-scaling
```yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: userservice-hpa
spec:
  scaleTargetRef:
    kind: Deployment
    name: userservice
  minReplicas: 1
  maxReplicas: 5
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 70
```

### Secrets Management
```bash
kubectl create secret generic uitgo-secrets \
  --from-literal=DB_PASSWORD=xxx \
  --from-literal=JWT_SECRET_KEY=xxx \
  --from-literal=REDIS_HOST=xxx \
  ...
```

### CI/CD Integration
```yaml
- name: Deploy to AKS
  run: |
    az aks set-context --resource-group rg-uitgo-prod --name aks-uitgo-prod
    kubectl apply -f k8s/
```

## Cost Estimation

- **AKS nodes**: 1x Standard_B2s = $30/month
- **Load Balancer**: $20/month
- **Bandwidth**: ~$10/month
- **Total**: ~$60/month (acceptable với Azure credits)

## Monitoring

- **Azure Monitor**: Container insights
- **Logs**: kubectl logs, Azure Log Analytics
- **Metrics**: CPU, Memory, Network
- **Alerts**: Pod crashes, High CPU

## Related Decisions

- ADR-004: Microservices Architecture (5 services cần orchestration)
- ADR-007: NGINX Ingress cho routing
- ADR-008: GitHub Actions cho CI/CD

## Future Considerations

- **Helm**: Package K8s manifests
- **ArgoCD**: GitOps deployment
- **Istio**: Service mesh cho advanced networking
- **Prometheus + Grafana**: Monitoring
