# ADR-004: Chọn Microservices Architecture

**Ngày:** 2025-10-10
**Trạng thái:** Accepted
**Người quyết định:** UIT-GO Development Team

## Context (Bối cảnh)

UIT-GO là ứng dụng gọi xe với các yêu cầu:
- Nhiều bounded contexts khác nhau: User, Driver, Trip, Location, Payment
- Team 5 người, cần phát triển parallel
- Scale requirements khác nhau cho từng service
- Công nghệ/database khác nhau cho từng domain
- Cần deploy independent (không muốn deploy lại toàn bộ khi sửa 1 feature)

## Decision (Quyết định)

Chọn **Microservices Architecture** với 5 services:
1. **UserService**: Quản lý users, authentication
2. **DriverService**: Quản lý driver profiles, availability
3. **TripService**: Quản lý trip lifecycle, matching
4. **LocationService**: Real-time location tracking, WebSocket
5. **PaymentService**: Xử lý thanh toán, VNPay integration

## Alternatives Considered (Các phương án đã xem xét)

### 1. Monolithic Architecture
**Ưu điểm:**
- Đơn giản để start
- Deployment dễ (1 codebase)
- Transactions dễ (single database)
- Debugging dễ hơn

**Nhược điểm:**
- Khó scale independently (phải scale toàn bộ app)
- Khó deploy independent (sửa 1 feature phải deploy lại hết)
- Tech stack bị lock (phải dùng 1 ngôn ngữ, 1 framework)
- Database coupling (khó dùng PostgreSQL + MongoDB + Redis)
- Team conflict (nhiều người sửa cùng 1 codebase)
- Slow CI/CD (test + build toàn bộ app)

### 2. Modular Monolith
**Ưu điểm:**
- Tách modules rõ ràng nhưng vẫn 1 app
- Dễ migrate sang microservices sau
- Đơn giản hơn microservices

**Nhược điểm:**
- Vẫn không scale independently
- Vẫn deploy toàn bộ
- Vẫn bị lock tech stack
- Modules có thể bị coupling lại

### 3. Serverless (AWS Lambda, Azure Functions)
**Ưu điểm:**
- Auto-scaling tuyệt vời
- Pay-per-use
- Không quản lý infrastructure

**Nhược điểm:**
- Cold start latency
- Vendor lock-in
- WebSocket support phức tạp
- Team chưa có exp với serverless
- Debugging khó

## Consequences (Hậu quả/Trade-offs)

### Ưu điểm:
- ✅ **Independent scaling**: LocationService scale riêng (write-heavy), TripService scale riêng
- ✅ **Independent deployment**: Sửa UserService không ảnh hưởng TripService
- ✅ **Technology diversity**:
  - UserService → PostgreSQL
  - TripService → Cosmos DB (MongoDB)
  - LocationService → Redis
- ✅ **Team autonomy**: Mỗi người phụ trách 1 service, develop parallel
- ✅ **Fault isolation**: LocationService crash không làm UserService die
- ✅ **Faster CI/CD**: Mỗi service có pipeline riêng, build nhanh hơn
- ✅ **Domain-driven design**: Mỗi service = 1 bounded context rõ ràng

### Nhược điểm:
- ❌ **Complexity tăng**:
  - Cần API Gateway / Ingress
  - Service discovery
  - Distributed tracing
  - Centralized logging
- ❌ **Network latency**: Inter-service calls qua HTTP (slower than in-process)
- ❌ **Data consistency**: Không có distributed transactions, eventual consistency
- ❌ **Testing phức tạp**: Cần integration tests, contract testing
- ❌ **Deployment overhead**: Cần Kubernetes, CI/CD cho 5 services
- ❌ **More resources**: 5 containers thay vì 1 monolith

### Risks:
- **Risk**: Service dependencies tạo coupling
  - **Mitigation**:
    - Minimize sync calls
    - Use events/message queue (future)
    - Implement circuit breakers

- **Risk**: Distributed transactions (trip + payment)
  - **Mitigation**:
    - Saga pattern
    - Compensating transactions
    - Idempotent APIs

- **Risk**: Network failures giữa services
  - **Mitigation**:
    - Retry logic
    - Timeouts
    - Fallback responses
    - Circuit breakers

- **Risk**: Monitoring/debugging phức tạp
  - **Mitigation**:
    - Centralized logging (Azure Monitor)
    - Distributed tracing (Application Insights)
    - Health check endpoints
    - Correlation IDs

## Service Boundaries

### UserService
- **Responsibility**: User registration, authentication, JWT
- **Database**: PostgreSQL
- **Why separate**: Core domain, strict ACID requirements

### DriverService
- **Responsibility**: Driver profiles, status, wallet
- **Database**: Cosmos DB (MongoDB)
- **Why separate**: Different scale, flexible schema

### TripService
- **Responsibility**: Trip lifecycle, matching, fare calculation
- **Database**: Cosmos DB (MongoDB)
- **Why separate**: Complex domain logic, high write throughput

### LocationService
- **Responsibility**: Real-time location, WebSocket, nearby search
- **Database**: Redis
- **Why separate**: Extreme low latency, different tech stack (WebSocket)

### PaymentService
- **Responsibility**: Payment processing, VNPay, refunds
- **Database**: Cosmos DB (MongoDB)
- **Why separate**: Payment domain, external integration, PCI compliance

## Inter-Service Communication

```
TripService → DriverService: Get driver info (HTTP/REST)
TripService → PaymentService: Process payment (HTTP/REST)
TripService → LocationService: Notify drivers (HTTP/REST)
UserService → DriverService: NOT ALLOWED (should go through API Gateway)
```

**Rules:**
- Services communicate via REST APIs
- Use service names for DNS (Kubernetes Service Discovery)
- Implement timeout (10s max)
- Implement retry (3 times with exponential backoff)

## Implementation Notes

- Each service có Dockerfile riêng
- Each service có CI/CD pipeline riêng
- Shared libraries: schemas, auth utils (via pip package)
- API versioning: `/v1/`, `/v2/`
- Health check: `/health` endpoint

## Related Decisions

- ADR-005: Kubernetes/AKS cho deployment
- ADR-007: NGINX Ingress cho API Gateway
- ADR-001, 002, 003: Database choices per service

## Future Considerations

- Có thể thêm **API Gateway service** (Kong, Traefik) cho advanced routing
- Có thể thêm **Message Queue** (RabbitMQ, Kafka) cho async events
- Có thể thêm **Service Mesh** (Istio) cho advanced traffic management
