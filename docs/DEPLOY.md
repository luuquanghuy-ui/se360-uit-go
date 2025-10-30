# UIT-GO Deployment Architecture

## Overview
Hệ thống UIT-GO được triển khai trên Azure Kubernetes Service (AKS) với kiến trúc microservices, sử dụng Azure Container Registry (ACR) để lưu trữ Docker images và Azure Database for PostgreSQL để lưu trữ dữ liệu.

---

## Infrastructure Components

### 1. Azure Resources

#### Azure Kubernetes Service (AKS)
- **Cluster Name:** `uitgo-aks-cluster`
- **Resource Group:** `uitgo-rg`
- **Node Count:** 2-3 nodes
- **Node Size:** Standard_DS2_v2 hoặc tương đương
- **Kubernetes Version:** 1.27+

#### Azure Container Registry (ACR)
- **Registry Name:** `uitgoregistry` (hoặc tên tương tự)
- **SKU:** Basic/Standard
- **Purpose:** Lưu trữ Docker images của 5 services

#### Azure Database for PostgreSQL
- **Server Name:** `uitgo-postgres-server`
- **Database:** `uitgo_users`
- **SKU:** Flexible Server
- **Public Access:** Enabled với firewall rules
- **VNet Integration:** Có thể enabled cho bảo mật cao hơn

#### Azure Cache for Redis (Optional)
- **Name:** `uitgo-redis`
- **Purpose:** LocationService sử dụng cho geospatial queries

#### Azure MongoDB (CosmosDB hoặc MongoDB Atlas)
- **Databases:** `uitgo_trips`, `uitgo_drivers`, `uitgo_payments`
- **Connection:** External connection string

---

## Kubernetes Architecture

### Service Network Topology

```
┌─────────────────────────────────────────────────────────────────┐
│                        INTERNET                                  │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             │ HTTP/HTTPS
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│                    Azure Load Balancer                           │
│              External IP: 4.144.174.255                          │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             │ Port 80 → 8000
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│                  KUBERNETES CLUSTER (AKS)                        │
│                                                                   │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │  UserService (LoadBalancer)                                │ │
│  │  - ClusterIP: 10.0.100.43                                  │ │
│  │  - External IP: 4.144.174.255:80                           │ │
│  │  - Container Port: 8000                                     │ │
│  │  - Database: PostgreSQL (Azure)                            │ │
│  │  - Chức năng: Authentication, JWT issuance, User profiles  │ │
│  └────────────────────────────────────────────────────────────┘ │
│                                                                   │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │  TripService (ClusterIP)                                   │ │
│  │  - ClusterIP: 10.0.223.190                                 │ │
│  │  - Internal DNS: http://tripservice:8000                   │ │
│  │  - Container Port: 8000                                     │ │
│  │  - Database: MongoDB                                        │ │
│  │  - Chức năng: Trip lifecycle, matching, orchestration      │ │
│  └────────────────────────────────────────────────────────────┘ │
│                                                                   │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │  DriverService (ClusterIP)                                 │ │
│  │  - ClusterIP: 10.0.221.7                                   │ │
│  │  - Internal DNS: http://driverservice:8000                 │ │
│  │  - Container Port: 8000                                     │ │
│  │  - Database: MongoDB                                        │ │
│  │  - Chức năng: Driver profiles, wallet, internal endpoints  │ │
│  └────────────────────────────────────────────────────────────┘ │
│                                                                   │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │  LocationService (ClusterIP)                               │ │
│  │  - ClusterIP: 10.0.37.202                                  │ │
│  │  - Internal DNS: http://locationservice:8000               │ │
│  │  - Container Port: 8000                                     │ │
│  │  - Database: Redis (Azure)                                 │ │
│  │  - Chức năng: Real-time location, WebSocket, notifications │ │
│  └────────────────────────────────────────────────────────────┘ │
│                                                                   │
│  ┌────────────────────────────────────────────────────────────┐ │
│  │  PaymentService (ClusterIP)                                │ │
│  │  - ClusterIP: 10.0.6.187                                   │ │
│  │  - Internal DNS: http://paymentservice:8000                │ │
│  │  - Container Port: 8000                                     │ │
│  │  - Database: MongoDB                                        │ │
│  │  - Chức năng: Wallet, VNPay integration, payment callbacks │ │
│  └────────────────────────────────────────────────────────────┘ │
│                                                                   │
└───────────────────────────────────────────────────────────────────┘
                             │
                             │ Private connection
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│                    AZURE DATABASES                               │
│                                                                   │
│  ┌──────────────────────┐  ┌──────────────────────┐             │
│  │  PostgreSQL          │  │  Redis Cache         │             │
│  │  (uitgo_users)       │  │  (geospatial data)   │             │
│  └──────────────────────┘  └──────────────────────┘             │
│                                                                   │
│  ┌──────────────────────┐  ┌──────────────────────┐             │
│  │  MongoDB/CosmosDB    │  │  MongoDB/CosmosDB    │             │
│  │  (uitgo_trips)       │  │  (uitgo_drivers)     │             │
│  └──────────────────────┘  └──────────────────────┘             │
│                                                                   │
│  ┌──────────────────────┐                                        │
│  │  MongoDB/CosmosDB    │                                        │
│  │  (uitgo_payments)    │                                        │
│  └──────────────────────┘                                        │
└───────────────────────────────────────────────────────────────────┘
                             │
                             │ HTTPS
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│                    EXTERNAL SERVICES                             │
│                                                                   │
│  - Mapbox API (routing, geocoding)                              │
│  - VNPay Payment Gateway (sandbox/production)                   │
└───────────────────────────────────────────────────────────────────┘
```

---

## Inter-Service Communication

### 1. Internal Service-to-Service (Trong Cluster)

Các service giao tiếp với nhau qua **Kubernetes DNS** sử dụng **ClusterIP**:

#### **TripService → UserService**
```
URL: http://userservice:8000/auth/token
Method: POST
Purpose: Lấy service token để authenticate với DriverService
Headers: {"client_id": "TRIPSVC_CLIENT_ID", "client_secret": "TRIPSVC_CLIENT_SECRET"}
```

#### **TripService → DriverService**
```
URL: http://driverservice:8000/drivers/internal/{driver_id}
Method: GET
Purpose: Lấy thông tin chi tiết driver
Headers: {"Authorization": "Bearer <service_token>"}
Authentication: Service JWT token từ UserService
```

#### **TripService → LocationService**
```
# Tìm driver gần
URL: http://locationservice:8000/drivers/nearby
Method: GET
Query: ?lat=10.8231&lng=106.6297&radius=5

# Gửi thông báo đến drivers
URL: http://locationservice:8000/notify/drivers
Method: POST
Body: {"driver_ids": [...], "message": {...}}

# Gửi thông báo đến passenger
URL: http://locationservice:8000/notify/trip/{trip_id}/passenger
Method: POST
```

#### **TripService → PaymentService**
```
URL: http://paymentservice:8000/process-payment
Method: POST
Body: {"trip_id": "...", "amount": 50000, "user_id": "..."}
Purpose: Xử lý thanh toán E-Wallet hoặc tạo VNPay URL
```

### 2. External Access (Từ Internet)

#### **User/Frontend → UserService**
```
URL: http://4.144.174.255/auth/login
Method: POST
Body: {"username": "user1", "password": "pass123"}
Response: {"access_token": "eyJ...", "token_type": "bearer"}
```

#### **VNPay → PaymentService**
```
URL: http://<NGROK_OR_PUBLIC_IP>/payment-return
Method: GET
Query: ?vnp_TxnRef=...&vnp_ResponseCode=00&vnp_SecureHash=...
Purpose: Payment callback sau khi user thanh toán trên VNPay
```

### 3. WebSocket Connections (Real-time)

#### **Driver App → LocationService**
```
WebSocket URL: ws://locationservice:8000/ws/driver/{driver_id}/location
Protocol: WebSocket
Purpose: Driver gửi GPS location updates mỗi 5-10s
Message Format: {"lat": 10.8231, "lng": 106.6297, "timestamp": "..."}
Storage: Redis GEOADD drivers:locations {lng} {lat} driver:{id}
```

#### **Passenger/Driver App → LocationService (Trip Room)**
```
WebSocket URL: ws://locationservice:8000/ws/trip/{trip_id}/{user_type}
user_type: "passenger" | "driver"
Purpose: Real-time trip updates, location sharing, status changes
Messages:
  - trip_status_update: {"status": "accepted", "driver_id": "..."}
  - driver_location: {"lat": ..., "lng": ...}
  - trip_completed: {"final_amount": 50000}
```

---

## Authentication & Authorization Flow

### 1. User Authentication (UserService)

```
┌──────────┐        POST /auth/login        ┌─────────────┐
│  Client  │ ───────────────────────────────>│ UserService │
│          │  {username, password}           │  (Port 80)  │
│          │                                  │             │
│          │ <───────────────────────────────│             │
│          │  {access_token: JWT}            └─────────────┘
└──────────┘
     │
     │  Subsequent requests
     │  Header: Authorization: Bearer <JWT>
     ▼
┌─────────────┐
│ Any Service │ (validates JWT using SECRET_KEY)
└─────────────┘
```

**JWT Payload (User Token):**
```json
{
  "sub": "user_id_123",
  "username": "john_doe",
  "type": "user",
  "exp": 1730000000
}
```

### 2. Service-to-Service Authentication

```
┌─────────────┐     1. Request Service Token      ┌─────────────┐
│ TripService │ ─────────────────────────────────> │ UserService │
│             │  POST /auth/token                  │             │
│             │  {client_id, client_secret}        │             │
│             │                                     │             │
│             │ <───────────────────────────────── │             │
│             │  {access_token: service_jwt}       └─────────────┘
│             │
│             │  2. Call Internal Endpoint
│             │  Authorization: Bearer <service_jwt>
│             │
│             ▼
│         ┌─────────────────┐
│         │  DriverService  │
│         │  /drivers/      │
│         │  internal/{id}  │
│         └─────────────────┘
└─────────────┘
```

**JWT Payload (Service Token):**
```json
{
  "sub": "tripservice",
  "client_id": "TRIPSVC_CLIENT_ID",
  "type": "service",
  "exp": 1730000000
}
```

**Environment Variables Required:**
```bash
# UserService & DriverService (MUST BE IDENTICAL)
JWT_SECRET_KEY=your-super-secret-key-min-32-chars

# TripService
TRIPSVC_CLIENT_ID=tripservice_client_001
TRIPSVC_CLIENT_SECRET=super_secret_trip_key_456
USERSERVICE_URL=http://userservice:8000
DRIVERSERVICE_URL=http://driverservice:8000
```

---

## Database Connections

### PostgreSQL (UserService)
```bash
# Connection String (from Kubernetes Secret or ConfigMap)
DATABASE_URL=postgresql://admin@uitgo-postgres-server:password@uitgo-postgres-server.postgres.database.azure.com:5432/uitgo_users?sslmode=require

# Tables
- users (id, username, hashed_password, email, full_name, phone_number, role)
```

### MongoDB (TripService, DriverService, PaymentService)
```bash
# Connection Strings
MONGO_URI=mongodb+srv://admin:password@cluster.mongodb.net/

# Databases
- uitgo_trips
  Collections: trips, trip_offers

- uitgo_drivers
  Collections: drivers, driver_wallets

- uitgo_payments
  Collections: user_wallets, transactions
```

### Redis (LocationService)
```bash
# Connection
REDIS_URL=redis://uitgo-redis.redis.cache.windows.net:6380?ssl=true&password=...

# Data Structures
- Key: drivers:locations
  Type: GEOSPATIAL (Redis GEO)
  Commands: GEOADD, GEORADIUS

- Key: driver:{driver_id}:status
  Type: STRING
  Values: online | offline | busy

- Key: connected_drivers
  Type: SET
  Members: driver_id_1, driver_id_2, ...
```

---

## External Integrations

### 1. Mapbox API (TripService)
```bash
# Endpoint
POST https://api.mapbox.com/directions/v5/mapbox/driving/{coordinates}

# Request
?access_token=MAPBOX_ACCESS_TOKEN
&geometries=geojson
&steps=true

# Response
{
  "routes": [{
    "distance": 5432,  // meters
    "duration": 876,   // seconds
    "geometry": {...}  // GeoJSON
  }]
}

# Used For
- Tính khoảng cách và thời gian di chuyển
- Lấy route geometry để hiển thị trên map
- Estimate trip fare
```

### 2. VNPay Payment Gateway (PaymentService)
```bash
# Payment URL Generation
URL: https://sandbox.vnpayment.vn/paymentv2/vpcpay.html
Method: GET (redirect user)
Parameters:
  - vnp_TmnCode: VNP_TMN_CODE (merchant code)
  - vnp_Amount: 5000000 (50,000 VND * 100)
  - vnp_OrderInfo: "Payment for trip TRIP123"
  - vnp_ReturnUrl: {BASE_URL}/payment-return
  - vnp_SecureHash: HMACSHA512(params, VNP_HASH_SECRET)

# Callback (Return URL)
URL: {BASE_URL}/payment-return
Query: ?vnp_TxnRef=...&vnp_ResponseCode=00&vnp_SecureHash=...
Validation: Verify vnp_SecureHash matches computed hash

# Response Codes
- 00: Success
- 07: Suspicious transaction
- 09: Card not registered for online payment
- 24: Transaction canceled
```

**Environment Variables:**
```bash
VNP_TMN_CODE=YOUR_MERCHANT_CODE
VNP_HASH_SECRET=YOUR_HASH_SECRET_KEY
BASE_URL=https://your-public-domain.com  # MUST be HTTPS for production
```

---

## Deployment Process

### 1. Build & Push Docker Images

```bash
# Login to ACR
az acr login --name uitgoregistry

# Build and tag images
docker build -t uitgoregistry.azurecr.io/userservice:v1.0 ./UserService
docker build -t uitgoregistry.azurecr.io/tripservice:v1.0 ./TripService
docker build -t uitgoregistry.azurecr.io/driverservice:v1.0 ./DriverService
docker build -t uitgoregistry.azurecr.io/locationservice:v1.0 ./LocationService
docker build -t uitgoregistry.azurecr.io/paymentservice:v1.0 ./PaymentService

# Push to ACR
docker push uitgoregistry.azurecr.io/userservice:v1.0
docker push uitgoregistry.azurecr.io/tripservice:v1.0
docker push uitgoregistry.azurecr.io/driverservice:v1.0
docker push uitgoregistry.azurecr.io/locationservice:v1.0
docker push uitgoregistry.azurecr.io/paymentservice:v1.0
```

### 2. Configure Kubernetes Secrets

```bash
# Create namespace
kubectl create namespace uitgo

# Database credentials
kubectl create secret generic db-credentials \
  --from-literal=postgres-user=admin \
  --from-literal=postgres-password=your-password \
  --from-literal=mongo-uri=mongodb+srv://... \
  --from-literal=redis-url=redis://... \
  -n uitgo

# Service secrets
kubectl create secret generic service-secrets \
  --from-literal=jwt-secret=your-super-secret-key \
  --from-literal=tripsvc-client-id=tripservice_client_001 \
  --from-literal=tripsvc-client-secret=super_secret_key \
  --from-literal=mapbox-token=pk.eyJ... \
  --from-literal=vnpay-tmn-code=YOUR_CODE \
  --from-literal=vnpay-hash-secret=YOUR_SECRET \
  -n uitgo

# ACR authentication (if using private registry)
kubectl create secret docker-registry acr-secret \
  --docker-server=uitgoregistry.azurecr.io \
  --docker-username=uitgoregistry \
  --docker-password=<ACR_PASSWORD> \
  -n uitgo
```

### 3. Deploy Services

```bash
# Deploy all services
kubectl apply -f k8s/userservice-deployment.yaml
kubectl apply -f k8s/tripservice-deployment.yaml
kubectl apply -f k8s/driverservice-deployment.yaml
kubectl apply -f k8s/locationservice-deployment.yaml
kubectl apply -f k8s/paymentservice-deployment.yaml

# Check deployment status
kubectl get deployments -n uitgo
kubectl get pods -n uitgo
kubectl get services -n uitgo

# View logs
kubectl logs -f deployment/userservice -n uitgo
```

### 4. Verify Deployment

```bash
# Test external access
curl http://4.144.174.255/health

# Test internal service communication (exec into pod)
kubectl exec -it <tripservice-pod> -n uitgo -- /bin/bash
curl http://userservice:8000/health
curl http://driverservice:8000/health
```

---

## Network Policies (Optional - Bảo mật nâng cao)

```yaml
# Chỉ cho phép TripService gọi DriverService internal endpoints
apiVersion: networking.k8s.io/v1
kind: NetworkPolicy
metadata:
  name: driverservice-allow-from-trip
  namespace: uitgo
spec:
  podSelector:
    matchLabels:
      app: driverservice
  policyTypes:
  - Ingress
  ingress:
  - from:
    - podSelector:
        matchLabels:
          app: tripservice
    ports:
    - protocol: TCP
      port: 8000
```

---

## Monitoring & Troubleshooting

### Health Check Endpoints

```bash
# UserService
GET http://4.144.174.255/health
Response: {"status": "healthy", "database": "connected"}

# Internal services (from within cluster)
GET http://tripservice:8000/health
GET http://driverservice:8000/health
GET http://locationservice:8000/health
GET http://paymentservice:8000/health
```

### Common Issues

#### 1. Service Cannot Connect to Database
```bash
# Check connection string in secret
kubectl get secret db-credentials -n uitgo -o yaml

# Test connection from pod
kubectl exec -it <pod-name> -n uitgo -- /bin/bash
python -c "import psycopg2; conn = psycopg2.connect('postgresql://...')"
```

#### 2. Service-to-Service Authentication Fails
```bash
# Verify JWT_SECRET_KEY is identical
kubectl exec -it <userservice-pod> -- env | grep JWT_SECRET
kubectl exec -it <driverservice-pod> -- env | grep JWT_SECRET

# Test token generation
curl -X POST http://userservice:8000/auth/token \
  -H "Content-Type: application/json" \
  -d '{"client_id":"...","client_secret":"..."}'
```

#### 3. WebSocket Connections Drop
```bash
# Check Redis connection
kubectl exec -it <locationservice-pod> -- redis-cli -h <redis-host> PING

# Monitor WebSocket connections
kubectl logs -f deployment/locationservice | grep "WebSocket"
```

---

## Scaling

### Horizontal Pod Autoscaling

```bash
# Enable metrics server (if not already)
kubectl apply -f https://github.com/kubernetes-sigs/metrics-server/releases/latest/download/components.yaml

# Create HPA for services
kubectl autoscale deployment tripservice --cpu-percent=70 --min=2 --max=10 -n uitgo
kubectl autoscale deployment locationservice --cpu-percent=80 --min=2 --max=8 -n uitgo

# Check HPA status
kubectl get hpa -n uitgo
```

---

## Security Considerations

### 1. Secrets Management
- ✅ Sử dụng Kubernetes Secrets (hiện tại)
- 🔄 Khuyến nghị: Azure Key Vault với CSI driver
- 🔄 Rotate secrets định kỳ (JWT_SECRET, database passwords)

### 2. Network Security
- ✅ Internal services dùng ClusterIP (không expose ra ngoài)
- ✅ Service-to-service authentication với JWT
- 🔄 Khuyến nghị: Implement NetworkPolicies
- 🔄 Khuyến nghị: Mutual TLS (mTLS) giữa services

### 3. Database Security
- ✅ Azure PostgreSQL có firewall rules
- ✅ SSL/TLS enabled cho database connections
- 🔄 Khuyến nghị: VNet integration cho AKS và databases
- 🔄 Khuyến nghị: Private endpoints

### 4. API Security
- ✅ JWT authentication cho user endpoints
- ✅ Service tokens cho internal endpoints
- 🔄 Khuyến nghị: Rate limiting
- 🔄 Khuyến nghị: API Gateway (Azure API Management)

---

## Cost Optimization

### Current Resources
- **AKS:** 2-3 nodes × Standard_DS2_v2 (~$70-100/month)
- **Azure Database for PostgreSQL:** Flexible Server (~$50-100/month)
- **Azure Cache for Redis:** Basic tier (~$15-30/month)
- **Load Balancer:** 1 public IP (~$3-5/month)
- **Azure Container Registry:** Basic (~$5/month)

### Optimization Tips
1. **Right-size pods:** Set appropriate CPU/memory requests and limits
2. **Use spot instances:** Cho non-critical workloads
3. **Auto-scaling:** Scale down trong off-peak hours
4. **Reserved instances:** Nếu có budget dài hạn

---

## Disaster Recovery

### Backup Strategy
```bash
# Database backups (automated by Azure)
- PostgreSQL: Point-in-time restore (7-35 days)
- MongoDB Atlas: Continuous backups
- Redis: Daily snapshots

# Kubernetes state backup
velero backup create uitgo-backup --include-namespaces uitgo

# Container images: Stored in ACR with geo-replication (optional)
```

### Recovery Procedure
1. Restore database từ backup
2. Redeploy services từ latest images trong ACR
3. Restore Kubernetes configs từ Git repository
4. Update DNS/Load Balancer nếu cần

---

## CI/CD Pipeline (Khuyến nghị)

```yaml
# Azure DevOps / GitHub Actions workflow
stages:
  1. Build: Docker build cho 5 services
  2. Test: Unit tests, integration tests
  3. Push: Push images to ACR
  4. Deploy: kubectl apply to AKS
  5. Verify: Health checks, smoke tests
  6. Rollback: Tự động rollback nếu verify fails
```

---

## Contact & Support

**Infrastructure:** Azure AKS, ACR, PostgreSQL, Redis
**Orchestration:** Kubernetes 1.27+
**Container Registry:** Azure Container Registry
**Deployment Method:** kubectl + YAML manifests (hoặc Helm charts)

**Current Status:**
- ✅ UserService: Publicly accessible via LoadBalancer (4.144.174.255)
- ✅ Other services: Internal ClusterIP (accessible within cluster)
- 🔄 Next steps: Setup Ingress hoặc API Gateway cho unified external access
