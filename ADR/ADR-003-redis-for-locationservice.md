# ADR-003: Sử dụng Redis cho LocationService

**Ngày:** 2025-10-17
**Trạng thái:** Accepted
**Người quyết định:** UIT-GO Development Team

## Context (Bối cảnh)

LocationService cần lưu trữ vị trí real-time của tài xế với các yêu cầu:
- **Real-time updates**: Tài xế cập nhật vị trí mỗi 2-3 giây
- **High write throughput**: Hàng trăm drivers cập nhật đồng thời
- **Low latency reads**: Tìm drivers gần passenger < 100ms
- **Geospatial queries**: Tìm drivers trong bán kính X km
- **TTL (Time-to-live)**: Vị trí cũ tự động xóa khi driver offline
- **Ephemeral data**: Không cần lưu trữ lâu dài, chỉ cần real-time

## Decision (Quyết định)

Chọn **Azure Cache for Redis** làm database cho LocationService.

## Alternatives Considered (Các phương án đã xem xét)

### 1. Cosmos DB (như TripService)
**Ưu điểm:**
- Geospatial support tốt
- Persistent storage
- Đã dùng cho TripService

**Nhược điểm:**
- Chi phí RU/s cao cho write-heavy workload
- Overkill cho ephemeral data
- Latency cao hơn Redis (50-100ms vs 1-5ms)
- Không có TTL tự động cho từng key

### 2. PostgreSQL với PostGIS
**Ưu điểm:**
- Geospatial queries mạnh
- ACID compliance
- Persistent storage

**Nhược điểm:**
- Latency cao (10-50ms)
- Khó scale cho write-heavy
- Connection overhead
- Overkill cho temporary location data

### 3. In-memory dictionary (Python)
**Ưu điểm:**
- Cực nhanh
- Không cần external service
- Không tốn tiền

**Nhược điểm:**
- Mất data khi pod restart
- Không scale across pods
- Không có geospatial queries built-in
- Không HA (High Availability)

### 4. Memcached
**Ưu điểm:**
- Rất nhanh, low latency
- Simple key-value

**Nhược điểm:**
- KHÔNG có geospatial support (deal-breaker)
- Không có data structures phức tạp
- Không có TTL per key

## Consequences (Hậu quả/Trade-offs)

### Ưu điểm:
- ✅ **Ultra-low latency**: Sub-millisecond reads/writes (1-5ms)
- ✅ **Geospatial commands**: `GEOADD`, `GEORADIUS`, `GEODIST` native
- ✅ **High throughput**: Handle hàng nghìn writes/second
- ✅ **TTL support**: Auto-expire driver location khi offline
- ✅ **In-memory**: Blazing fast, perfect cho real-time
- ✅ **Data structures**: Sorted Sets, Hashes, Lists
- ✅ **Pub/Sub**: Có thể dùng cho notifications (future)
- ✅ **Chi phí thấp**: Azure Redis cache cheaper than Cosmos

### Nhược điểm:
- ❌ **Volatile storage**: Data mất khi restart (acceptable cho location)
- ❌ **Memory limit**: Cần monitor memory usage
- ❌ **No complex queries**: Chỉ có basic operations
- ❌ **Single-threaded**: Redis chạy single thread (nhưng vẫn rất nhanh)

### Risks:
- **Risk**: Redis instance crash → mất hết location data
  - **Mitigation**:
    - Acceptable vì location là ephemeral
    - Drivers sẽ reconnect và update lại vị trí
    - Sử dụng Redis HA (clustering)

- **Risk**: Memory full khi quá nhiều drivers
  - **Mitigation**:
    - Set TTL 5 phút cho mỗi location
    - Eviction policy: `allkeys-lru`
    - Monitor memory usage và scale up nếu cần
    - Giới hạn max drivers concurrent

- **Risk**: Geospatial query performance khi có hàng nghìn drivers
  - **Mitigation**:
    - Redis GEORADIUS rất nhanh (<5ms cho 10k points)
    - Giới hạn radius search (max 20km)
    - Sử dụng Redis clustering nếu cần

## Implementation Notes

### Data Structure
```
Key: "driver_locations"
Type: Geospatial Index (Sorted Set)

GEOADD driver_locations 106.660172 10.762622 "driver-id-1"
GEOADD driver_locations 106.670000 10.770000 "driver-id-2"

GEORADIUS driver_locations 106.660172 10.762622 5 km WITHDIST
```

### TTL Strategy
- Set TTL 5 phút cho mỗi driver location
- Driver phải gửi heartbeat mỗi 3 giây
- Nếu không update → auto-remove sau 5 phút

### WebSocket Integration
- LocationService nhận location qua WebSocket
- Update Redis mỗi khi nhận location
- Passenger query Redis để tìm nearby drivers

### Configuration
- Max memory: 1GB (Standard tier)
- Eviction policy: `allkeys-lru`
- Persistence: Disabled (không cần)
- Clustering: Enabled (HA)

## Performance Metrics

- **Write latency**: < 2ms (p99)
- **Read latency**: < 3ms (p99)
- **Throughput**: 100k ops/sec
- **GEORADIUS query**: < 5ms cho 10k drivers

## Related Decisions

- ADR-006: WebSocket cho real-time location updates
- ADR-002: Cosmos DB cho TripService (persistent trip history)

## Future Considerations

- Có thể dùng Redis Pub/Sub để notify nearby drivers về trips mới
- Có thể lưu driver location history vào Cosmos DB (analytics)
- Có thể dùng Redis Streams cho event sourcing
