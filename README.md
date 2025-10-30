﻿# UIT-Go

Tài liệu kiến trúc hệ thống: xem `docs/ARCHITECTURE.md` để nắm tổng quan microservice, sơ đồ sequence và cách các service giao tiếp (HTTP/WS).

## Thành phần & cổng

- FastAPI microservices + MongoDB; LocationService dùng Redis + WebSocket.
- Cổng ngoài (localhost):
	- UserService: 8000
	- LocationService: 8001
	- TripService: 8002
	- DriverService: 8003
	- PaymentService: 8004

## Onboarding nhanh

1) Đọc `docs/ARCHITECTURE.md` (sơ đồ và luồng chính).
2) Tạo file môi trường: copy `docs/ENV.sample` thành `.env` và điền giá trị.
3) Kiểm tra `docker-compose.yml` đã trỏ đúng các URL nội bộ (userservice, driverservice, locationservice, paymentservice).
4) Chạy bằng Docker Compose.

> Lưu ý: PaymentService cần `BASE_URL` là public URL để VNPay redirect/callback (nếu dùng ngrok, lấy HTTPS URL hiển thị từ ngrok và set vào `BASE_URL`).

## API (rút gọn – xem code để chi tiết)

- UserService: `/auth/register`, `/auth/login`, `/auth/token`, `/users/*`
- TripService: `/fare-estimate`, `/trip-requests/complete`, `/trips/*`
- DriverService: `/drivers/*`, nội bộ: `/drivers/internal/{id}`
- LocationService: `/drivers/nearby`, `/notify/*`, WS `/ws/driver/*`, `/ws/trip/*`
- PaymentService: `/process-payment`, `/payment-return`, `/users/{id}/wallet`, `/wallets/top-up`