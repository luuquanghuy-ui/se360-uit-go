# Architectural Decision Records (ADR)

Thư mục này chứa các bản ghi quyết định kiến trúc (Architectural Decision Records - ADR) cho dự án UIT-GO.

## 📚 Danh sách ADRs

| ADR | Tiêu đề | Trạng thái | Ngày |
|-----|---------|-----------|------|
| [ADR-001](ADR-001-postgresql-for-userservice.md) | PostgreSQL cho UserService | Accepted | 2025-10-15 |
| [ADR-002](ADR-002-cosmosdb-for-tripservice.md) | Cosmos DB (MongoDB) cho TripService | Accepted | 2025-10-16 |
| [ADR-003](ADR-003-redis-for-locationservice.md) | Redis cho LocationService | Accepted | 2025-10-17 |
| [ADR-004](ADR-004-microservices-architecture.md) | Microservices Architecture | Accepted | 2025-10-10 |
| [ADR-005](ADR-005-kubernetes-deployment.md) | Kubernetes/AKS cho Deployment | Accepted | 2025-10-12 |

## 🎯 ADR là gì?

**Architectural Decision Record (ADR)** là tài liệu ghi lại các quyết định quan trọng về kiến trúc hệ thống, bao gồm:
- **Bối cảnh** (Context): Tại sao cần quyết định này?
- **Quyết định** (Decision): Chọn giải pháp gì?
- **Các phương án** (Alternatives): Đã xem xét những gì khác?
- **Hậu quả** (Consequences): Ưu/nhược điểm, trade-offs, risks

## 🤔 Tại sao cần ADR?

1. **Lưu giữ lịch sử**: Hiểu được tại sao chọn PostgreSQL thay vì MongoDB cho UserService
2. **Onboarding nhanh**: Dev mới hiểu được kiến trúc và lý do thiết kế
3. **Tránh tranh luận lặp lại**: "Tại sao không dùng MySQL?" → Đọc ADR-001
4. **Review decisions**: Có thể revisit và change quyết định khi context thay đổi
5. **Học hỏi**: Hiểu trade-offs, không repeat mistakes

## 📝 Khi nào tạo ADR mới?

Tạo ADR khi:
- ✅ Chọn database/technology stack
- ✅ Chọn architecture pattern (monolith vs microservices)
- ✅ Chọn deployment platform (K8s, AWS, Azure)
- ✅ Quyết định về security, scaling, monitoring
- ✅ Breaking changes trong API design
- ✅ Vendor selection (payment gateway, cloud provider)

Không cần ADR khi:
- ❌ Implementation details nhỏ (variable naming, code style)
- ❌ Temporary workarounds
- ❌ Obvious choices (dùng Git cho version control)

## 📄 Template ADR

```markdown
# ADR-XXX: [Tiêu đề ngắn gọn]

**Ngày:** YYYY-MM-DD
**Trạng thái:** [Proposed | Accepted | Deprecated | Superseded]
**Người quyết định:** [Team/người]

## Context (Bối cảnh)
[Mô tả vấn đề, yêu cầu, constraints]

## Decision (Quyết định)
[Quyết định cuối cùng là gì?]

## Alternatives Considered (Các phương án đã xem xét)
### 1. Phương án A
**Ưu điểm:** ...
**Nhược điểm:** ...

### 2. Phương án B
**Ưu điểm:** ...
**Nhược điểm:** ...

## Consequences (Hậu quả/Trade-offs)

### Ưu điểm:
- ✅ ...

### Nhược điểm:
- ❌ ...

### Risks:
- **Risk**: ...
  - **Mitigation**: ...

## Implementation Notes
[Chi tiết kỹ thuật, config, best practices]

## Related Decisions
- ADR-XXX: ...
```

## 🔄 Trạng thái ADR

- **Proposed**: Đang đề xuất, chưa quyết định
- **Accepted**: Đã chấp nhận và đang áp dụng
- **Deprecated**: Không dùng nữa nhưng chưa thay thế
- **Superseded**: Đã bị thay thế bởi ADR mới (ghi rõ ADR nào)

## 📊 ADR Workflow

```
1. Gặp vấn đề cần quyết định kiến trúc
   ↓
2. Research & brainstorm các phương án
   ↓
3. Tạo ADR-XXX-draft.md với status "Proposed"
   ↓
4. Team review & discuss
   ↓
5. Quyết định → Update status "Accepted"
   ↓
6. Commit ADR vào Git
   ↓
7. Implement theo quyết định
```

## 🛠️ Cách tạo ADR mới

1. Copy template ở trên
2. Đặt tên: `ADR-XXX-short-title.md` (XXX là số thứ tự)
3. Fill in các sections
4. Tạo PR để team review
5. Sau khi approved → merge và update README.md

## 📖 Đọc thêm

- [ADR GitHub](https://adr.github.io/)
- [Documenting Architecture Decisions - Michael Nygard](https://cognitect.com/blog/2011/11/15/documenting-architecture-decisions)
- [ADR Tools](https://github.com/npryce/adr-tools)

## 🙋 FAQs

**Q: ADR có cần update không?**
A: Không! ADR ghi lại quyết định TẠI THỜI ĐIỂM ĐÓ. Nếu thay đổi → tạo ADR mới và supersede ADR cũ.

**Q: ADR dài bao nhiêu?**
A: 1-3 pages. Đủ context nhưng không quá dài.

**Q: Ai viết ADR?**
A: Người đề xuất quyết định, nhưng cả team phải review & approve.

**Q: ADR vs RFC?**
A: ADR ghi lại QUYẾT ĐỊNH đã chốt. RFC (Request for Comments) là đề xuất, discussion.

---

**Made with ❤️ by UIT-GO Team**
