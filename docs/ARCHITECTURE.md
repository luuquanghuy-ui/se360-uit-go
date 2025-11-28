# UIT-Go: System Architecture

Tài liệu này mô tả kiến trúc microservices của UIT-Go, cách các service giao tiếp với nhau, và các luồng nghiệp vụ chính.

## 📋 Table of Contents

- [System Overview](#system-overview)
- [Sơ đồ kiến trúc tổng quan](#sơ-đồ-kiến-trúc-tổng-quan)
- [Module chuyên sâu](#module-chuyên-sâu)
  - [Trip Orchestration Module](#trip-orchestration-module)
  - [Location & Notification Module](#location--notification-module)
- [Microservices Architecture](#microservices-architecture)
- [Sequence Diagrams](#sequence-diagrams)
- [Inter-Service Communication](#inter-service-communication)
- [Authentication & Security](#authentication--security)
- [Database Design](#database-design)
- [WebSocket Architecture](#websocket-architecture)
- [External Integrations](#external-integrations)
- [Environment Configuration](#environment-configuration)

---

## System Overview

UIT-Go là nền tảng gọi xe được xây dựng với **microservices architecture** sử dụng FastAPI và Python. Hệ thống bao gồm 5 services độc lập, mỗi service có database riêng và giao tiếp qua HTTP REST APIs và WebSocket.

### Core Design Principles

1. **Database per Service**: Mỗi service có isolated database (PostgreSQL hoặc MongoDB)
2. **Service Independence**: Services có thể deploy và scale độc lập
3. **Async Communication**: WebSocket cho real-time features, HTTP cho synchronous operations
4. **Centralized Authentication**: UserService cấp JWT cho cả user và service-to-service auth
5. **Redis for Geospatial**: LocationService sử dụng Redis GEO indexes cho nearby driver queries

---

## Sơ đồ kiến trúc tổng quan

```mermaid
flowchart TB
    subgraph Clients["Client Applications"]
        PA[Passenger App]
        DA[Driver App]
    end

    subgraph Edge["Azure Edge"]
        ALB[Azure Load Balancer<br/>Public IP]
        NGINX[NGINX Ingress Controller<br/>Path-based routing + TLS]
    end

    subgraph Mesh["AKS Cluster + Linkerd"]
        US[UserService<br/>:8000<br/>PostgreSQL]
        TS[TripService<br/>:8002<br/>CosmosDB]
        DS[DriverService<br/>:8003<br/>CosmosDB]
        LS[LocationService<br/>:8001<br/>Redis]
        PS[PaymentService<br/>:8004<br/>CosmosDB]
    end

    subgraph Data["Data Layer (Private VNet)"]
        PG[(Azure PostgreSQL Flexible Server)]
        COSMOS[(Azure CosmosDB Mongo API)]
        REDIS[(Azure Redis Cache GEO)]
    end

    subgraph Ext["External Providers"]
        MAPBOX[Mapbox Directions API]
        VNPAY[VNPay Gateway]
    end

    PA -->|HTTPS / WS| ALB --> NGINX
    DA -->|HTTPS / WS| ALB

    NGINX -->|/api/users| US
    NGINX -->|/api/trips| TS
    NGINX -->|/api/drivers| DS
    NGINX -->|/api/locations & /ws| LS
    NGINX -->|/api/payments| PS

    US --> PG
    TS --> COSMOS
    DS --> COSMOS
    PS --> COSMOS
    LS --> REDIS

    TS --> MAPBOX
    PS --> VNPAY

    TS -. mTLS .-> US
    TS -. mTLS .-> DS
    TS -. mTLS .-> LS
    TS -. mTLS .-> PS
```

**Highlights**
- Single entry point thông qua NGINX Ingress (LoadBalancer) + Azure Firewall/NSG.
- Linkerd cung cấp mTLS, observability và policy enforcement cho mọi traffic nội bộ.
- Dữ liệu lưu tách biệt theo service, kết nối qua Service Endpoint hoặc private VNet.
- External integrations (Mapbox, VNPay) chỉ được gọi từ service tương ứng với outbound egress control.

---

## Module chuyên sâu

### Trip Orchestration Module

```mermaid
flowchart LR
    subgraph TripCore["TripService Core"]
        API[REST API Layer]
        FLOW[Trip Orchestrator]
        STORE[(Trips Collection)]
    end

    API --> FLOW
    FLOW --> STORE

    FLOW -->|Service token| US[UserService]
    FLOW -->|Driver lookup| DS[DriverService]
    FLOW -->|Nearby drivers| LS[LocationService]
    FLOW -->|Process payment| PS[PaymentService]
    FLOW -->|Route & ETA| MAPBOX[Mapbox API]

    DS -->|Internal driver info| FLOW
    LS -->|WebSocket notify| NOTIFY[(Passengers & Drivers)]
    PS -->|Wallet / VNPay| FLOW

    classDef core fill:#fff2cc,stroke:#f57f17,stroke-width:2px;
    classDef svc fill:#e0f7fa,stroke:#006064,stroke-width:1.5px;
    classDef ext fill:#ffe0e0,stroke:#c62828,stroke-width:1.5px;

    class API,FLOW,STORE core
    class US,DS,LS,PS svc
    class MAPBOX ext
```

**Luồng chính**
1. Passenger gửi yêu cầu chuyến đi → API layer → Trip Orchestrator.
2. Trip Orchestrator gọi Mapbox để tính toán quãng đường/giá dự kiến.
3. Trip Orchestrator phát service token từ UserService để truy cập endpoint nội bộ DriverService.
4. Trip Orchestrator tìm tài xế gần nhất qua LocationService, gửi thông báo WebSocket.
5. Khi tài xế nhận chuyến, Trip Orchestrator xử lý thanh toán qua PaymentService (wallet/VNPay) và cập nhật trạng thái chuyến.

### Location & Notification Module

```mermaid
sequenceDiagram
    autonumber
    participant Driver as Driver App
    participant WS as LocationService WS Gateway
    participant Redis as Redis GEO Store
    participant Passenger as Passenger App
    participant TripSvc as TripService

    Driver->>WS: Connect ws://.../driver/{id}
    WS->>Redis: SADD connected_drivers
    loop Every 5-10s
        Driver->>WS: {"lat":10.82,"lng":106.62}
        WS->>Redis: GEOADD drivers:locations
    end
    TripSvc->>WS: POST /notify/drivers {trip_offer}
    WS-->>Driver: WebSocket push TRIP_OFFER

    note over WS: Trip room
    Passenger->>WS: Connect ws://.../trip/{trip_id}/passenger
    Driver->>WS: Connect ws://.../trip/{trip_id}/driver
    loop During trip
        Driver->>WS: {"type":"location",...}
        WS-->>Passenger: Broadcast driver location
        TripSvc->>WS: {"type":"status_update"}
        WS-->>Driver: Update trip status
    end
```

**Thành phần chính**
- **WS Gateway**: FastAPI WebSocket manager quản lý kết nối và phòng (trip room).
- **Redis GEO**: Lưu vị trí, trạng thái online và publish events để TripService truy vấn nhanh.
- **Notifications**: TripService dùng HTTP call để bắn thông báo (trip offer, driver assigned, trip completed) và LocationService phân phối qua WS.

---

## Microservices Architecture

### Service Overview

| Service | Database | Port | Responsibility |
|---------|----------|------|----------------|
| **UserService** | PostgreSQL | 8000 | User authentication, JWT issuance (user + service tokens), user profiles |
| **TripService** | MongoDB | 8002 | Trip lifecycle, matching logic, orchestrates other services, Mapbox integration |
| **DriverService** | MongoDB | 8003 | Driver profiles, driver wallet, internal driver info endpoints |
| **LocationService** | Redis | 8001 | Real-time location tracking (Redis GEO), WebSocket connections, notifications |
| **PaymentService** | MongoDB | 8004 | User wallet, VNPay integration, payment processing & callbacks |

### Network Configuration

**Local Development (Docker Compose):**
- External access: `http://localhost:800X`
- Internal communication: `http://servicename:8000` (Docker network DNS)

**Production (Kubernetes - Ingress API Gateway Pattern):**
- External access: `http://<INGRESS-EXTERNAL-IP>` → NGINX Ingress Controller (LoadBalancer)
- Ingress routes traffic based on path:
  - `/api/users/*` → UserService (ClusterIP)
  - `/api/drivers/*` → DriverService (ClusterIP)
  - `/api/trips/*` → TripService (ClusterIP)
  - `/api/locations/*` → LocationService (ClusterIP)
  - `/api/payments/*` → PaymentService (ClusterIP)
  - `/ws` → LocationService WebSocket (ClusterIP)
- Internal service-to-service: `http://servicename:8000` (Kubernetes DNS)
- All services use ClusterIP (internal only, không exposed trực tiếp)

---

## Component Diagram

```mermaid
flowchart TB
    subgraph "Client Applications"
        PA[Passenger App]
        DA[Driver App]
    end

    subgraph "External Services"
        MAPBOX[Mapbox API<br/>Directions & Geocoding]
        VNPAY[VNPay<br/>Payment Gateway]
    end

    subgraph "Azure Load Balancer"
        LB[Azure Load Balancer<br/>Public IP]
    end

    subgraph "Kubernetes Cluster - Ingress Layer"
        INGRESS[NGINX Ingress Controller<br/>API Gateway<br/>Type: LoadBalancer]
    end

    subgraph "Kubernetes Cluster - Service Layer"
        US[UserService<br/>:8000<br/>ClusterIP]
        TS[TripService<br/>:8000<br/>ClusterIP]
        DS[DriverService<br/>:8000<br/>ClusterIP]
        LS[LocationService<br/>:8000<br/>ClusterIP]
        PS[PaymentService<br/>:8000<br/>ClusterIP]
    end

    subgraph "Data Layer"
        POSTGRES[(PostgreSQL<br/>uitgo_users)]
        MONGO_TRIP[(CosmosDB MongoDB API<br/>uitgo_trips)]
        MONGO_DRIVER[(CosmosDB MongoDB API<br/>uitgo_drivers)]
        MONGO_PAYMENT[(CosmosDB MongoDB API<br/>uitgo_payments)]
        REDIS[(Azure Redis Cache<br/>Geospatial + Cache)]
    end

    %% Client to Ingress
    PA -->|HTTP/WS| LB
    DA -->|HTTP/WS| LB
    LB --> INGRESS

    %% Ingress routing (API Gateway pattern)
    INGRESS -->|/api/users/*| US
    INGRESS -->|/api/trips/*| TS
    INGRESS -->|/api/drivers/*| DS
    INGRESS -->|/api/locations/*| LS
    INGRESS -->|/api/payments/*| PS
    INGRESS -->|/ws| LS

    %% Service-to-service communication (internal)
    TS -.->|Service Token| US
    TS -.->|Get Driver Info| DS
    TS -.->|Find Nearby| LS
    TS -.->|Notify| LS
    TS -.->|Process Payment| PS
    TS -->|Routing API| MAPBOX

    PS -->|Payment URL| VNPAY
    VNPAY -->|Callback via Ingress| INGRESS
    INGRESS -->|/api/payments/callback| PS

    %% Database connections
    US --- POSTGRES
    TS --- MONGO_TRIP
    DS --- MONGO_DRIVER
    PS --- MONGO_PAYMENT
    LS --- REDIS

    %% Styling
    classDef clientStyle fill:#e1f5ff,stroke:#01579b,stroke-width:2px
    classDef ingressStyle fill:#fce4ec,stroke:#c2185b,stroke-width:3px
    classDef serviceStyle fill:#fff9c4,stroke:#f57f17,stroke-width:2px
    classDef dbStyle fill:#c8e6c9,stroke:#2e7d32,stroke-width:2px
    classDef externalStyle fill:#ffccbc,stroke:#bf360c,stroke-width:2px

    class PA,DA clientStyle
    class INGRESS ingressStyle
    class US,TS,DS,LS,PS serviceStyle
    class POSTGRES,MONGO_TRIP,MONGO_DRIVER,MONGO_PAYMENT,REDIS dbStyle
    class MAPBOX,VNPAY,LB externalStyle
```

---

## Sequence Diagrams

### 1. Trip Creation Flow

```mermaid
sequenceDiagram
    autonumber
    participant P as Passenger App
    participant TS as TripService
    participant MAPBOX as Mapbox API
    participant LS as LocationService
    participant REDIS as Redis
    participant DA as Driver App

    P->>TS: POST /trip-requests/complete<br/>{pickup, dropoff, vehicle_type, payment_method}

    Note over TS: Calculate route & fare
    TS->>MAPBOX: GET /directions/v5<br/>Query route
    MAPBOX-->>TS: {distance, duration, geometry}

    Note over TS: Save trip to MongoDB
    TS->>TS: Create Trip document<br/>status: PENDING

    Note over TS: Find available drivers
    TS->>LS: GET /drivers/nearby<br/>?lat=X&lng=Y&radius=5
    LS->>REDIS: GEORADIUS drivers:locations
    REDIS-->>LS: [driver_ids]
    LS-->>TS: Available drivers

    Note over TS: Broadcast trip offer
    TS->>LS: POST /notify/drivers<br/>{driver_ids, TRIP_OFFER}
    LS-->>DA: WebSocket push TRIP_OFFER<br/>{trip_id, pickup, fare, ETA}

    TS-->>P: 201 Created<br/>{trip_id, status: PENDING}
```

### 2. Driver Assignment Flow

```mermaid
sequenceDiagram
    autonumber
    participant DA as Driver App
    participant TS as TripService
    participant US as UserService
    participant DS as DriverService
    participant LS as LocationService
    participant PA as Passenger App

    DA->>TS: PUT /trips/{id}/assign-driver<br/>{driver_id}

    Note over TS: Authenticate with DriverService
    TS->>US: POST /auth/token<br/>{client_id: TRIPSVC_CLIENT_ID, client_secret}
    US-->>TS: {access_token: SERVICE_JWT, type: "service"}

    Note over TS: Fetch driver details
    TS->>DS: GET /drivers/internal/{driver_id}<br/>Authorization: Bearer SERVICE_JWT
    DS->>DS: Validate service token<br/>(check JWT type=service)
    DS-->>TS: {driver_name, phone, vehicle_info, rating}

    Note over TS: Update trip status
    TS->>TS: Update MongoDB<br/>status: ACCEPTED, driver_id

    Note over TS: Notify passenger
    TS->>LS: POST /notify/trip/{id}/passenger<br/>{type: DRIVER_ASSIGNED, driver_info}
    LS-->>PA: WebSocket push<br/>DRIVER_ASSIGNED

    TS-->>DA: 200 OK<br/>{status: ACCEPTED}
```

### 3. Payment Flow (E-Wallet via VNPay)

```mermaid
sequenceDiagram
    autonumber
    participant PA as Passenger App
    participant TS as TripService
    participant PS as PaymentService
    participant VNPAY as VNPay Gateway
    participant MONGO as MongoDB

    Note over PA: Trip completed
    PA->>TS: POST /trips/{id}/complete<br/>{actual_fare: 50000}

    alt payment_method == "E-Wallet"
        TS->>PS: POST /process-payment<br/>{trip_id, user_id, driver_id, amount: 50000}

        Note over PS: Check wallet balance
        PS->>MONGO: Find user_wallet

        alt balance < amount
            Note over PS: Insufficient balance - create VNPay URL
            PS->>PS: Generate VNPay parameters<br/>+ HMAC-SHA512 hash
            PS-->>TS: {payUrl: "https://sandbox.vnpayment.vn/...", txnRef}
            TS-->>PA: 200 OK {payUrl}

            PA->>VNPAY: Redirect to payUrl<br/>(User completes payment)
            VNPAY-->>PS: GET /payment-return<br/>?vnp_TxnRef&vnp_ResponseCode=00&vnp_SecureHash

            Note over PS: Verify hash & update transaction
            PS->>MONGO: Update transaction<br/>status: SUCCESS
            PS->>MONGO: Credit user wallet<br/>+ Debit driver wallet
            PS-->>VNPAY: 200 OK

        else balance >= amount
            Note over PS: Direct wallet deduction
            PS->>MONGO: Debit user wallet<br/>Credit driver wallet
            PS-->>TS: {status: "success", transaction_id}
        end

    else payment_method == "Cash"
        Note over TS: No online payment needed
        TS->>TS: Update trip status: COMPLETED
    end

    TS->>MONGO: Update trip<br/>status: COMPLETED, actual_fare
    TS-->>PA: 200 OK {trip_status: COMPLETED}
```

### 4. Real-time Location Tracking (WebSocket)

```mermaid
sequenceDiagram
    autonumber
    participant DA as Driver App
    participant LS as LocationService
    participant REDIS as Redis
    participant PA as Passenger App

    Note over DA: Driver starts shift
    DA->>LS: WS Connect<br/>ws://locationservice/ws/driver/{driver_id}/location
    LS->>REDIS: SADD connected_drivers {driver_id}

    loop Every 5-10 seconds
        DA->>LS: WS message<br/>{lat: 10.8231, lng: 106.6297, timestamp}
        LS->>REDIS: GEOADD drivers:locations<br/>{lng} {lat} driver:{id}
        LS->>REDIS: SET driver:{id}:status "online"
    end

    Note over PA: Passenger monitoring trip
    PA->>LS: WS Connect<br/>ws://locationservice/ws/trip/{trip_id}/passenger
    LS->>LS: Add passenger to trip room

    Note over DA: Driver also joins trip room
    DA->>LS: WS Connect<br/>ws://locationservice/ws/trip/{trip_id}/driver

    loop During trip
        DA->>LS: WS message<br/>{type: "location", lat, lng}
        LS-->>PA: WS broadcast to room<br/>{driver_location: {lat, lng}}

        Note over LS: Status updates also pushed
        LS-->>PA: {type: "status_update", status: "IN_PROGRESS"}
        LS-->>DA: {type: "status_update", status: "IN_PROGRESS"}
    end

    Note over DA: Trip completed, disconnect
    DA->>LS: WS disconnect
    LS->>REDIS: SREM connected_drivers {driver_id}
```

---

## Inter-Service Communication

### 1. HTTP REST APIs (Synchronous)

#### TripService → UserService
```
Endpoint: POST http://userservice:8000/auth/token
Purpose: Lấy service JWT token để authenticate với DriverService
Headers: Content-Type: application/json
Body: {
  "client_id": "TRIPSVC_CLIENT_ID",
  "client_secret": "TRIPSVC_CLIENT_SECRET"
}
Response: {
  "access_token": "eyJhbGc...",
  "token_type": "bearer"
}
```

#### TripService → DriverService
```
Endpoint: GET http://driverservice:8000/drivers/internal/{driver_id}
Purpose: Lấy thông tin chi tiết driver (protected endpoint)
Headers:
  Authorization: Bearer <service_token>
Response: {
  "driver_id": "...",
  "name": "...",
  "phone": "...",
  "vehicle": {...},
  "rating": 4.8
}
```

#### TripService → LocationService
```
# Find nearby drivers
GET http://locationservice:8000/drivers/nearby?lat=10.8231&lng=106.6297&radius=5
Response: {
  "drivers": ["driver_id_1", "driver_id_2", ...]
}

# Notify drivers about trip offer
POST http://locationservice:8000/notify/drivers
Body: {
  "driver_ids": ["driver_1", "driver_2"],
  "message": {
    "type": "TRIP_OFFER",
    "trip_id": "...",
    "pickup": {...},
    "fare": 50000
  }
}

# Notify passenger about driver assignment
POST http://locationservice:8000/notify/trip/{trip_id}/passenger
Body: {
  "type": "DRIVER_ASSIGNED",
  "driver": {...}
}
```

#### TripService → PaymentService
```
POST http://paymentservice:8000/process-payment
Body: {
  "trip_id": "...",
  "user_id": "...",
  "driver_id": "...",
  "amount": 50000,
  "payment_method": "E-Wallet"
}
Response: {
  "status": "success",
  "payUrl": "https://sandbox.vnpayment.vn/..." (if needed),
  "transaction_id": "..."
}
```

#### TripService → Mapbox API
```
GET https://api.mapbox.com/directions/v5/mapbox/driving/{start_lng},{start_lat};{end_lng},{end_lat}
Query params:
  access_token=<MAPBOX_ACCESS_TOKEN>
  geometries=geojson
  steps=true
Response: {
  "routes": [{
    "distance": 5432,  // meters
    "duration": 876,   // seconds
    "geometry": {...}  // GeoJSON LineString
  }]
}
```

### 2. WebSocket (Asynchronous Real-time)

#### Driver Location Updates
```
URL: ws://locationservice:8000/ws/driver/{driver_id}/location
Direction: Bidirectional
Driver → Server: {"lat": 10.8231, "lng": 106.6297, "timestamp": "2025-01-15T10:30:00Z"}
Server → Driver: {"type": "NOTIFICATION", "message": "Trip offer: TRIP123"}
Storage: Redis GEOADD drivers:locations {lng} {lat} driver:{driver_id}
```

#### Trip Room (Passenger & Driver)
```
URL: ws://locationservice:8000/ws/trip/{trip_id}/{user_type}
user_type: "passenger" | "driver"
Direction: Bidirectional, broadcast to all room members

Message Types:
1. Location update (from driver)
   {"type": "location", "lat": 10.8231, "lng": 106.6297}

2. Status update (from either side)
   {"type": "status_update", "status": "IN_PROGRESS"}

3. Trip completed
   {"type": "trip_completed", "final_amount": 50000}
```

---

## Authentication & Security

### 1. User Authentication (JWT)

**Flow:**
1. User calls `POST /auth/login` với username/password
2. UserService validates credentials → PostgreSQL
3. UserService generates JWT token với SECRET_KEY
4. User sử dụng token trong header: `Authorization: Bearer <token>`

**JWT Payload (User Token):**
```json
{
  "sub": "user_id_123",
  "username": "john_doe",
  "type": "user",
  "exp": 1730000000,
  "iat": 1729996400
}
```

**Token Validation:**
- Mỗi service có thể validate JWT nếu có SECRET_KEY
- Token expires sau ACCESS_TOKEN_EXPIRE_MINUTES (default: 30 minutes)

### 2. Service-to-Service Authentication

**Flow:**
1. TripService cần gọi protected endpoint của DriverService
2. TripService gọi UserService `POST /auth/token` với client credentials
3. UserService validates (TRIPSVC_CLIENT_ID, TRIPSVC_CLIENT_SECRET)
4. UserService trả về service JWT với `type: "service"`
5. TripService dùng service token để gọi DriverService

**JWT Payload (Service Token):**
```json
{
  "sub": "tripservice",
  "client_id": "TRIPSVC_CLIENT_ID",
  "type": "service",
  "exp": 1730000000,
  "iat": 1729996400
}
```

**Validation tại DriverService:**
```python
# DriverService validates:
# 1. JWT signature với SECRET_KEY
# 2. Token chưa expired
# 3. payload["type"] == "service"
```

**Security Improvements (Recommended):**
1. ✅ Add `aud` (audience) claim: `"aud": "driverservice"`
2. ✅ DriverService validates aud to prevent token misuse
3. ✅ Implement token refresh mechanism
4. ✅ Use different secrets for user vs service tokens

### 3. Environment Variables (Security)

**MUST be identical:**
```bash
# UserService & DriverService
JWT_SECRET_KEY=your-super-secret-key-minimum-32-characters
```

**TripService credentials:**
```bash
TRIPSVC_CLIENT_ID=tripservice_client_001
TRIPSVC_CLIENT_SECRET=super_secret_trip_key_456
```

---

## Database Design

### PostgreSQL (UserService)

**Database:** `uitgo_users`

**Table: users**
```sql
CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    username VARCHAR(50) UNIQUE NOT NULL,
    email VARCHAR(100) UNIQUE NOT NULL,
    hashed_password VARCHAR(255) NOT NULL,
    full_name VARCHAR(100),
    phone_number VARCHAR(20),
    role VARCHAR(20) DEFAULT 'passenger', -- 'passenger' | 'driver' | 'admin'
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);
```

### MongoDB (TripService)

**Database:** `uitgo_trips`

**Collection: trips**
```json
{
  "_id": ObjectId("..."),
  "trip_id": "TRIP123",
  "passenger_id": "user_001",
  "driver_id": "driver_005",
  "status": "COMPLETED",  // PENDING | ACCEPTED | IN_PROGRESS | COMPLETED | CANCELLED
  "pickup": {
    "lat": 10.8231,
    "lng": 106.6297,
    "address": "123 Nguyen Hue, Q1, HCMC"
  },
  "dropoff": {
    "lat": 10.7769,
    "lng": 106.7009,
    "address": "456 Le Lai, Q1, HCMC"
  },
  "vehicle_type": "car",
  "payment_method": "E-Wallet",
  "fare": {
    "estimated": 50000,
    "actual": 55000,
    "currency": "VND"
  },
  "route": {
    "distance": 5432,  // meters
    "duration": 876,   // seconds
    "geometry": {...}  // GeoJSON
  },
  "created_at": ISODate("2025-01-15T10:00:00Z"),
  "started_at": ISODate("2025-01-15T10:05:00Z"),
  "completed_at": ISODate("2025-01-15T10:20:00Z")
}
```

**Collection: trip_offers**
```json
{
  "_id": ObjectId("..."),
  "trip_id": "TRIP123",
  "driver_id": "driver_005",
  "status": "ACCEPTED",  // PENDING | ACCEPTED | REJECTED | EXPIRED
  "offered_at": ISODate("2025-01-15T10:00:30Z"),
  "responded_at": ISODate("2025-01-15T10:01:15Z")
}
```

### MongoDB (DriverService)

**Database:** `uitgo_drivers`

**Collection: drivers**
```json
{
  "_id": ObjectId("..."),
  "driver_id": "driver_005",
  "user_id": "user_010",  // Links to UserService
  "name": "Nguyen Van A",
  "phone": "+84901234567",
  "license_number": "123456789",
  "vehicle": {
    "type": "car",
    "model": "Toyota Vios",
    "color": "white",
    "plate": "59A-12345"
  },
  "rating": 4.8,
  "total_trips": 150,
  "status": "online",  // online | offline | busy
  "created_at": ISODate("2024-01-01T00:00:00Z")
}
```

**Collection: driver_wallets**
```json
{
  "_id": ObjectId("..."),
  "driver_id": "driver_005",
  "balance": 500000,
  "currency": "VND",
  "updated_at": ISODate("2025-01-15T10:20:00Z")
}
```

### MongoDB (PaymentService)

**Database:** `uitgo_payments`

**Collection: user_wallets**
```json
{
  "_id": ObjectId("..."),
  "user_id": "user_001",
  "balance": 200000,
  "currency": "VND",
  "updated_at": ISODate("2025-01-15T10:00:00Z")
}
```

**Collection: transactions**
```json
{
  "_id": ObjectId("..."),
  "transaction_id": "TXN20250115100001",
  "trip_id": "TRIP123",
  "user_id": "user_001",
  "driver_id": "driver_005",
  "type": "TRIP_PAYMENT",  // TRIP_PAYMENT | WALLET_TOPUP | WITHDRAWAL
  "amount": 55000,
  "payment_method": "E-Wallet",
  "status": "SUCCESS",  // PENDING | SUCCESS | FAILED
  "vnpay": {
    "txnRef": "VNP20250115...",
    "responseCode": "00",
    "secureHash": "..."
  },
  "created_at": ISODate("2025-01-15T10:20:00Z")
}
```

### Redis (LocationService)

**Key Structures:**

```redis
# Geospatial index (driver locations)
GEOADD drivers:locations 106.6297 10.8231 driver:driver_005
GEOADD drivers:locations 106.7009 10.7769 driver:driver_012

# Query nearby drivers (5km radius)
GEORADIUS drivers:locations 106.6297 10.8231 5 km WITHDIST

# Driver status
SET driver:driver_005:status "online" EX 300  # expires in 5 minutes

# Connected drivers set
SADD connected_drivers driver:driver_005
SISMEMBER connected_drivers driver:driver_005
SREM connected_drivers driver:driver_005

# WebSocket connection tracking
SET ws:driver:driver_005:connection_id "conn_abc123" EX 3600
```

---

## WebSocket Architecture

### LocationService WebSocket Manager

**Implementation Pattern:**
```python
class ConnectionManager:
    def __init__(self):
        # Track active WebSocket connections
        self.active_connections: Dict[str, WebSocket] = {}
        # Track trip rooms (trip_id -> {passenger: ws, driver: ws})
        self.trip_rooms: Dict[str, Dict[str, WebSocket]] = {}
```

### Endpoints

#### 1. Driver Location Stream
```
ws://locationservice:8000/ws/driver/{driver_id}/location
```

**Purpose:**
- Driver app sends GPS updates every 5-10 seconds
- Server stores in Redis GEO index
- Server can push notifications to driver

**Message Flow:**
```
Driver → Server: {"lat": 10.8231, "lng": 106.6297, "timestamp": "..."}
Server → Redis: GEOADD drivers:locations 106.6297 10.8231 driver:{id}
Server → Driver: {"type": "TRIP_OFFER", "trip_id": "TRIP123", ...}
```

**Connection Lifecycle:**
```
1. Driver connects → SADD connected_drivers {driver_id}
2. Driver sends location → Store in Redis GEO
3. Driver disconnects → SREM connected_drivers {driver_id}
4. Heartbeat timeout (5min) → Auto disconnect & cleanup
```

#### 2. Trip Room (Passenger & Driver)
```
ws://locationservice:8000/ws/trip/{trip_id}/passenger
ws://locationservice:8000/ws/trip/{trip_id}/driver
```

**Purpose:**
- Real-time communication during trip
- Broadcast driver location to passenger
- Share status updates bidirectionally

**Message Types:**
```python
# Location update (driver → passenger)
{
  "type": "location",
  "lat": 10.8231,
  "lng": 106.6297,
  "heading": 180,  # degrees
  "speed": 35      # km/h
}

# Status update (either side)
{
  "type": "status_update",
  "status": "IN_PROGRESS",
  "timestamp": "2025-01-15T10:10:00Z"
}

# Trip completed (system → both)
{
  "type": "trip_completed",
  "final_amount": 55000,
  "distance": 5.4,  # km
  "duration": 876   # seconds
}
```

**Room Management:**
```python
# Add user to room
trip_rooms[trip_id][user_type] = websocket

# Broadcast to room (except sender)
for user_type, ws in trip_rooms[trip_id].items():
    if ws != sender:
        await ws.send_json(message)

# Cleanup on disconnect
del trip_rooms[trip_id][user_type]
if not trip_rooms[trip_id]:  # Room empty
    del trip_rooms[trip_id]
```

---

## External Integrations

### 1. Mapbox API

**Service:** TripService

**Use Cases:**
1. Calculate route between pickup and dropoff
2. Estimate distance and duration for fare calculation
3. Get route geometry for map display

**Endpoint:**
```
GET https://api.mapbox.com/directions/v5/mapbox/driving/{coordinates}
```

**Request Example:**
```
GET https://api.mapbox.com/directions/v5/mapbox/driving/106.6297,10.8231;106.7009,10.7769
  ?access_token=pk.eyJ...
  &geometries=geojson
  &steps=true
  &overview=full
```

**Response:**
```json
{
  "routes": [
    {
      "distance": 5432,  // meters
      "duration": 876,   // seconds
      "geometry": {
        "type": "LineString",
        "coordinates": [
          [106.6297, 10.8231],
          [106.6350, 10.8200],
          ...
          [106.7009, 10.7769]
        ]
      },
      "legs": [...]
    }
  ]
}
```

**Environment Variable:**
```bash
MAPBOX_ACCESS_TOKEN=pk.eyJ1Ijoib2F0aHR1eSIsImEiOiJjbTYza2YwOGEwOXhqMmxzN3E5MWdqNnFpIn0.ZVv_6E3gLpW2kNhfhJ0bqg
```

### 2. VNPay Payment Gateway

**Service:** PaymentService

**Use Cases:**
1. Create payment URL for top-up
2. Receive payment callback
3. Verify transaction authenticity

**Flow:**

**Step 1: Generate Payment URL**
```python
# PaymentService generates URL
params = {
    "vnp_Version": "2.1.0",
    "vnp_Command": "pay",
    "vnp_TmnCode": VNP_TMN_CODE,
    "vnp_Amount": 5000000,  # 50,000 VND * 100
    "vnp_CurrCode": "VND",
    "vnp_TxnRef": unique_txn_ref,
    "vnp_OrderInfo": f"Payment for trip {trip_id}",
    "vnp_OrderType": "other",
    "vnp_Locale": "vn",
    "vnp_ReturnUrl": f"{BASE_URL}/payment-return",
    "vnp_IpAddr": client_ip,
    "vnp_CreateDate": datetime.now().strftime("%Y%m%d%H%M%S")
}

# Generate HMAC SHA512 hash
query_string = "&".join([f"{k}={v}" for k, v in sorted(params.items())])
vnp_SecureHash = hmac.new(
    VNP_HASH_SECRET.encode(),
    query_string.encode(),
    hashlib.sha512
).hexdigest()

params["vnp_SecureHash"] = vnp_SecureHash
payment_url = f"https://sandbox.vnpayment.vn/paymentv2/vpcpay.html?{urlencode(params)}"
```

**Step 2: User Redirects to VNPay**
```
User clicks payUrl → VNPay payment page → User completes payment
```

**Step 3: VNPay Callback**
```
GET {BASE_URL}/payment-return
  ?vnp_TxnRef=VNP20250115...
  &vnp_Amount=5000000
  &vnp_ResponseCode=00
  &vnp_TransactionNo=14379497
  &vnp_SecureHash=abc123...
```

**Step 4: Verify & Process**
```python
# PaymentService verifies hash
received_hash = request.query_params["vnp_SecureHash"]
params_to_verify = {k: v for k, v in request.query_params.items() if k != "vnp_SecureHash"}
query_string = "&".join([f"{k}={v}" for k, v in sorted(params_to_verify.items())])
computed_hash = hmac.new(VNP_HASH_SECRET.encode(), query_string.encode(), hashlib.sha512).hexdigest()

if received_hash == computed_hash and response_code == "00":
    # Payment successful
    update_wallet(user_id, amount)
    update_transaction_status(txn_ref, "SUCCESS")
```

**VNPay Response Codes:**
- `00`: Success
- `07`: Suspicious transaction (blocked by VNPay)
- `09`: Card not registered for online payment
- `10`: Invalid authentication
- `24`: Transaction canceled by user

**Environment Variables:**
```bash
VNP_TMN_CODE=YOUR_MERCHANT_CODE
VNP_HASH_SECRET=YOUR_SECRET_KEY
VNP_URL=https://sandbox.vnpayment.vn/paymentv2/vpcpay.html
BASE_URL=https://your-public-domain.com  # MUST be HTTPS
```

**Important Notes:**
1. ⚠️ BASE_URL phải là public HTTPS URL (không thể localhost)
2. ⚠️ Development: Dùng ngrok để expose PaymentService
3. ⚠️ Production: Dùng domain thật với SSL certificate
4. ⚠️ VNPay sandbox chỉ hỗ trợ test cards (xem docs VNPay)

---

## Environment Configuration

### Critical Variables (Must Match Across Services)

```bash
# UserService & DriverService - MUST BE IDENTICAL
JWT_SECRET_KEY=your-super-secret-key-minimum-32-characters
ACCESS_TOKEN_EXPIRE_MINUTES=30
```

### Service-Specific Configuration

#### UserService (PostgreSQL)
```bash
POSTGRES_HOST=uitgo-postgres
POSTGRES_PORT=5432
POSTGRES_DB=uitgo_users
POSTGRES_USER=uitgo_app
POSTGRES_PASSWORD=<strong_password>
JWT_SECRET_KEY=your-super-secret-key-minimum-32-characters
TRIPSVC_CLIENT_ID=tripservice_client_001
TRIPSVC_CLIENT_SECRET=super_secret_trip_key_456
```

#### TripService
```bash
MONGODB_URL=mongodb://admin:secret@mongodb:27017/uitgo_trips?authSource=admin
LOCATION_SERVICE_URL=http://locationservice:8000
DRIVER_SERVICE_URL=http://driverservice:8000
PAYMENT_SERVICE_URL=http://paymentservice:8000
USER_SERVICE_URL=http://userservice:8000
MAPBOX_ACCESS_TOKEN=pk.eyJ...
MY_CLIENT_ID=tripservice_client_001
MY_CLIENT_SECRET=super_secret_trip_key_456
```

#### DriverService
```bash
MONGODB_URL=mongodb://admin:secret@mongodb:27017/uitgo_drivers?authSource=admin
SECRET_KEY=your-super-secret-key-minimum-32-characters  # SAME as UserService
LOCATION_SERVICE_URL=http://locationservice:8000
PAYMENT_SERVICE_URL=http://paymentservice:8000
```

#### LocationService
```bash
REDIS_URL=redis://redis:6379
REDIS_HOST=redis
REDIS_PORT=6379
```

#### PaymentService
```bash
MONGODB_URL=mongodb://admin:secret@mongodb:27017/uitgo_payments?authSource=admin
DRIVER_SERVICE_URL=http://driverservice:8000
VNP_TMN_CODE=YOUR_MERCHANT_CODE
VNP_HASH_SECRET=YOUR_SECRET_KEY
VNP_URL=https://sandbox.vnpayment.vn/paymentv2/vpcpay.html
BASE_URL=https://your-ngrok-url.ngrok.io  # Public HTTPS URL
```

### Network Configuration

**Docker Compose (Development):**
```yaml
networks:
  uitgo-net:
    driver: bridge

# Services communicate via: http://servicename:8000
```

**Kubernetes (Production):**
```yaml
# Services communicate via: http://servicename:8000
# Kubernetes DNS automatically resolves service names
```

---

## Performance Considerations

### 1. Database Optimization

**Redis (LocationService):**
- ✅ Redis GEO indexes for O(log N) nearby queries
- ✅ TTL on driver status keys (auto-cleanup inactive drivers)
- 🔄 Consider Redis Cluster for horizontal scaling

**MongoDB (Trip/Driver/Payment):**
- ✅ Index on trip_id, driver_id, user_id
- ✅ Index on status for filtering pending trips
- 🔄 Consider sharding by user_id for horizontal scaling

**PostgreSQL (UserService):**
- ✅ Index on username, email for fast lookups
- ✅ Connection pooling (SQLAlchemy)

### 2. Service Communication

**Current: Synchronous HTTP**
- ✅ Simple implementation
- ❌ Tight coupling, cascading failures

**Improvement: Message Queue (RabbitMQ/Kafka)**
- ✅ Asynchronous, decoupled
- ✅ Retry mechanism, dead letter queue
- ✅ Event sourcing pattern

### 3. Caching Strategy

**Redis Cache Layer:**
```python
# Cache driver info (reduce MongoDB reads)
key = f"driver:{driver_id}:info"
cached = redis.get(key)
if cached:
    return json.loads(cached)
else:
    driver = db.drivers.find_one({"driver_id": driver_id})
    redis.setex(key, 300, json.dumps(driver))  # 5 min TTL
    return driver
```

### 4. Rate Limiting

**API Gateway (Nginx/Kong):**
```nginx
limit_req_zone $binary_remote_addr zone=api:10m rate=10r/s;

location /api/ {
    limit_req zone=api burst=20 nodelay;
    proxy_pass http://backend;
}
```

---

## Monitoring & Observability

### Health Check Endpoints

Mỗi service expose `/health` endpoint:

```python
@app.get("/health")
async def health_check():
    try:
        # Check database connection
        db.command("ping")
        return {"status": "healthy", "database": "connected"}
    except Exception as e:
        return {"status": "unhealthy", "error": str(e)}
```

### Logging Best Practices

```python
import logging

logger = logging.getLogger(__name__)

# Structured logging
logger.info("Trip created", extra={
    "trip_id": trip_id,
    "passenger_id": passenger_id,
    "pickup_lat": pickup.lat,
    "pickup_lng": pickup.lng
})
```

### Metrics (Prometheus/Grafana)

**Key Metrics to Track:**
- Request rate (requests/sec per service)
- Response time (p50, p95, p99)
- Error rate (4xx, 5xx)
- WebSocket active connections
- Redis GEORADIUS query time
- Database query latency

---

## Disaster Recovery

### Backup Strategy

**Databases:**
- PostgreSQL: Automated daily backups (Azure/AWS)
- MongoDB: Continuous backups (MongoDB Atlas)
- Redis: Daily snapshots, AOF persistence

**Code & Infrastructure:**
- Git repository (GitHub)
- Docker images (Azure Container Registry)
- Kubernetes manifests (Infrastructure as Code)

### Rollback Procedure

```bash
# Rollback to previous deployment
kubectl rollout undo deployment/tripservice -n uitgo

# Check rollout status
kubectl rollout status deployment/tripservice -n uitgo
```

---

## Future Improvements

### 1. Architectural Enhancements
- [ ] Implement API Gateway (Kong/Ambassador)
- [ ] Add service mesh (Istio) for mTLS
- [ ] Introduce event-driven architecture (Kafka)
- [ ] Implement circuit breaker pattern

### 2. Security Enhancements
- [ ] Add `aud` claim to service tokens
- [ ] Implement token refresh mechanism
- [ ] Add rate limiting per user/service
- [ ] Implement request signing for service-to-service

### 3. Operational Improvements
- [ ] Add distributed tracing (Jaeger/Zipkin)
- [ ] Implement centralized logging (ELK stack)
- [ ] Add Prometheus metrics + Grafana dashboards
- [ ] Setup alerting (PagerDuty)

### 4. Feature Enhancements
- [ ] Driver surge pricing algorithm
- [ ] Machine learning for demand prediction
- [ ] Real-time traffic integration (Google Traffic API)
- [ ] Multi-language support

---

## References

- **Deployment Guide**: [DEPLOY.md](DEPLOY.md)
- **Environment Setup**: [ENV.sample](ENV.sample)
- **Mapbox API**: https://docs.mapbox.com/api/navigation/directions/
- **VNPay Integration**: https://sandbox.vnpayment.vn/apis/docs/
- **Kubernetes Docs**: https://kubernetes.io/docs/
- **FastAPI Docs**: https://fastapi.tiangolo.com/
