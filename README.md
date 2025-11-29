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

```bash
git clone <repository-url>
cd se360-uit-go
cp docs/ENV.sample .env        # Điền JWT_SECRET_KEY, Mapbox, VNPay, DB creds

# Chạy toàn bộ stack local
docker-compose up -d
docker-compose logs -f userservice

# Tắt dịch vụ
docker-compose down
```

| Service | URL local |
|---------|-----------|
| UserService | http://localhost:8000 |
| LocationService | http://localhost:8001 |
| TripService | http://localhost:8002 |
| DriverService | http://localhost:8003 |
| PaymentService | http://localhost:8004 |

Chạy từng service riêng:

```bash
cd UserService
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

## Triển khai production

1. **IaC**  
   ```bash
   cd terraform
   terraform init
   terraform apply -var="prefix=uitgo"   # tạo RG, VNet, AKS, databases, monitor
   ```
2. **CI/CD**  
   - Push lên `main` → GitHub Actions chạy test + security scans → build image cho từng service → đẩy ACR → `kubectl apply -f k8s/`.
3. **Manual fallback**  
   ```bash
   az acr login --name <acr_name>
   docker build -t <acr>/userservice:<tag> ./UserService
   docker push <acr>/userservice:<tag>
   kubectl apply -f k8s/userservice.yaml
   ```

Ingress gateway: `http://<EXTERNAL-IP>/api/<service>/...`, WebSocket `ws://<EXTERNAL-IP>/ws/...`.

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

## License & Hỗ trợ

- License: cập nhật theo nhu cầu dự án (placeholder).
- Hỗ trợ kỹ thuật: tạo issue hoặc liên hệ nhóm DevSecOps.
- Tra cứu nhanh: `docs/ARCHITECTURE.md` (kiến trúc), `docs/plan.md` (zero trust), `docs/runbooks.md` (sự cố).
