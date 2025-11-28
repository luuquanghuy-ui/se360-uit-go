# ADR-007: Linkerd thay vì Istio cho Service Mesh

## Bối cảnh
UIT-Go cần mTLS và observability nội bộ. Istio mạnh nhưng resource footprint cao và yêu cầu đội vận hành lớn.

## Quyết định
Triển khai **Linkerd 2.x** làm service mesh chính.

## Lý do
1. **Chi phí**: Linkerd OSS miễn phí, Istio managed version tốn phí.
2. **Đơn giản**: CLI + manifest dễ cài đặt, ít CRD, phù hợp đội 1-2 người.
3. **Hiệu năng**: Proxy viết bằng Rust, overhead <10ms, footprint ~50MB RAM.
4. **Bảo mật**: mTLS mặc định, certificate rotation tự động 24h.

## Hệ quả
- Cần huấn luyện đội về Linkerd CLI (`linkerd check`, `linkerd viz`).
- Nếu future cần advanced traffic shaping (L7 routing phức tạp) mới cân nhắc Istio.

