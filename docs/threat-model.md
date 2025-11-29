# Mô hình Đe dọa hệ thống UIT-Go

Tài liệu này mô tả tổng quan kiến trúc, các luồng dữ liệu quan trọng và phân tích rủi ro theo phương pháp STRIDE nhằm hỗ trợ triển khai kế hoạch bảo mật trong `docs/plan.md`.

**Phiên bản:** 2.0  
**Ngày cập nhật:** 2025-01-15  
**Người review:** Security Team

---

## 1. Data Flow Diagram (DFD)

### 1.1 DFD Level 0 – Context Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                    External Entities                          │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐        │
│  │ Mobile App   │  │ Driver App   │  │ VNPay Gateway│        │
│  │ (Passenger)  │  │              │  │              │        │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘        │
│         │                  │                  │                │
│         └──────────────────┼──────────────────┘                │
│                            │                                   │
│                            ▼                                   │
│              ┌─────────────────────────┐                      │
│              │  NGINX Ingress          │                      │
│              │  (API Gateway + TLS)    │                      │
│              └───────────┬─────────────┘                      │
│                          │                                     │
│                          ▼                                     │
│        ┌──────────────────────────────────────┐              │
│        │  AKS Cluster (Zero Trust Network)     │              │
│        │  ┌──────────┐  ┌──────────┐          │              │
│        │  │UserService│ │TripService│         │              │
│        │  │DriverSvc │ │LocationSvc│         │              │
│        │  │PaymentSvc│ │           │         │              │
│        │  └────┬─────┘  └────┬─────┘         │              │
│        │       │              │              │              │
│        │  ┌────┴──────────────┴────┐         │              │
│        │  │  Linkerd Service Mesh  │         │              │
│        │  │  (mTLS Encryption)      │         │              │
│        │  └────────────────────────┘         │              │
│        └───────────┬──────────────────────────┘              │
│                    │                                          │
│        ┌───────────┼───────────┐                            │
│        │           │           │                            │
│        ▼           ▼           ▼                            │
│  ┌─────────┐ ┌──────────┐ ┌────────┐                        │
│  │PostgreSQL│ │ CosmosDB │ │ Redis │                        │
│  │(Private) │ │(Service  │ │(VNet) │                        │
│  │          │ │Endpoint) │ │       │                        │
│  └─────────┘ └──────────┘ └────────┘                        │
└─────────────────────────────────────────────────────────────┘
```

- **External Entities**: Mobile App (Khách hàng), Driver App, Hệ thống thanh toán VNPAY, Dịch vụ bản đồ Mapbox.
- **System Boundary**: Cụm AKS chứa 5 microservices (User, Trip, Driver, Location, Payment) và các dịch vụ dữ liệu (PostgreSQL, CosmosDB, Redis).
- **Luồng chính**: Người dùng tương tác với API Gateway/NGINX Ingress thông qua HTTPS; yêu cầu được định tuyến tới microservice tương ứng.

### 1.2 DFD Level 1 – Service Interactions

- **UserService**: Xác thực, quản lý hồ sơ; giao tiếp với PostgreSQL qua SQLAlchemy async.
- **TripService**: Quản lý chuyến đi; giao tiếp CosmosDB (MongoDB API), gọi Mapbox API, orchestrate các services khác.
- **DriverService**: Quản lý tài xế, ví tài xế; giao tiếp CosmosDB, expose internal APIs với service token protection.
- **LocationService**: Theo dõi vị trí thời gian thực; dùng Redis GEO, quản lý WebSocket connections.
- **PaymentService**: Xử lý thanh toán, ví người dùng; gọi VNPay, giao tiếp CosmosDB, callback handling.
- **Ingress Controller**: Bảo vệ rìa mạng, định tuyến tới service mesh, TLS termination.

### 1.3 DFD Level 2 – Luồng quan trọng

#### 1.3.1 Luồng xác thực (Authentication Flow)
```
Mobile App → Ingress (HTTPS) → UserService → PostgreSQL
    ↓
UserService verify credentials (bcrypt)
    ↓
Generate JWT token (HS256, 30min expiry)
    ↓
Return token to Mobile App
```

**Dữ liệu nhạy cảm:**
- Password (hashed với bcrypt)
- Email, phone number (PII)
- JWT secret key

#### 1.3.2 Luồng thanh toán (Payment Flow)
```
TripService → PaymentService (/v1/payment/process)
    ↓
PaymentService check wallet balance
    ↓
If insufficient: Generate VNPay payment URL (HMAC-SHA512)
    ↓
User redirects to VNPay → Complete payment
    ↓
VNPay → PaymentService (/v1/payment/vnpay_ipn) [IPN]
VNPay → PaymentService (/v1/payment/vnpay_return) [Return URL]
    ↓
PaymentService verify hash → Update wallet → Notify TripService
```

**Dữ liệu nhạy cảm:**
- Transaction amounts
- Payment card information (handled by VNPay)
- VNPay hash secret
- Wallet balances

#### 1.3.3 Luồng định vị (Location Tracking Flow)
```
Driver App → WebSocket (wss://) → LocationService
    ↓
LocationService → Redis GEO (GEOADD drivers:locations)
    ↓
TripService → LocationService (/drivers/nearby)
    ↓
LocationService → Redis GEO (GEORADIUS query)
    ↓
Return nearby drivers to TripService
```

**Dữ liệu nhạy cảm:**
- Real-time GPS coordinates
- Driver locations (privacy concern)
- Trip routes

#### 1.3.4 Luồng Service-to-Service Authentication
```
TripService → UserService (/auth/token)
    ↓
UserService verify client credentials (TRIPSVC_CLIENT_ID/SECRET)
    ↓
Generate service JWT (type: "service", aud: "driverservice")
    ↓
TripService → DriverService (/drivers/internal/{id})
    ↓
DriverService verify service token (check type, aud, signature)
```

**Dữ liệu nhạy cảm:**
- Service client credentials
- Service JWT tokens
- Internal driver information

---

## 2. Phân tích STRIDE

### 2.1 Ingress Controller / API Gateway

| Threat | Mô tả | Mức độ | Mitigation hiện tại | Gaps |
|--------|-------|--------|---------------------|------|
| **Spoofing** | Attacker giả mạo request từ trusted source | High | IP whitelisting (NSG) | ❌ Không có rate limiting per IP |
| **Tampering** | Modify request/response trong transit | Medium | ✅ TLS 1.2+ enforced | ⚠️ CORS allow-origin: "*" (quá rộng) |
| **Repudiation** | Không có audit log cho requests | Medium | ⚠️ Basic logging | ❌ Thiếu structured logging với request ID |
| **Information Disclosure** | TLS downgrade attack | Low | ✅ TLS 1.2+ minimum | ✅ mTLS cho inter-service |
| **DoS** | HTTP flood attack | High | ⚠️ Network policies | ❌ Không có rate limiting |
| **Elevation of Privilege** | RBAC misconfiguration | Medium | ✅ Restricted RBAC | ⚠️ Cần review định kỳ |

**CORS Configuration Risk:**
```yaml
nginx.ingress.kubernetes.io/enable-cors: "true"
nginx.ingress.kubernetes.io/cors-allow-origin: "*"  # ⚠️ QUÁ RỘNG
```
**Mitigation:** Nên restrict CORS chỉ cho domain của mobile app.

### 2.2 UserService

| Threat | Mô tả | Mức độ | Mitigation hiện tại | Gaps |
|--------|-------|--------|---------------------|------|
| **Spoofing** | JWT token bị giả mạo | High | ✅ HS256 với SECRET_KEY | ⚠️ SECRET_KEY có default value trong code |
| **Tampering** | SQL injection | Medium | ✅ SQLAlchemy ORM (parameterized queries) | ✅ Input validation với Pydantic |
| **Repudiation** | Không log failed login attempts | Medium | ⚠️ Basic logging | ❌ Thiếu audit log cho auth events |
| **Information Disclosure** | PII rò rỉ trong logs/response | High | ⚠️ Logs có thể chứa email | ❌ Không có PII masking |
| **DoS** | Brute force login | High | ❌ Không có rate limiting | ❌ Không có account lockout |
| **Elevation of Privilege** | User có quyền admin | Medium | ✅ Role-based access | ⚠️ Cần review user_type validation |

**JWT Implementation Risks:**
- Default SECRET_KEY trong code: `"default-secret-key-change-in-production-min-32-chars"`
- Token expiry: 30 minutes (có thể quá dài cho sensitive operations)
- Không có refresh token mechanism
- Service tokens expire sau 15 phút (ngắn hơn user tokens)

### 2.3 PaymentService

| Threat | Mô tả | Mức độ | Mitigation hiện tại | Gaps |
|--------|-------|--------|---------------------|------|
| **Spoofing** | Attacker giả mạo VNPay callback | High | ✅ HMAC-SHA512 hash verification | ⚠️ IP whitelist VNPay (chưa implement) |
| **Tampering** | Modify payment amount trong callback | High | ✅ Hash verification | ⚠️ Race condition: IPN và Return URL có thể xử lý cùng lúc |
| **Repudiation** | Không có audit trail cho payment | Medium | ✅ Transaction logs trong MongoDB | ⚠️ Cần immutable audit log |
| **Information Disclosure** | Payment details rò rỉ | High | ⚠️ Logs có thể chứa amount | ❌ Không có PII masking cho payment logs |
| **DoS** | Spam payment callbacks | Medium | ✅ Hash verification reject invalid | ⚠️ Không có rate limiting cho callback endpoints |
| **Elevation of Privilege** | Unauthorized wallet access | High | ✅ Service token required | ⚠️ Wallet top-up endpoint không có auth check |

**Payment Flow Vulnerabilities:**
1. **Idempotency**: Có check transaction_id nhưng có thể có race condition giữa IPN và Return URL
2. **Amount Validation**: Không verify amount từ callback với original transaction
3. **Callback Replay**: Không có nonce/timestamp check để prevent replay attacks

### 2.4 LocationService

| Threat | Mô tả | Mức độ | Mitigation hiện tại | Gaps |
|--------|-------|--------|---------------------|------|
| **Spoofing** | WebSocket connection giả mạo driver | High | ⚠️ WebSocket không có authentication | ❌ Không verify driver_id trong WebSocket |
| **Tampering** | Modify location data | Medium | ⚠️ Input validation với Pydantic | ❌ Không verify location coordinates hợp lệ |
| **Repudiation** | Không log location updates | Low | ⚠️ Basic logging | ❌ Thiếu audit log cho location tracking |
| **Information Disclosure** | Location data rò rỉ | High | ⚠️ Redis không encrypt at rest | ⚠️ WebSocket không có TLS (wss://) |
| **DoS** | WebSocket connection flood | High | ⚠️ Connection pooling | ❌ Không có connection limit per driver |
| **Elevation of Privilege** | Access other drivers' locations | Medium | ⚠️ WebSocket room isolation | ❌ Không verify user có quyền access trip room |

**WebSocket Security Issues:**
- WebSocket endpoints không có authentication: `/ws/driver/{driver_id}/location`
- Không verify driver_id trong WebSocket connection
- Trip room không verify user có quyền access trip đó
- CORS allow-origin: "*" cho WebSocket

### 2.5 TripService

| Threat | Mô tả | Mức độ | Mitigation hiện tại | Gaps |
|--------|-------|--------|---------------------|------|
| **Spoofing** | Giả mạo trip request | Medium | ⚠️ User token required | ❌ Không verify user có quyền tạo trip |
| **Tampering** | Modify trip data | Medium | ✅ MongoDB atomic updates | ⚠️ Race condition khi nhiều drivers accept |
| **Repudiation** | Không log trip state changes | Medium | ⚠️ Basic logging | ❌ Thiếu audit log cho trip lifecycle |
| **Information Disclosure** | Trip details rò rỉ | Medium | ⚠️ User token required | ⚠️ Không verify user có quyền xem trip |
| **DoS** | Spam trip creation | Medium | ❌ Không có rate limiting | ❌ Không có trip creation limit per user |
| **Elevation of Privilege** | Unauthorized trip modification | Medium | ⚠️ User token required | ❌ Không verify user là owner của trip |

**Trip Orchestration Risks:**
- Race condition: Nhiều drivers cùng accept một trip → giải quyết bằng MongoDB atomic update
- Service token caching: Có cache service token nhưng không có refresh mechanism
- Mapbox API key: Có thể bị lộ trong logs nếu không cẩn thận

### 2.6 DriverService

| Threat | Mô tả | Mức độ | Mitigation hiện tại | Gaps |
|--------|-------|--------|---------------------|------|
| **Spoofing** | Service token bị reuse | High | ✅ Audience claim validation | ⚠️ Token expiry 15 phút (có thể quá dài) |
| **Tampering** | Modify driver profile | Medium | ✅ User token required | ⚠️ Không verify user là owner của driver profile |
| **Repudiation** | Không log driver actions | Low | ⚠️ Basic logging | ❌ Thiếu audit log |
| **Information Disclosure** | Driver PII rò rỉ | High | ✅ Service token required cho internal APIs | ⚠️ Logs có thể chứa driver info |
| **DoS** | Spam internal API calls | Low | ✅ Service token required | ⚠️ Không có rate limiting |
| **Elevation of Privilege** | Unauthorized wallet access | High | ✅ User token required | ⚠️ Wallet top-up không có admin check |

### 2.7 Databases

| Threat | Mô tả | Mức độ | Mitigation hiện tại | Gaps |
|--------|-------|--------|---------------------|------|
| **Spoofing** | Connection string lộ | Critical | ✅ Kubernetes Secrets | ⚠️ Secrets có thể bị expose trong logs |
| **Tampering** | Data tampering | High | ✅ ACID transactions (PostgreSQL) | ⚠️ CosmosDB không có ACID across documents |
| **Repudiation** | Không có audit log | Medium | ⚠️ Application-level logging | ❌ Không có database audit logs |
| **Information Disclosure** | Public endpoint | Critical | ✅ Service Endpoints + NSG | ✅ Private access only |
| **DoS** | Connection flood | High | ✅ Connection pooling | ⚠️ Pool size có thể không đủ |
| **Elevation of Privilege** | Admin account compromise | Critical | ✅ Least privilege DB users | ⚠️ Cần rotate passwords định kỳ |

**Database Security:**
- PostgreSQL: Private VNet, SSL/TLS required, connection pooling
- CosmosDB: Service Endpoints, TLS 1.2+, VNet filtering
- Redis: VNet integration, TLS 1.2+ (port 6380)

---

## 3. Attack Surface

### 3.1 External Attack Surface

1. **HTTPS APIs** (qua NGINX Ingress):
   - `/api/users/*` - User authentication, profile management
   - `/api/trips/*` - Trip creation, management
   - `/api/drivers/*` - Driver profile, wallet
   - `/api/locations/*` - Location queries
   - `/api/payments/*` - Payment processing, VNPay callbacks

2. **WebSocket Endpoints**:
   - `ws://locationservice/ws/driver/{driver_id}/location` - Driver location stream
   - `ws://locationservice/ws/trip/{trip_id}/{user_type}` - Trip room communication

3. **External Integrations**:
   - VNPay Payment Gateway (callbacks)
   - Mapbox API (directions, geocoding)

### 3.2 Internal Attack Surface

1. **Service-to-Service Communication**:
   - HTTP calls giữa services (mTLS encrypted)
   - Service token authentication
   - Kubernetes DNS service discovery

2. **Database Connections**:
   - PostgreSQL: Port 5432 (VNet only)
   - CosmosDB: Port 10255 (Service Endpoint)
   - Redis: Port 6380 (VNet only)

3. **CI/CD Pipeline**:
   - GitHub Actions workflows
   - Docker image builds
   - Security scans (Bandit, Safety, TruffleHog, Checkov, Trivy, OWASP ZAP)

### 3.3 Dependencies Attack Surface

1. **Python Dependencies**:
   - FastAPI, Pydantic, SQLAlchemy, Motor, etc.
   - Vulnerabilities được scan bởi Safety

2. **Container Images**:
   - Python base images
   - Vulnerabilities được scan bởi Trivy

3. **Infrastructure as Code**:
   - Terraform configurations
   - Misconfigurations được scan bởi Checkov

### 3.4 Secrets Attack Surface

1. **Kubernetes Secrets**:
   - JWT_SECRET_KEY
   - Database passwords
   - API keys (Mapbox, VNPay)
   - Service client credentials

2. **GitHub Secrets**:
   - Azure credentials
   - ACR credentials
   - DAST target URL

3. **CI/CD Logs**:
   - Secrets có thể bị expose trong GitHub Actions logs
   - TruffleHog scan để detect

---

## 4. Đánh giá Rủi ro Chi tiết

### 4.1 Critical Risks

| Mối đe dọa | Mức độ | Lý do | Mitigation | Status |
|------------|--------|-------|------------|--------|
| **CosmosDB & Redis public access** | Critical | Cho phép truy cập từ Internet | ✅ VNet Service Endpoints + NSG | ✅ Fixed |
| **JWT Secret Key default value** | Critical | Code có hardcoded secret | ✅ Kubernetes Secrets | ⚠️ Cần verify không có trong code |
| **WebSocket không có authentication** | Critical | Bất kỳ ai cũng có thể connect | ❌ Cần implement JWT auth cho WebSocket | ❌ Open |
| **Payment callback replay attack** | Critical | Có thể replay successful payment | ⚠️ Idempotency check | ⚠️ Cần thêm nonce/timestamp |
| **Secrets trong logs** | Critical | Logs có thể expose secrets | ⚠️ Basic logging | ❌ Cần PII masking |

### 4.2 High Risks

| Mối đe dọa | Mức độ | Lý do | Mitigation | Status |
|------------|--------|-------|------------|--------|
| **Không có rate limiting** | High | DoS dễ dàng | ⚠️ Network policies | ❌ Cần implement rate limiting |
| **Brute force login** | High | Không có account lockout | ❌ Không có | ❌ Open |
| **CORS allow-origin: "*"** | High | CSRF attacks | ⚠️ CORS enabled | ❌ Cần restrict domain |
| **Payment amount tampering** | High | Callback có thể modify amount | ✅ Hash verification | ⚠️ Cần verify với original |
| **Service token reuse** | High | Token có thể bị reuse | ✅ Audience claim | ⚠️ Token expiry 15 phút |
| **Location data privacy** | High | GPS coordinates rò rỉ | ⚠️ Redis không encrypt | ⚠️ Cần encryption at rest |

### 4.3 Medium Risks

| Mối đe dọa | Mức độ | Lý do | Mitigation | Status |
|------------|--------|-------|------------|--------|
| **Secrets không mã hóa at rest** | Medium | Base64 only | ✅ Kubernetes encryption at rest | ✅ Fixed |
| **Thiếu audit logging** | Medium | Không trace được actions | ⚠️ Basic logging | ❌ Cần structured audit logs |
| **Pod chạy quyền root** | Medium | Lateral movement | ✅ Pod Security Standards | ✅ Fixed |
| **Thiếu SAST/SCA/DAST** | Medium | Không phát hiện vuln sớm | ✅ 6 OSS security tools | ✅ Fixed |
| **Database connection pool exhaustion** | Medium | DoS via connection flood | ✅ Connection pooling | ⚠️ Cần monitor |
| **Race condition trong payment** | Medium | IPN và Return URL conflict | ⚠️ Idempotency check | ⚠️ Cần improve |

### 4.4 Low Risks

| Mối đe dọa | Mức độ | Lý do | Mitigation | Status |
|------------|--------|-------|------------|--------|
| **Thiếu cảnh báo bảo mật** | Low | Không phát hiện sự cố | ✅ Azure Monitor alerts | ✅ Fixed |
| **TLS downgrade** | Low | TLS 1.2+ enforced | ✅ TLS 1.2+ minimum | ✅ Fixed |
| **Information disclosure trong errors** | Low | Error messages có thể leak info | ⚠️ Generic error messages | ⚠️ Cần review |

---

## 5. Lộ trình Giảm thiểu

### Phase 1: Foundation (✅ Completed)
- ✅ Bịt lỗ hổng mạng (Service Endpoints + NSG)
- ✅ Mã hóa secrets at rest (Kubernetes encryption)
- ✅ Cập nhật threat model

### Phase 2: Zero Trust (✅ Completed)
- ✅ Áp dụng Linkerd + NetworkPolicy
- ✅ mTLS encryption cho inter-service traffic
- ✅ Pod Security Standards (restricted)

### Phase 3: CI/CD Security (✅ Completed)
- ✅ 6 security tools trong pipeline (Bandit, Safety, TruffleHog, Checkov, Trivy, OWASP ZAP)
- ✅ Security gates và fail-fast rules

### Phase 4: Application Hardening (✅ Completed)
- ✅ Pod Security Standards
- ✅ Resource limits
- ✅ Security contexts (non-root, read-only FS)

### Phase 5: Monitoring (✅ Completed)
- ✅ Azure Monitor alerts (7 alerts)
- ✅ Fluent Bit log aggregation
- ✅ Security runbooks (6 procedures)

### Phase 6: Future Improvements (⚠️ Pending)

**Priority 1 (High):**
1. **Implement WebSocket Authentication**
   - JWT token verification trong WebSocket handshake
   - Verify driver_id trong connection
   - Trip room access control

2. **Rate Limiting**
   - NGINX rate limiting annotations
   - Per-user rate limits
   - Per-IP rate limits

3. **CORS Restriction**
   - Restrict CORS chỉ cho mobile app domain
   - Remove wildcard "*"

4. **Payment Security Enhancements**
   - Nonce/timestamp để prevent replay attacks
   - Amount verification với original transaction
   - IP whitelist cho VNPay callbacks

**Priority 2 (Medium):**
5. **Audit Logging**
   - Structured audit logs với request ID
   - Immutable audit trail
   - PII masking trong logs

6. **Authentication Improvements**
   - Refresh token mechanism
   - Account lockout sau failed attempts
   - Shorter token expiry cho sensitive operations

7. **Input Validation**
   - Location coordinate validation
   - Amount range validation
   - Trip ownership verification

**Priority 3 (Low):**
8. **Monitoring Enhancements**
   - Custom metrics cho security events
   - Anomaly detection
   - Real-time alerting

---

## 6. Compliance Mapping

### OWASP Top 10 (2021)

| OWASP Risk | Coverage | Implementation |
|------------|----------|----------------|
| **A01: Broken Access Control** | ✅ | Network policies, service tokens, JWT validation |
| **A02: Cryptographic Failures** | ✅ | TLS 1.2+, mTLS, bcrypt for passwords, secrets encryption |
| **A03: Injection** | ✅ | SQLAlchemy ORM, Pydantic validation, parameterized queries |
| **A04: Insecure Design** | ✅ | Zero Trust architecture, defense-in-depth |
| **A05: Security Misconfiguration** | ✅ | Pod Security Standards, IaC scanning (Checkov) |
| **A06: Vulnerable Components** | ✅ | SCA scanning (Safety, Trivy) |
| **A07: Identification/Authentication Failures** | ⚠️ | JWT implementation, nhưng thiếu rate limiting, account lockout |
| **A08: Software and Data Integrity Failures** | ✅ | Hash verification (VNPay), secure logging |
| **A09: Security Logging and Monitoring Failures** | ⚠️ | Basic logging, thiếu structured audit logs |
| **A10: Server-Side Request Forgery (SSRF)** | ✅ | Network policies restrict outbound traffic |

---

## 7. Threat Model Review Process

### 7.1 Review Schedule
- **Quarterly**: Full threat model review
- **After major changes**: Architecture changes, new services, new integrations
- **After security incidents**: Post-incident review

### 7.2 Review Checklist
- [ ] DFD có phản ánh đúng kiến trúc hiện tại?
- [ ] STRIDE analysis có cover tất cả components?
- [ ] Risk assessment có cập nhật mitigation status?
- [ ] Có mối đe dọa mới nào không?
- [ ] Mitigation strategies có hiệu quả?
- [ ] Compliance mapping có đầy đủ?

### 7.3 Update History
- **v2.0 (2025-01-15)**: Comprehensive update với code review, bổ sung WebSocket security, payment vulnerabilities, CORS risks
- **v1.0 (2024-11-28)**: Initial threat model

---

**Tài liệu này phải được cập nhật khi kiến trúc thay đổi và được xem xét ở mỗi vòng đánh giá bảo mật hàng quý.**
