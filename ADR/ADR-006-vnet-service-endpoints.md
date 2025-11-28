# ADR-006: Chọn VNet Service Endpoints thay vì Private Endpoints

## Bối cảnh
CosmosDB và Redis đang publish ra Internet. Private Endpoint mang lại bảo mật cao nhưng phát sinh chi phí (≈$15/tháng mỗi dịch vụ) và phức tạp hóa routing.

## Quyết định
Sử dụng **VNet Service Endpoints + NSG** cho CosmosDB, Redis, Storage, Container Registry và SQL thay vì Private Endpoint.

## Lý do
1. **Chi phí $0**: Service Endpoint miễn phí, chỉ cần cấu hình subnet.
2. **Tốc độ triển khai**: Terraform có thể áp dụng trong vài phút, không cần phê duyệt DNS.
3. **Đủ an toàn**: Khi kết hợp với NSG + `public_network_access = false`, chỉ subnet AKS mới truy cập được.
4. **Đơn giản hóa vận hành**: Không cần quản lý Private DNS zone riêng cho mỗi dịch vụ (trừ PostgreSQL đã có).

## Hệ quả
- Phải duy trì subnet hygiene (không xóa service endpoint).
- Alerts cần theo dõi việc ai đó bật lại `public_network_access`.
- Nếu sau này cần cross-region, cân nhắc nâng cấp lên Private Endpoint.

