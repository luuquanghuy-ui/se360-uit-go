# UIT-Go

Tài liệu kiến trúc hệ thống: xem docs/ARCHITECTURE.md để nắm tổng quan microservice, sơ đồ sequence và cách các service giao tiếp (HTTP/WS).

� Ghi chú nhanh:
- Các service dùng FastAPI + MongoDB; LocationService dùng Redis và WebSocket để định vị real-time.
- Cổng ngoài: UserService 8000, LocationService 8001, TripService 8002, DriverService 8003, PaymentService 8004.

📚 Onboarding nhanh:
1) Đọc docs/ARCHITECTURE.md (sơ đồ và luồng chính).
2) Kiểm tra docker-compose.yml và tạo file .env theo ghi chú trong compose.
3) Chạy toàn bộ bằng Docker Compose.

📋 API (rút gọn – xem code từng service để chi tiết):
- UserService: /auth/register, /auth/login, /auth/token, /users/*
- TripService: /fare-estimate, /trip-requests/complete, /trips/*
- DriverService: /drivers/* và /drivers/internal/{id} (nội bộ)
- LocationService: /drivers/nearby, /notify/*, WS /ws/driver/* và /ws/trip/*
- PaymentService: /process-payment, /payment-return, /users/{id}/wallet, /wallets/top-up