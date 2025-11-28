# ADR-008: Ưu tiên OSS Security Tooling trong CI/CD

## Bối cảnh
Pipeline hiện không có lớp bảo mật. Các giải pháp thương mại (Snyk, Veracode, Burp Enterprise) vượt ngân sách.

## Quyết định
Thêm 6 công cụ OSS vào GitHub Actions:
1. Bandit (SAST)
2. Safety (SCA)
3. TruffleHog (Secret scan)
4. Checkov (IaC)
5. Trivy (Container & filesystem)
6. OWASP ZAP baseline (DAST)

## Lý do
- **Chi phí $0** nhưng vẫn phủ được hầu hết OWASP Top 10.
- Các tool dễ tích hợp CLI, không cần self-host server.
- Có thể xuất SARIF để đồng bộ vào GitHub Security tab.

## Hệ quả
- Pipeline build lâu hơn ~6-8 phút.
- Cần duy trì baseline (allowlist) cho Safety/Trivy để tránh false positive.
- yêu cầu secret `DAST_TARGET_URL` để chạy ZAP trên môi trường staging.

