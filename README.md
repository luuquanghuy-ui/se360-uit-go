# UIT-Go - Ride Hailing Platform

UIT-Go là nền tảng gọi xe được xây dựng với kiến trúc microservices sử dụng FastAPI, Python, và được triển khai trên Azure Kubernetes Service (AKS).

## 📚 Tài liệu hệ thống

- **[ARCHITECTURE.md](docs/ARCHITECTURE.md)**: Kiến trúc microservices, sơ đồ luồng nghiệp vụ, giao tiếp giữa các service
- **[plan.md](docs/plan.md)**: Kế hoạch Module C - Security (DevSecOps), Zero Trust architecture, WAF, CI/CD security
- **[ENV.sample](docs/ENV.sample)**: Template file môi trường

## 🏗️ Kiến trúc hệ thống

### Microservices

- **UserService** (Port 8000): Authentication, JWT issuance, user profiles
- **TripService** (Port 8002): Trip lifecycle, matching, orchestration
- **DriverService** (Port 8003): Driver profiles, wallet management
- **LocationService** (Port 8001): Real-time location tracking, WebSocket, notifications
- **PaymentService** (Port 8004): User wallet, VNPay integration

### Databases

- **PostgreSQL**: User data (uitgo_users)
- **Azure CosmosDB** (MongoDB API): Trips, drivers, payments data
- **Azure Redis Cache**: Geospatial indexing, real-time location cache

### External APIs

- **Mapbox API**: Routing and geocoding
- **VNPay**: Payment gateway integration

## 🚀 Quick Start

### 1. Cài đặt môi trường

```bash
# Clone repository
git clone <repository-url>
cd se360-uit-go

# Tạo file .env từ template
cp docs/ENV.sample .env

# Chỉnh sửa .env với các credentials của bạn
# - JWT_SECRET_KEY
# - MAPBOX_ACCESS_TOKEN
# - VNP_TMN_CODE, VNP_HASH_SECRET
# - Database credentials
```

### 2. Chạy với Docker Compose (Development)

```bash
# Build và start all services
docker-compose up -d

# View logs
docker-compose logs -f [service_name]

# Stop all services
docker-compose down
```

**Service URLs (localhost):**
- UserService: http://localhost:8000
- LocationService: http://localhost:8001
- TripService: http://localhost:8002
- DriverService: http://localhost:8003
- PaymentService: http://localhost:8004

### 3. Deploy lên Azure Kubernetes (Production)

Deployment thông qua GitHub Actions CI/CD pipeline (xem `.github/workflows/deploy.yml`):

```bash
# Pipeline tự động chạy khi push lên main:
# 1. Test → 2. Build & Push to ACR → 3. Deploy to AKS → 4. Smoke Test

# Manual deployment (nếu cần):
az acr login --name acruitgoprod
docker build -t acruitgoprod.azurecr.io/userservice:latest ./UserService
docker push acruitgoprod.azurecr.io/userservice:latest

# Deploy lên AKS
kubectl apply -f k8s/userservice.yaml
kubectl get pods
```

## 🔑 API Endpoints (Tóm tắt)

**Base URL (Production):** `http://<INGRESS-IP>/api/<service>/`

### UserService
- `POST /api/users/auth/register` - Đăng ký user
- `POST /api/users/auth/login` - Đăng nhập, nhận JWT token
- `POST /api/users/auth/token` - Lấy service token (internal)
- `GET /api/users/{id}` - Thông tin user

### TripService
- `POST /api/trips/fare-estimate` - Ước tính giá cước
- `POST /api/trips/trip-requests/complete` - Tạo chuyến đi
- `PUT /api/trips/{id}/assign-driver` - Tài xế nhận chuyến
- `POST /api/trips/{id}/complete` - Hoàn thành chuyến

### DriverService
- `POST /api/drivers/` - Đăng ký tài xế
- `GET /api/drivers/{id}` - Thông tin tài xế
- `GET /api/drivers/internal/{id}` - Internal endpoint (cần service token)

### LocationService
- `GET /api/locations/drivers/nearby` - Tìm tài xế gần
- `POST /api/locations/notify/drivers` - Gửi thông báo đến drivers
- `WS /ws/driver/{id}/location` - WebSocket cập nhật vị trí
- `WS /ws/trip/{id}/{user_type}` - WebSocket theo dõi chuyến đi

### PaymentService
- `POST /api/payments/process-payment` - Xử lý thanh toán
- `GET /api/payments/payment-return` - VNPay callback
- `GET /api/payments/users/{id}/wallet` - Thông tin ví
- `POST /api/payments/wallets/top-up` - Nạp tiền

**Note:** Ingress sẽ rewrite `/api/users/auth/login` → `/auth/login` khi forward đến UserService

## 🔐 Authentication Flow

### User Authentication
1. User gọi `POST /auth/login` với username/password
2. UserService trả về JWT token
3. User sử dụng token trong header: `Authorization: Bearer <token>`

### Service-to-Service Authentication
1. TripService gọi `POST /auth/token` với client credentials
2. UserService trả về service JWT (type=service)
3. TripService dùng service token để gọi DriverService internal endpoints

## 🌐 Deployment Architecture (Azure)

### **Ingress API Gateway Pattern**

```
Internet (Client Apps)
   │
   ▼
Azure Load Balancer (Public IP)
   │
   ▼
┌──────────────────────────────────────────────────────┐
│  NGINX Ingress Controller (API Gateway)             │
│  - Type: LoadBalancer                                │
│  - Routes based on path:                             │
│    • /api/users/*     → UserService                  │
│    • /api/trips/*     → TripService                  │
│    • /api/drivers/*   → DriverService                │
│    • /api/locations/* → LocationService              │
│    • /api/payments/*  → PaymentService               │
│    • /ws              → LocationService (WebSocket)  │
│  - Future: + ModSecurity WAF                         │
└──────────────────────────────────────────────────────┘
   │
   ▼
┌─────────────────────────────────────┐
│  AKS Cluster (VNet: 172.16.0.0/16) │
│  All services: ClusterIP (internal) │
│  ├─ UserService:8000                │
│  ├─ TripService:8000                │
│  ├─ DriverService:8000              │
│  ├─ LocationService:8000            │
│  └─ PaymentService:8000             │
└─────────────────────────────────────┘
   │
   ▼
┌─────────────────────────────────────┐
│  Azure Databases (Private VNet)    │
│  ├─ PostgreSQL (uitgo_users)       │
│  ├─ CosmosDB (trips/drivers/pay)   │
│  └─ Redis Cache (location)         │
└─────────────────────────────────────┘
```

**Ưu điểm của Ingress Pattern:**
- ✅ Single entry point cho external traffic
- ✅ Centralized routing, SSL termination, CORS
- ✅ Không có bottleneck (không qua UserService)
- ✅ Dễ mở rộng (thêm service chỉ cần thêm path rule)
- ✅ Tất cả services đều ClusterIP (bảo mật hơn)

Chi tiết architecture và sequence diagrams xem [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)

Security planning và Zero Trust architecture xem [docs/plan.md](docs/plan.md)

## 📁 Project Structure

```
se360-uit-go/
├── UserService/          # Authentication & user management
├── TripService/          # Trip lifecycle orchestration
├── DriverService/        # Driver profiles & wallet
├── LocationService/      # Real-time location & WebSocket
├── PaymentService/       # Payment processing & VNPay
├── docs/
│   ├── ARCHITECTURE.md   # System architecture
│   ├── plan.md           # Security planning (Module C - DevSecOps)
│   └── ENV.sample        # Environment variables template
├── k8s/                  # Kubernetes manifests
├── terraform/            # Infrastructure as Code
├── docker-compose.yml    # Local development setup
└── README.md            # This file
```

## 🛠️ Development

### Chạy service riêng lẻ

```bash
cd UserService
pip install -r requirements.txt
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

### Database access

**Local development (Docker Compose):**
```bash
# MongoDB (local container)
docker exec -it uitgo-mongodb mongosh -u admin -p secret

# PostgreSQL (local container)
docker exec -it uitgo-postgres psql -U admin -d mydb

# Redis (local container)
docker exec -it uitgo-redis redis-cli
```

**Production (Azure):**
```bash
# CosmosDB - Use connection string from Azure Portal
# PostgreSQL - Connect via Azure PostgreSQL flexible server
# Redis - Connect via Azure Redis Cache endpoint
```

## 🔍 Monitoring & Troubleshooting

```bash
# View Kubernetes pods status
kubectl get pods

# View service logs
kubectl logs -f deployment/userservice

# Port forward for local testing
kubectl port-forward service/tripservice 8002:8000

# Check service health via Ingress
kubectl get ingress
# Lấy EXTERNAL-IP và test: curl http://<EXTERNAL-IP>/health
```

## 🤝 Contributing

1. Đọc [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) để hiểu kiến trúc
2. Tạo branch mới từ `main`
3. Implement feature/fix
4. Test locally với Docker Compose
5. Create pull request

## 📄 License

[License information here]

## 📞 Support

- **Issues**: Report tại GitHub Issues
- **Documentation**: Xem folder `docs/`
- **Architecture Questions**: Đọc [ARCHITECTURE.md](docs/ARCHITECTURE.md)
- **Security Planning**: Đọc [plan.md](docs/plan.md)
