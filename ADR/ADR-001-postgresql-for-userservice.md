# ADR-001: Sử dụng PostgreSQL cho UserService

**Ngày:** 2025-10-15
**Trạng thái:** Accepted
**Người quyết định:** UIT-GO Development Team

## Context (Bối cảnh)

UserService cần lưu trữ thông tin người dùng (passengers và drivers) với các yêu cầu:
- Dữ liệu có cấu trúc rõ ràng (user profile, authentication)
- Cần đảm bảo tính toàn vẹn dữ liệu (ACID)
- Quan hệ giữa User và Driver (1-1 relationship)
- Cần hỗ trợ unique constraints (email, phone, username)
- Queries đơn giản (lookup by email, ID)
- Dữ liệu nhạy cảm (password hashing, personal info)

## Decision (Quyết định)

Chọn **PostgreSQL** (Azure Database for PostgreSQL) làm database cho UserService.

## Alternatives Considered (Các phương án đã xem xét)

### 1. MongoDB (Cosmos DB)
**Ưu điểm:**
- Schema flexible, dễ thay đổi
- Horizontal scaling tốt
- Đã sử dụng cho TripService, giảm số loại database

**Nhược điểm:**
- Không có foreign key constraints
- ACID chỉ trong document/collection level
- Chi phí Cosmos DB cao hơn PostgreSQL
- Overkill cho dữ liệu có schema cố định

### 2. MySQL
**Ưu điểm:**
- Relational database, ACID compliance
- Chi phí thấp
- Team quen thuộc

**Nhược điểm:**
- Ít tính năng nâng cao hơn PostgreSQL (JSON, full-text search)
- Community support nhỏ hơn

### 3. SQL Server
**Ưu điểm:**
- Native support trên Azure
- Enterprise features mạnh

**Nhược điểm:**
- Chi phí cao
- Overkill cho scale của dự án
- License restrictions

## Consequences (Hậu quả/Trade-offs)

### Ưu điểm:
- ✅ **ACID compliance**: Đảm bảo tính toàn vẹn dữ liệu user
- ✅ **Constraints**: Unique email/phone tự động enforce ở DB level
- ✅ **Chi phí thấp**: Azure PostgreSQL rẻ hơn Cosmos DB
- ✅ **Mature ecosystem**: SQLAlchemy, psycopg3, migrations tools
- ✅ **JSON support**: Có thể lưu metadata linh hoạt nếu cần
- ✅ **Team familiar**: Team đã có kinh nghiệm với PostgreSQL

### Nhược điểm:
- ❌ **Vertical scaling**: Khó scale ngang hơn NoSQL
- ❌ **Mixed tech stack**: Thêm 1 loại database (PostgreSQL + Cosmos + Redis)
- ❌ **Connection pooling**: Cần quản lý connection pool cẩn thận

### Risks:
- **Risk**: PostgreSQL có thể trở thành bottleneck khi users tăng lên millions
  - **Mitigation**: Sử dụng read replicas, caching (Redis), index optimization

- **Risk**: Schema migration phức tạp khi production
  - **Mitigation**: Sử dụng Alembic cho database migrations, test kỹ trước khi deploy

## Implementation Notes

- Sử dụng SQLAlchemy ORM với async support
- Enable connection pooling
- Index trên: email, phone, username
- Password phải hash bằng bcrypt trước khi lưu
- Định kỳ backup tự động (Azure backup)

## Related Decisions

- ADR-002: Chọn Cosmos DB cho TripService (NoSQL cho flexible schema)
- ADR-003: Chọn Redis cho LocationService (real-time data)
