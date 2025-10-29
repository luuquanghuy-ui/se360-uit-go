# UIT-Go: Kiến trúc hệ thống

Tài liệu này mô tả kiến trúc microservice của dự án, các service giao tiếp với nhau (HTTP/WS), và các luồng nghiệp vụ chính. Mục tiêu là giúp team onboard nhanh và phát triển nhất quán.

## Thành phần hệ thống

- UserService (FastAPI, MongoDB): đăng ký/đăng nhập, cấp JWT cho user và Service Token cho nội bộ.
- TripService (FastAPI, MongoDB): quản lý chuyến, matching, gọi các service nội bộ, tích hợp Mapbox & Payment.
- DriverService (FastAPI, MongoDB): hồ sơ tài xế, ví tài xế (nội bộ), endpoint nội bộ tra cứu tài xế.
- LocationService (FastAPI, Redis + WebSocket): định vị tài xế real-time, tìm tài xế gần, gửi thông báo WS.
- PaymentService (FastAPI, MongoDB): ví người dùng, tạo link thanh toán VNPay, xử lý callback.
- MongoDB: mỗi service có DB riêng (tách collection theo service).
- Redis: GEO index vị trí tài xế, lưu kết nối WS.
- Ngrok: expose PaymentService để nhận callback VNPay (tùy môi trường dev).
- External APIs: Mapbox Directions/Geocoding, VNPay.

### Cổng và URL

- Bên ngoài (localhost):
  - UserService: http://localhost:8000
  - LocationService: http://localhost:8001 (WS cũng dùng host/cổng này)
  - TripService: http://localhost:8002
  - DriverService: http://localhost:8003
  - PaymentService: http://localhost:8004
- Nội bộ (Docker network): `http://userservice:8000`, `http://locationservice:8000`, `http://driverservice:8000`, `http://paymentservice:8000`.

## Sơ đồ thành phần

```mermaid
flowchart LR
  FE_Passenger[FE Passenger App]
  FE_Driver[FE Driver App]

  subgraph Docker Network
    US[UserService]
    TS[TripService]
    DS[DriverService]
    LS[LocationService]
    PS[PaymentService]
    M[(MongoDB)]
    R[(Redis)]
  end

  MB[(Mapbox API)]
  VNP[(VNPay)]

  FE_Passenger <-- JWT (user) --> US
  FE_Driver <-- JWT (user) --> US

  FE_Passenger -->|create trip| TS
  TS -->|find nearby| LS
  LS <--> R
  LS -->|notify drivers (WS)| FE_Driver

  FE_Driver -->|assign trip| TS
  TS -->|service token| US
  TS -->|get driver info| DS

  TS -->|notify passenger (WS)| FE_Passenger

  TS --> MB
  TS -->|E-Wallet| PS
  PS --> VNP

  US --- M
  TS --- M
  DS --- M
  PS --- M
```

## Sơ đồ sequence: Tạo chuyến, nhận chuyến, thanh toán

```mermaid
sequenceDiagram
  autonumber
  participant P as Passenger App
  participant T as TripService
  participant L as LocationService
  participant D as Driver App
  participant U as UserService
  participant R as Redis
  participant Dr as DriverService
  participant Pay as PaymentService
  participant V as VNPay
  participant MB as Mapbox

  P->>T: POST /trip-requests/complete (pickup/dropoff, vehicle_type, payment_method)
  T->>MB: Mapbox Directions (route)
  T->>T: Lưu Trip (Mongo)
  T->>L: GET /drivers/nearby
  L->>R: GEOSEARCH
  R-->>L: danh sách driver gần
  L-->>T: driver_ids
  T->>L: POST /notify/drivers (payload TRIP_OFFER)
  L-->>D: WS push TRIP_OFFER

  D->>T: PUT /trips/{id}/assign-driver
  T->>U: POST /auth/token (client credentials)
  U-->>T: Service JWT (type=service)
  T->>Dr: GET /drivers/internal/{driver_id} (Bearer service JWT)
  Dr-->>T: driver details
  T->>L: POST /notify/trip/{id}/passenger (DRIVER_ASSIGNED)
  L-->>P: WS push DRIVER_ASSIGNED

  Note over P,D: Chuyến diễn ra, 2 bên kết nối WS /ws/trip/{id}/{role}

  P->>T: POST /trips/{id}/complete {actual_fare}
  alt payment_method == "E-Wallet"
    T->>Pay: POST /process-payment (trip_id, user_id, driver_id, amount)
    Pay-->>P: payUrl VNPay
    P->>V: redirect thanh toán
    V->>Pay: GET /payment-return
    Pay->>Pay: cập nhật giao dịch (Mongo)
    T->>T: cập nhật trip COMPLETED + fare.actual
  else Cash
    T->>T: cập nhật trip COMPLETED + fare.actual
  end
```

## Giao tiếp giữa các service

- TripService -> LocationService:
  - GET `/drivers/nearby`
  - POST `/notify/drivers` (bắn WS tới nhiều tài xế)
  - POST `/notify/trip/{trip_id}/passenger|driver` (thông báo cho 1 phía trong phòng)
- TripService -> UserService:
  - POST `/auth/token` (client credentials: TRIPSVC_CLIENT_ID/SECRET) để lấy Service JWT
- TripService -> DriverService:
  - GET `/drivers/internal/{driver_id}` kèm Bearer Service JWT (type=service)
- TripService -> PaymentService:
  - POST `/process-payment` khi trip complete và payment_method = "E-Wallet"
- LocationService <-> Driver App:
  - WS `/ws/driver/{driver_id}/location` (driver gửi vị trí; server lưu Redis GEO; server push notification)
- LocationService <-> Passenger/Driver App:
  - WS `/ws/trip/{trip_id}/{user_type}` (relay vị trí 2 chiều + sự kiện trạng thái)

## Chứng thực & bảo mật

- User JWT: trả từ UserService `/auth/login`, dùng cho API dành cho user.
- Service JWT (type=service): trả từ UserService `/auth/token` khi TripService cung cấp client credentials. Dùng cho endpoint nội bộ ở DriverService.
- Gợi ý cải thiện:
  - Thêm claim `aud` khi sinh Service JWT ở UserService và validate `aud` tại DriverService.
  - Retry/backoff khi gọi nội bộ (httpx), circuit breaker.
  - API Gateway cho routing/observability.

## Biến môi trường quan trọng (theo service)

- Mongo/Redis (hạ tầng):
  - `MONGO_ROOT_USER`, `MONGO_ROOT_PASSWORD`, `MONGO_INITDB_DATABASE` (khởi tạo Mongo container)
  - `REDIS_URL` (LocationService), mặc định trong compose trỏ tới `redis://redis:6379`

- UserService:
  - `MONGODB_URL` (ví dụ: mongodb://user:pass@mongodb:27017/uitgo_users?authSource=admin)
  - `SECRET_KEY` (JWT Secret), `ACCESS_TOKEN_EXPIRE_MINUTES`
  - `TRIPSVC_CLIENT_ID`, `TRIPSVC_CLIENT_SECRET` (để cấp Service Token cho TripService)
  - `DRIVER_SERVICE_URL` (nội bộ, nếu cần gọi sang DriverService)

- TripService:
  - `MONGODB_URL` (uitgo_trips), `LOCATION_SERVICE_URL`, `DRIVER_SERVICE_URL`, `PAYMENT_SERVICE_URL`
  - `MAPBOX_ACCESS_TOKEN`
  - `MY_CLIENT_ID`, `MY_CLIENT_SECRET` (client credentials khi xin Service Token từ UserService)
  - `USER_SERVICE_URL`

- DriverService:
  - `MONGODB_URL` (uitgo_drivers), `LOCATION_SERVICE_URL`, `PAYMENT_SERVICE_URL`
  - `SECRET_KEY` (dùng để verify Service JWT gửi tới endpoint nội bộ)

- LocationService:
  - `REDIS_URL`

- PaymentService:
  - `MONGODB_URL` (uitgo_payments), `DRIVER_SERVICE_URL`
  - `VNP_TMN_CODE`, `VNP_HASH_SECRET`, `VNP_URL`
  - `BASE_URL` — Public base URL để VNPay redirect/callback (ví dụ dùng ngrok thì set HTTPS URL của ngrok vào đây). Lưu ý: code hiện tại dùng `BASE_URL` chứ không đọc `NGROK_API_URL`.
  - `NGROK_AUTHTOKEN` thuộc container ngrok (không phải biến của PaymentService)

## Quick start (tuỳ chọn)

- Docker Compose: đảm bảo `.env` đầy đủ (JWT, Mapbox, VNPay, v.v.) rồi chạy compose.
- FE driver/passenger: kết nối WS tới LocationService theo endpoint đã mô tả.

> Tham khảo thêm code trong mỗi service để biết đầy đủ schema và response cụ thể.
