# Mô hình Đe dọa hệ thống UIT-Go

Tài liệu này mô tả tổng quan kiến trúc, các luồng dữ liệu quan trọng và phân tích rủi ro theo phương pháp STRIDE nhằm hỗ trợ triển khai kế hoạch bảo mật trong `docs/plan.md`.

## 1. Data Flow Diagram (DFD)

### 1.1 DFD Level 0 – Context Diagram
- **External Entities**: Mobile App (Khách hàng), Driver App, Hệ thống thanh toán VNPAY, Dịch vụ bản đồ Mapbox.
- **System Boundary**: Cụm AKS chứa 5 microservices (User, Trip, Driver, Location, Payment) và các dịch vụ dữ liệu (PostgreSQL, CosmosDB, Redis).
- **Luồng chính**: Người dùng tương tác với API Gateway/NGINX Ingress thông qua HTTPS; yêu cầu được định tuyến tới microservice tương ứng.

### 1.2 DFD Level 1 – Service Interactions
- **UserService**: Xác thực, quản lý hồ sơ; giao tiếp với PostgreSQL.
- **TripService**: Quản lý chuyến đi; giao tiếp CosmosDB.
- **DriverService**: Quản lý tài xế; giao tiếp CosmosDB.
- **LocationService**: Theo dõi vị trí thời gian thực; dùng Redis cache.
- **PaymentService**: Tạo và xác minh giao dịch; gọi VNPAY và CosmosDB.
- **Ingress Controller**: Bảo vệ rìa mạng, định tuyến tới service mesh.

### 1.3 DFD Level 2 – Luồng quan trọng
1. **Luồng xác thực**: Mobile app → Ingress → UserService → PostgreSQL → trả JWT.
2. **Luồng thanh toán**: PaymentService ↔ VNPAY ↔ TripService/CosmosDB.
3. **Luồng định vị**: Driver app → Ingress → LocationService → Redis + TripService.

## 2. Phân tích STRIDE

| Thành phần | Spoofing | Tampering | Repudiation | Information Disclosure | DoS | Elevation of Privilege |
|------------|----------|-----------|-------------|------------------------|-----|------------------------|
| Ingress Controller | Thiếu rate limit | Sai cấu hình ingress | Log chưa đủ | TLS downgrade/mTLS thiếu | Flood HTTP | RBAC cluster rộng |
| UserService | JWT bị giả mạo | SQL injection | Log auth thiếu | PII rò rỉ | Burst login | Quyền DB cao |
| PaymentService | Mạo danh request | Payload chỉnh sửa | Thiếu trace | Rò bí mật giao dịch | Tấn công callback | Sidecar root |
| LocationService | Websocket giả | Dữ liệu vị trí sửa | Log thiếu | Dữ liệu vị trí lộ | Spam socket | Privilege fs |
| Databases | Connection string lộ | Data tampering | Audit thiếu | Public endpoint | Connection flood | Admin account |

## 3. Attack Surface
- **External APIs**: HTTPS ingress, Websocket endpoint.
- **Service-to-service**: Traffic nội bộ giữa 5 service, kết nối DB.
- **Dependencies**: Thư viện Python, Docker base image, Terraform, GitHub Actions.
- **Secrets**: Kubernetes Secrets, GitHub Secrets, CI logs.

## 4. Đánh giá rủi ro

| Mối đe dọa | Mức độ | Lý do | Mitigation |
|------------|--------|-------|------------|
| CosmosDB & Redis public | Critical | Cho phép truy cập Internet | Phase 1.2 – Service Endpoints + NSG |
| Không có rate limiting | High | DoS dễ dàng | Phase 2 – Network policies + mesh |
| Secrets không mã hóa | High | Base64 only | Phase 1.3 – Encryption at rest |
| Thiếu SAST/SCA/DAST | High | Không phát hiện vuln sớm | Phase 3 – CI/CD security |
| Pod chạy quyền root | Medium | Lateral movement | Phase 4 – PSS + securityContext |
| Thiếu cảnh báo bảo mật | Medium | Không phát hiện sự cố | Phase 5 – Azure Monitor alerts |

## 5. Lộ trình giảm thiểu
- **Phase 1**: Bịt lỗ hổng mạng, mã hóa secret, cập nhật threat model.
- **Phase 2**: Áp dụng Linkerd + NetworkPolicy để đạt Zero Trust.
- **Phase 3**: Thêm 6 công cụ bảo mật vào pipeline và thiết lập security gates.
- **Phase 4**: Cứng hóa ứng dụng (PSS, resource limit, non-root).
- **Phase 5**: Tăng quan sát (Fluent Bit, Azure Monitor alerts, runbooks).
- **Phase 6**: Hoàn thiện ADRs, tài liệu triển khai và báo cáo chi phí.

Tài liệu này phải được cập nhật khi kiến trúc thay đổi và được xem xét ở mỗi vòng đánh giá bảo mật hàng quý.

