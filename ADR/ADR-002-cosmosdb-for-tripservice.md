# ADR-002: Sử dụng Cosmos DB (MongoDB API) cho TripService

## Context (Bối cảnh)

TripService cần lưu trữ thông tin chuyến đi với các yêu cầu:
- Schema có thể thay đổi theo thời gian (thêm fields mới cho features)
- Nested documents phức tạp (pickup/dropoff location, fare, payment, rating, cancellation)
- Geospatial queries (tìm trips gần location)
- High write throughput (nhiều trips được tạo đồng thời)
- Flexible data model (mỗi trip có thể có metadata khác nhau)
- Document size lớn (trip data + history + metadata)

## Decision (Quyết định)

Chọn **Azure Cosmos DB với MongoDB API** làm database cho TripService.

## Alternatives Considered (Các phương án đã xem xét)

### 1. PostgreSQL với JSONB
**Ưu điểm:**
- Relational + flexible JSONB columns
- ACID compliance
- Chi phí thấp hơn

**Nhược điểm:**
- Geospatial queries phức tạp hơn MongoDB
- Không native horizontal scaling
- JSONB indexing performance kém hơn MongoDB
- Kém linh hoạt cho nested documents

### 2. DynamoDB
**Ưu điểm:**
- Serverless, auto-scaling
- Chi phí pay-as-you-go

**Nhược điểm:**
- Vendor lock-in (AWS)
- Team không quen DynamoDB query patterns
- Geospatial support phức tạp
- Cần học query patterns mới (partition key, sort key)

### 3. MongoDB Atlas
**Ưu điểm:**
- Native MongoDB, full features
- Geospatial support tuyệt vời
- Aggregation pipeline mạnh

**Nhược điểm:**
- Chi phí cao hơn Cosmos DB (với Azure credits)
- Không native integration với Azure services
- Cần quản lý cluster riêng

## Consequences (Hậu quả/Trade-offs)

### Ưu điểm:
- ✅ **Flexible schema**: Dễ thêm fields mới (vehicle_details, promotions, etc.)
- ✅ **Geospatial queries**: Native `$near`, `$geoWithin` cho location-based search
- ✅ **Horizontal scaling**: Cosmos DB auto-scale theo throughput
- ✅ **Global distribution**: Có thể replicate sang regions khác
- ✅ **Nested documents**: Lưu pickup/dropoff/payment trong 1 document
- ✅ **Aggregation**: Tính statistics (total_trips, revenue) dễ dàng
- ✅ **Azure integration**: Native với AKS, managed service

### Nhược điểm:
- ❌ **Chi phí cao**: RU/s pricing, có thể tốn kém khi traffic tăng
- ❌ **No ACID across documents**: Chỉ ACID trong 1 document
- ❌ **Query cost**: Mỗi query tốn RU/s, phải optimize cẩn thận
- ❌ **Limited MongoDB compatibility**: Không phải full MongoDB features

### Risks:
- **Risk**: Chi phí Cosmos DB vượt ngân sách khi scale
  - **Mitigation**:
    - Sử dụng autoscale RU/s
    - Monitor và optimize queries
    - Archive old trips sang cheap storage
    - Sử dụng TTL cho temporary data

- **Risk**: MongoDB compatibility issues với Cosmos DB
  - **Mitigation**:
    - Test kỹ trước khi deploy
    - Tránh dùng features MongoDB mới nhất
    - Sử dụng motor driver compatible

## Implementation Notes

- Sử dụng motor (async MongoDB driver)
- Tạo geospatial index trên `pickup.location` và `dropoff.location`
- Index trên: `passenger_id`, `driver_id`, `status`, `created_at`
- Sử dụng compound index cho queries thường dùng
- Set TTL cho trips > 2 năm (auto-delete hoặc archive)
- Connection pool: 100 connections max

## Data Model Example

```javascript
{
  "_id": ObjectId("..."),
  "passenger_id": "uuid",
  "driver_id": "uuid",
  "status": "COMPLETED",
  "vehicle_type": "car",
  "pickup": {
    "latitude": 10.762622,
    "longitude": 106.660172,
    "address": "227 Nguyen Van Cu",
    "location": { "type": "Point", "coordinates": [106.660172, 10.762622] }
  },
  "dropoff": { /* same structure */ },
  "fare": { "estimated": 35000, "actual": 40000 },
  "payment": { "method": "Cash", "status": "COMPLETED" },
  "rating": { "stars": 5, "comment": "Great!" },
  "created_at": ISODate("2025-11-01T09:00:00Z"),
  "completed_at": ISODate("2025-11-01T09:30:00Z")
}
```

## Related Decisions

- ADR-001: PostgreSQL cho UserService (relational data)
- ADR-005: PaymentService cũng dùng Cosmos DB (payment transactions)
