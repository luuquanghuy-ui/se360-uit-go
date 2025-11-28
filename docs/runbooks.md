# Runbook sự cố bảo mật UIT-Go

Các quy trình dưới đây map trực tiếp với Phase 5 trong `docs/plan.md`. Mỗi runbook liệt kê tín hiệu kích hoạt, bước khắc phục, và tiêu chí đóng sự cố.

## 1. [High CPU Alert](runbooks/01-high-cpu-alert.md)
- **Tín hiệu**: Azure Monitor alert `aks-high-cpu`.
- **Mục tiêu**: Phát hiện DoS / workload bất thường.
- **Đóng sự cố**: CPU <60% trong 30 phút và metrics ổn định.

## 2. [Pod Restart Loop](runbooks/02-pod-restart-loop.md)
- **Tín hiệu**: Alert `pod-restart`.
- **Mục tiêu**: Gỡ CrashLoopBackOff / OOM.
- **Đóng sự cố**: Pod trở lại `Ready=1/1` qua ≥3 lần kiểm tra.

## 3. [Service Mesh mTLS Failure](runbooks/03-mtls-failure.md)
- **Tín hiệu**: Alert `mesh-mtls-error`.
- **Mục tiêu**: Khôi phục Linkerd mTLS + certificates.
- **Đóng sự cố**: `linkerd check` pass, không còn TLS error.

## 4. [Database Connection Failures](runbooks/04-database-connection.md)
- **Tín hiệu**: Alert `db-connection-failure`.
- **Mục tiêu**: Khôi phục kết nối Postgres/Cosmos/Redis.
- **Đóng sự cố**: Health check 200 trong ≥15 phút.

## 5. [Suspicious Login Activity](runbooks/05-suspicious-login.md)
- **Tín hiệu**: Azure Monitor security event, spike 401/429.
- **Mục tiêu**: Ngăn brute force & lock tài khoản bị ảnh hưởng.
- **Đóng sự cố**: Không còn đăng nhập khả nghi trong 24h.

## 6. [Container Image Vulnerability](runbooks/06-container-vulnerability.md)
- **Tín hiệu**: Trivy/GitHub alert severity HIGH/CRITICAL.
- **Mục tiêu**: Vá CVE, rollout image sạch.
- **Đóng sự cố**: Trivy báo sạch, deployment chạy image mới nhất.

