# Runbook sự cố bảo mật UIT-Go

Các quy trình dưới đây map trực tiếp với Phase 5 trong `docs/plan.md`. Mỗi runbook liệt kê tín hiệu kích hoạt, bước khắc phục, và tiêu chí đóng sự cố.

## 1. High CPU Alert (>80%)
- **Tín hiệu**: Azure Monitor alert `aks-high-cpu`.
- **Mục tiêu**: Xác định có tấn công DoS hay workload bất thường.
- **Bước xử lý**:
  1. `kubectl top nodes` và `kubectl top pods` để tìm pod vượt ngưỡng.
  2. Kiểm tra ingress metrics (Linkerd viz) xem có spike request nào bất thường.
  3. Scale ngang deployment bị ảnh hưởng (`kubectl scale deploy/...`).
  4. Nếu traffic ác ý, áp dụng rate limiting tại ingress và tạm thời chặn IP bằng WAF.
- **Đóng sự cố**: CPU <60% trong 30 phút và metrics ổn định.

## 2. Pod Restart Loop / CrashLoopBackOff
- **Tín hiệu**: Alert `pod-restart`.
- **Bước xử lý**:
  1. `kubectl describe pod` để lấy event.
  2. `kubectl logs -p <pod>` kiểm tra trace.
  3. So sánh resource usage với limit, tăng limit hoặc tối ưu code.
  4. Nếu do secret thay đổi, kích hoạt rollout restart toàn deployment.
- **Đóng sự cố**: Pod trở lại trạng thái `Ready=1/1` trong ≥3 lần kiểm tra.

## 3. Service Mesh mTLS Failure
- **Tín hiệu**: Alert `mesh-mtls-error`.
- **Bước xử lý**:
  1. `linkerd check` để xác minh control plane.
  2. `linkerd edges deploy` xem cặp service nào fail.
  3. Kiểm tra certificate expiry (`linkerd identity list`).
  4. `kubectl rollout restart deploy/<svc>` để tái cấp cert nếu cần.
- **Đóng sự cố**: `linkerd check` trả về OK, không còn error log.

## 4. Database Connection Failures
- **Tín hiệu**: Alert `db-connection-failure`.
- **Bước xử lý**:
  1. Đảm bảo NSG/Service Endpoint không thay đổi (`az network vnet subnet show ...`).
  2. Xác minh secret/connection string còn hợp lệ (`kubectl get secret uitgo-secrets -o yaml`).
  3. Chạy pod debug trong subnet (`kubectl run psql-debug ...`) để kiểm tra kết nối.
  4. Nếu Postgres maintenance, chuyển traffic sang instance DR.
- **Đóng sự cố**: Ứng dụng ghi log kết nối thành công, alert clear.

## 5. Suspicious Login Activity
- **Tín hiệu**: Azure Monitor security event hoặc log `401` bất thường.
- **Bước xử lý**:
  1. Truy vấn Log Analytics `SigninLogs`/application logs với IP, user agent.
  2. Kích hoạt `kubectl scale deploy/userservice --replicas=0` nếu cần phong tỏa.
  3. Reset mật khẩu người dùng bị ảnh hưởng, thu hồi token (xóa Redis session).
  4. Bật MFA hoặc rate limit tạm thời qua ingress annotations.
- **Đóng sự cố**: Không còn đăng nhập khả nghi trong 24h, người dùng xác nhận OK.

## 6. Container Image Vulnerability (CVE)
- **Tín hiệu**: Trivy/GitHub alert severity HIGH/CRITICAL.
- **Bước xử lý**:
  1. Kiểm tra gói bị ảnh hưởng từ report.
  2. Cập nhật dependency hoặc đổi base image.
  3. Chạy lại `security_scans` job để xác nhận fix.
  4. Rollout deployment với image mới và xoá tag cũ khỏi ACR.
- **Đóng sự cố**: Trivy báo sạch, deployment đang chạy image mới nhất (`kubectl get deploy -o jsonpath='{.spec.template.spec.containers[*].image}'`).

