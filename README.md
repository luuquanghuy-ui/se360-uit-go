# UIT-Go - Ride Hailing Platform

UIT-Go là nền tảng gọi xe được xây dựng với kiến trúc microservices sử dụng FastAPI, Python, và được triển khai trên Azure Kubernetes Service (AKS).

## 📚 Tài liệu hệ thống

- **[ARCHITECTURE.md](docs/ARCHITECTURE.md)**: Kiến trúc microservices, sơ đồ luồng nghiệp vụ, giao tiếp giữa các service
- **[DEPLOY.md](docs/DEPLOY.md)**: Chi tiết deployment trên Azure (AKS, ACR, databases), network topology, IP addresses
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
- **MongoDB**: Trips, drivers, payments data
- **Redis**: Geospatial indexing, real-time location cache

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

Xem chi tiết trong [docs/DEPLOY.md](docs/DEPLOY.md)

```bash
# Build và push images lên Azure Container Registry
az acr login --name uitgoregistry
docker build -t uitgoregistry.azurecr.io/userservice:v1.0 ./UserService
docker push uitgoregistry.azurecr.io/userservice:v1.0

# Deploy lên AKS
kubectl apply -f k8s/userservice-deployment.yaml
kubectl get pods -n uitgo
```

## 🔑 API Endpoints (Tóm tắt)

### UserService (8000)
- `POST /auth/register` - Đăng ký user
- `POST /auth/login` - Đăng nhập, nhận JWT token
- `POST /auth/token` - Lấy service token (internal)
- `GET /users/{id}` - Thông tin user

### TripService (8002)
- `POST /fare-estimate` - Ước tính giá cước
- `POST /trip-requests/complete` - Tạo chuyến đi
- `PUT /trips/{id}/assign-driver` - Tài xế nhận chuyến
- `POST /trips/{id}/complete` - Hoàn thành chuyến

### DriverService (8003)
- `POST /drivers` - Đăng ký tài xế
- `GET /drivers/{id}` - Thông tin tài xế
- `GET /drivers/internal/{id}` - Internal endpoint (cần service token)

### LocationService (8001)
- `GET /drivers/nearby` - Tìm tài xế gần
- `POST /notify/drivers` - Gửi thông báo đến drivers
- `WS /ws/driver/{id}/location` - WebSocket cập nhật vị trí
- `WS /ws/trip/{id}/{user_type}` - WebSocket theo dõi chuyến đi

### PaymentService (8004)
- `POST /process-payment` - Xử lý thanh toán
- `GET /payment-return` - VNPay callback
- `GET /users/{id}/wallet` - Thông tin ví
- `POST /wallets/top-up` - Nạp tiền

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

```
Internet
   │
   ▼
Azure Load Balancer (4.144.174.255)
   │
   ▼
┌─────────────────────────────────────┐
│  AKS Cluster                        │
│  ├─ UserService (LoadBalancer)     │
│  ├─ TripService (ClusterIP)        │
│  ├─ DriverService (ClusterIP)      │
│  ├─ LocationService (ClusterIP)    │
│  └─ PaymentService (ClusterIP)     │
└─────────────────────────────────────┘
   │
   ▼
┌─────────────────────────────────────┐
│  Azure Databases                    │
│  ├─ PostgreSQL (uitgo_users)       │
│  ├─ MongoDB (trips/drivers/payments)│
│  └─ Redis (location cache)         │
└─────────────────────────────────────┘
```

Chi tiết topology, IP addresses, và communication patterns xem [docs/DEPLOY.md](docs/DEPLOY.md)

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
│   ├── DEPLOY.md         # Deployment guide (Azure)
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

```bash
# MongoDB
docker exec -it uitgo-mongodb mongosh -u admin -p secret

# PostgreSQL
docker exec -it uitgo-postgres psql -U admin -d mydb

# Redis
docker exec -it uitgo-redis redis-cli
```

## 🔍 Monitoring & Troubleshooting

```bash
# View Kubernetes pods status
kubectl get pods -n uitgo

# View service logs
kubectl logs -f deployment/userservice -n uitgo

# Port forward for local testing
kubectl port-forward service/tripservice 8002:8000 -n uitgo

# Check service health
curl http://4.144.174.255/health  # UserService
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
- **Deployment Questions**: Đọc [DEPLOY.md](docs/DEPLOY.md)
