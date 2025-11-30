# UIT-Go · Secure Ride-Hailing Platform

UIT-Go là nền tảng gọi xe hiện đại được xây dựng bằng **FastAPI + Python**, triển khai trên **Azure Kubernetes Service (AKS)** với kiến trúc microservices, Zero Trust, và bộ DevSecOps đầy đủ.

## Kiến trúc tổng quan

- 5 microservices độc lập giao tiếp qua REST/WebSocket và Linkerd mTLS.
- Hệ thống chạy trên AKS, hạ tầng mô tả bằng Terraform (`terraform/`) với VNet riêng, subnets và Azure Monitor.
- CI/CD GitHub Actions (`.github/workflows/deploy.yml`) tự động test → build/push (ACR) → deploy → smoke test.

### Service matrix

| Service | Port (K8s) | Port (Local) | Database | Trách nhiệm chính |
|---------|-----------|--------------|----------|-------------------|
| `UserService` | 8000 | 8000 | PostgreSQL | Đăng ký/đăng nhập, JWT user + service token |
| `LocationService` | 8000 | 8001 | Redis GEO | Theo dõi vị trí real-time, WebSocket notify |
| `TripService` | 8000 | 8002 | CosmosDB (Mongo API) | Dàn xếp chuyến đi, gọi Mapbox, điều phối drivers |
| `DriverService` | 8000 | 8003 | CosmosDB (Mongo API) | Hồ sơ tài xế, ví tài xế, internal APIs |
| `PaymentService` | 8000 | 8004 | CosmosDB (Mongo API) | Ví người dùng, tích hợp VNPay, reconciliation |

**Lưu ý:** Trong Kubernetes, tất cả services đều expose trên port 8000 bên trong cluster. Các ports khác nhau (8001-8004) chỉ dùng cho local development với docker-compose.

## Ngăn xếp kỹ thuật

- **Application**: FastAPI, Pydantic, SQLAlchemy async, Motor.
- **Data**: Azure PostgreSQL Flexible Server, CosmosDB Mongo API, Azure Redis Cache.
- **Messaging/Realtime**: WebSocket + Redis pub/sub.
- **Infrastructure**: Terraform, AKS, ACR, NGINX Ingress, Linkerd, Fluent Bit.
- **Security**: JWT (user + service), Zero Trust network policies, Pod Security Standards, CI/CD với Bandit, Safety, TruffleHog, Checkov, Trivy, OWASP ZAP.

## Bắt đầu nhanh (local)

### Prerequisites

Trước khi bắt đầu, đảm bảo bạn đã cài đặt:

- **Docker** (version 20.10+) và **Docker Compose** (version 2.0+)
- **Python** 3.10+ (nếu chạy service riêng lẻ)
- **Git**

Kiểm tra cài đặt:
```bash
docker --version
docker-compose --version
python --version
```

### Cài đặt và chạy

1. **Clone repository và cấu hình môi trường**
   ```bash
   git clone <repository-url>
   cd se360-uit-go
   cp docs/ENV.sample .env
   ```

2. **Điền thông tin vào file `.env`**
   
   Mở file `.env` và điền các giá trị sau:
   - `MONGO_ROOT_USER`: Tên người dùng MongoDB (ví dụ: `admin`)
   - `MONGO_ROOT_PASSWORD`: Mật khẩu MongoDB (ví dụ: `secure_password_123`)
   - `JWT_SECRET_KEY`: Secret key cho JWT (tạo chuỗi ngẫu nhiên, ví dụ: `openssl rand -hex 32`)
   - `TRIPSVC_CLIENT_ID`: Client ID cho TripService (ví dụ: `tripservice`)
   - `TRIPSVC_CLIENT_SECRET`: Client secret (ví dụ: `tripservice_secret_123`)
   - `MAPBOX_ACCESS_TOKEN`: Token từ Mapbox (lấy tại https://account.mapbox.com/)
   - `VNP_TMN_CODE`: Mã merchant VNPay (sandbox hoặc production)
   - `VNP_HASH_SECRET`: Hash secret từ VNPay
   - `BASE_URL`: URL công khai để nhận callback từ VNPay (ví dụ: `http://localhost:8004` cho local)
   - `NGROK_AUTHTOKEN`: (Tùy chọn) Token ngrok nếu dùng ngrok cho webhook

   **Lưu ý:** Với môi trường local, bạn có thể dùng giá trị mẫu cho các trường không bắt buộc. Chỉ cần đảm bảo `MONGO_ROOT_USER`, `MONGO_ROOT_PASSWORD`, và `JWT_SECRET_KEY` được điền.

3. **Chạy toàn bộ stack**
   ```bash
   # Khởi động tất cả services và databases
   docker-compose up -d
   
   # Xem logs của UserService
   docker-compose logs -f userservice
   
   # Xem logs của tất cả services
   docker-compose logs -f
   ```

4. **Kiểm tra services đã chạy thành công**
   ```bash
   # Kiểm tra trạng thái containers
   docker-compose ps
   
   # Test health check
   curl http://localhost:8000/health
   curl http://localhost:8001/health
   curl http://localhost:8002/health
   curl http://localhost:8003/health
   curl http://localhost:8004/health
   ```

5. **Tắt dịch vụ**
   ```bash
   docker-compose down
   
   # Xóa cả volumes (dữ liệu sẽ bị mất)
   docker-compose down -v
   ```

### URLs các services

| Service | URL local | Health Check |
|---------|-----------|--------------|
| UserService | http://localhost:8000 | http://localhost:8000/health |
| LocationService | http://localhost:8001 | http://localhost:8001/health |
| TripService | http://localhost:8002 | http://localhost:8002/health |
| DriverService | http://localhost:8003 | http://localhost:8003/health |
| PaymentService | http://localhost:8004 | http://localhost:8004/health |

### Chạy từng service riêng (development)

Nếu muốn chạy từng service riêng để debug, bạn cần chạy databases trước:

```bash
# Chạy chỉ databases
docker-compose up -d mongodb redis postgres

# Chạy UserService
cd UserService
python -m venv .venv
# Windows:
.venv\Scripts\activate
# Linux/Mac:
source .venv/bin/activate
pip install -r requirements.txt
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

Tương tự cho các service khác:
- **LocationService**: Port 8001
- **TripService**: Port 8002  
- **DriverService**: Port 8003
- **PaymentService**: Port 8004

### Troubleshooting

**Lỗi: Port đã được sử dụng**
```bash
# Kiểm tra port nào đang được sử dụng
# Windows:
netstat -ano | findstr :8000
# Linux/Mac:
lsof -i :8000

# Thay đổi port trong docker-compose.yml hoặc dừng process đang dùng port
```

**Lỗi: Database connection failed**
- Đảm bảo containers database đã chạy: `docker-compose ps`
- Kiểm tra logs: `docker-compose logs postgres` hoặc `docker-compose logs mongodb`
- Xác nhận thông tin trong `.env` khớp với docker-compose.yml

**Lỗi: Service không start**
- Xem logs chi tiết: `docker-compose logs <service_name>`
- Kiểm tra file `.env` đã được tạo và điền đầy đủ
- Thử rebuild: `docker-compose up -d --build`

## Triển khai production (Azure)

### Prerequisites

Trước khi triển khai lên Azure, đảm bảo bạn đã cài đặt và cấu hình:

- **Azure CLI** (version 2.50+): [Hướng dẫn cài đặt](https://learn.microsoft.com/cli/azure/install-azure-cli)
- **kubectl**: [Hướng dẫn cài đặt](https://kubernetes.io/docs/tasks/tools/)
- **Terraform** (version 1.5+): [Hướng dẫn cài đặt](https://developer.hashicorp.com/terraform/downloads)
- **Docker** (để build images)
- **Azure subscription** với quyền Owner hoặc Contributor
- **Service Principal** hoặc đã đăng nhập Azure CLI (`az login`)

Kiểm tra cài đặt:
```bash
az --version
kubectl version --client
terraform version
docker --version
```

### Các bước triển khai

#### 1. Đăng nhập Azure và cấu hình

```bash
# Đăng nhập Azure
az login

# Chọn subscription (nếu có nhiều subscription)
az account list --output table
az account set --subscription "<subscription-id>"

# Tạo Service Principal (nếu chưa có, cho CI/CD)
az ad sp create-for-rbac --name "uitgo-sp" --role contributor \
  --scopes /subscriptions/<subscription-id>
```

#### 2. Triển khai Infrastructure (Terraform)

```bash
cd terraform

# Khởi tạo Terraform
terraform init

# Tạo file terraform.tfvars (KHÔNG commit file này)
cat > terraform.tfvars << EOF
prefix = "uitgo"
location = "southeastasia"
database_password = "YourSecurePassword123!"
jwt_secret_key = "your-jwt-secret-key-here"
mapbox_access_token = "your-mapbox-token"
vnpay_tmn_code = "your-vnpay-code"
vnpay_hash_secret = "your-vnpay-secret"
EOF

# Xem kế hoạch triển khai
terraform plan -var-file="terraform.tfvars"

# Triển khai infrastructure (sẽ tạo Resource Group, VNet, AKS, databases, monitor)
terraform apply -var-file="terraform.tfvars"
```

**Lưu ý:** Quá trình này có thể mất 15-30 phút để tạo AKS cluster và các resources.

#### 3. Lấy thông tin cluster và cấu hình kubectl

```bash
# Lấy tên resource group và AKS cluster từ Terraform output
RESOURCE_GROUP=$(terraform output -raw resource_group_name)
AKS_NAME=$(terraform output -raw aks_cluster_name)
ACR_NAME=$(terraform output -raw acr_name)

# Cấu hình kubectl để kết nối với AKS
az aks get-credentials --resource-group $RESOURCE_GROUP --name $AKS_NAME

# Xác nhận kết nối
kubectl get nodes
```

#### 4. Tạo Kubernetes Secrets

```bash
# Tạo secret chứa thông tin nhạy cảm
kubectl create secret generic uitgo-secrets \
  --from-literal=POSTGRES_PASSWORD="YourSecurePassword123!" \
  --from-literal=JWT_SECRET_KEY="your-jwt-secret-key-here" \
  --from-literal=MAPBOX_ACCESS_TOKEN="your-mapbox-token" \
  --from-literal=VNP_TMN_CODE="your-vnpay-code" \
  --from-literal=VNP_HASH_SECRET="your-vnpay-secret"

# Xác nhận secret đã được tạo
kubectl get secret uitgo-secrets
```

#### 5. Triển khai Services

**Cách 1: Sử dụng CI/CD (Khuyến nghị)**

- Push code lên branch `main` → GitHub Actions tự động:
  1. Chạy tests và security scans
  2. Build Docker images cho từng service
  3. Push images lên Azure Container Registry (ACR)
  4. Deploy lên AKS bằng `kubectl apply -f k8s/`
  5. Chạy smoke tests

**Cách 2: Manual deployment**

```bash
# Đăng nhập vào ACR
az acr login --name $ACR_NAME

# Build và push image cho từng service
docker build -t $ACR_NAME.azurecr.io/userservice:latest ./UserService
docker push $ACR_NAME.azurecr.io/userservice:latest

docker build -t $ACR_NAME.azurecr.io/tripservice:latest ./TripService
docker push $ACR_NAME.azurecr.io/tripservice:latest

# ... tương tự cho các service khác

# Deploy lên Kubernetes
kubectl apply -f k8s/userservice.yaml
kubectl apply -f k8s/tripservice.yaml
kubectl apply -f k8s/driverservice.yaml
kubectl apply -f k8s/locationservice.yaml
kubectl apply -f k8s/paymentservice.yaml
```

#### 6. Kiểm tra deployment

```bash
# Kiểm tra pods đang chạy
kubectl get pods -o wide

# Kiểm tra services
kubectl get services

# Kiểm tra ingress và lấy EXTERNAL-IP
kubectl get ingress
EXTERNAL_IP=$(kubectl get ingress uitgo-ingress -o jsonpath='{.status.loadBalancer.ingress[0].ip}')

# Test health check
curl http://$EXTERNAL_IP/api/users/health
curl http://$EXTERNAL_IP/api/trips/health
```

#### 7. URLs truy cập

Sau khi deployment thành công:

- **API Gateway**: `http://<EXTERNAL-IP>/api/<service>/...`
  - Ví dụ: `http://<EXTERNAL-IP>/api/users/health`
- **WebSocket**: `ws://<EXTERNAL-IP>/ws/...`
- **Linkerd Dashboard**: `linkerd viz dashboard` (port-forward)

### Hướng dẫn chi tiết

Để biết thêm chi tiết về:
- Cài đặt Linkerd service mesh
- Cấu hình Zero Trust network policies
- Setup monitoring và alerting
- Security hardening

Xem: **`docs/implementation-guide.md`** - Hướng dẫn triển khai đầy đủ từng bước.

## Bảo mật & Quan sát

- **Service mesh**: Linkerd mTLS, traffic encryption, metrics (`linkerd viz dashboard`).
- **Zero Trust**: NetworkPolicy default-deny, namespace enforced Pod Security Standards, non-root containers, read-only root filesystem.
- **Secrets**: `uitgo-secrets` + optional Azure Key Vault provider, encrypt-at-rest.
- **Security pipeline**: Bandit, Safety, TruffleHog, Checkov, Trivy, OWASP ZAP chạy trong CI.
- **Monitoring**: Azure Monitor + Log Analytics, Fluent Bit log shipping, alert pack (CPU, DB, Redis, security events).
- **Runbooks**: xem `docs/runbooks.md` và `docs/runbooks/`.

## Testing

```bash
pip install -r tests/requirements.txt
pytest tests/ -v
python tests/smoke_test.py --base-url http://localhost:8000
```

## Tài liệu liên quan

- `docs/ARCHITECTURE.md`: sơ đồ tổng quan + module chuyên sâu, sequence diagrams.
- `docs/plan.md`: roadmap Zero Trust, DevSecOps, cost-saving phases.
- `docs/cost-analysis.md`: phân tích chi phí OSS vs giải pháp enterprise.
- `docs/implementation-guide.md`: từng bước triển khai hạ tầng, mesh, monitoring.
- `docs/security-implementation-guide.md`: bóc tách lớp phòng thủ, alert, compliance.
- `docs/runbooks.md`: quy trình xử lý sự cố, link chi tiết.
- `docs/threat-model-vi.md`: threat model STRIDE + attack surface.

## Monitor & Troubleshoot nhanh

```bash
kubectl get pods -o wide
kubectl logs -f deployment/tripservice
kubectl port-forward svc/paymentservice 8004:8000
linkerd check && linkerd top deploy
```

## Đóng góp

1. Đọc kiến trúc và plan bảo mật trong `docs/`.
2. Tạo branch từ `main`, coding standard PEP8 + black.
3. Chạy test và security scans local (Bandit, Safety, pytest).
4. Tạo Pull Request, mô tả rõ tác động bảo mật.


