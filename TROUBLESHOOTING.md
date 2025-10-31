# 🔥 Troubleshooting Guide

## ❓ Bạn đang gặp vấn đề GÌ?

### Scenario 1: "Test trên Postman không được"
**Triệu chứng:**
- Call API `http://4.144.174.255/auth/register` → Lỗi 400
- Service đang chạy trên Azure
- Muốn test endpoints

**Giải pháp:**
→ **ĐÃ FIX RỒI!**
- Đã sửa bcrypt trong UserService
- Cần **rebuild và deploy** lại image mới

**Làm thế nào:**
```bash
# Build image mới
docker build -t uitgoregistry.azurecr.io/userservice:v1.2 ./UserService

# Push lên ACR (NẾU có ACR)
docker push uitgoregistry.azurecr.io/userservice:v1.2

# Deploy lên AKS
kubectl set image deployment/userservice userservice=uitgoregistry.azurecr.io/userservice:v1.2 -n uitgo
```

---

### Scenario 2: "GitHub Actions build/deploy fail"
**Triệu chứng:**
- GitHub Actions chạy → ACR login fail
- Lỗi: "uitgoregistry not found"
- Build jobs fail

**Nguyên nhân:**
- ACR `uitgoregistry` **không tồn tại**

**Giải pháp:**
```bash
# Option A: Tạo ACR mới
bash scripts/create-acr.sh

# Option B: Disable build jobs (ĐÃ LÀM)
# Các build jobs có && false → skip
```

---

## 📊 **So sánh 2 vấn đề:**

| Aspect | Postman Test Fail | ACR Login Fail |
|--------|------------------|----------------|
| **Đâu?** | Production (Azure AKS) | CI/CD (GitHub Actions) |
| **Khi nào?** | Khi gọi API từ Postman | Khi push code lên GitHub |
| **Nguyên nhân** | Service chưa rebuild với fix mới | ACR không tồn tại |
| **Ảnh hưởng** | User không dùng được app | Không deploy được tự động |
| **Đã fix?** | Code đã fix, chưa deploy | Build jobs đã disable |

---

## 🎯 **BẠN ĐANG GẶP VẤN ĐỀ NÀO?**

### A. "Tôi test API trên Postman bị lỗi 400"

**Current situation:**
- Service đang chạy version CŨ (có bug bcrypt)
- Code đã fix nhưng chưa deploy
- Cần deploy version MỚI

**Solution:**
```bash
# 1. Kiểm tra pod đang chạy version nào
kubectl get pods -n uitgo -o wide

# 2. Kiểm tra image version
kubectl describe pod <pod-name> -n uitgo | grep Image:

# 3. Rebuild và deploy manual (vì CI/CD đang disable)
# Xem phần "Manual Deploy" bên dưới
```

---

### B. "Tôi muốn tự động deploy khi push code"

**Current situation:**
- GitHub Actions test ✅ chạy OK
- Build/Deploy ❌ bị disable vì ACR không có

**Solution:**
```bash
# 1. Tạo ACR
bash scripts/create-acr.sh

# 2. Remove && false từ workflow
# 3. Setup GitHub secrets
# 4. Push code → tự động deploy
```

---

## 🚀 **Manual Deploy (Deploy ngay fix mới)**

Nếu bạn muốn deploy fix bcrypt **NGAY BÂY GIỜ** mà không cần CI/CD:

### Bước 1: Tìm ACR thật của bạn
```bash
az acr list --output table
```

**Output giả sử:**
```
NAME              RESOURCE GROUP    LOCATION      SKU    LOGIN SERVER
myuitgoacr        uitgo-rg          eastus        Basic  myuitgoacr.azurecr.io
```

### Bước 2: Build và push image
```bash
# Thay "myuitgoacr" bằng tên ACR thật
ACR_NAME="myuitgoacr"

# Login
az acr login --name $ACR_NAME

# Build
docker build -t ${ACR_NAME}.azurecr.io/userservice:v1.2 ./UserService

# Push
docker push ${ACR_NAME}.azurecr.io/userservice:v1.2
```

### Bước 3: Deploy lên AKS
```bash
# Update deployment
kubectl set image deployment/userservice \
  userservice=${ACR_NAME}.azurecr.io/userservice:v1.2 \
  -n uitgo

# Verify
kubectl rollout status deployment/userservice -n uitgo
kubectl get pods -n uitgo
```

### Bước 4: Test lại trên Postman
```
POST http://4.144.174.255/auth/register
{
  "username": "testuser",
  "email": "test@example.com",
  "password": "password123",
  "user_type": "passenger"
}
```

---

## 🔍 **Debugging Current Production Issue**

Xem pod hiện tại đang chạy gì:

```bash
# 1. Xem logs
kubectl logs -f deployment/userservice -n uitgo

# 2. Xem image version
kubectl get pods -n uitgo -o jsonpath='{.items[0].spec.containers[0].image}'

# 3. Xem pod status
kubectl describe pod -n uitgo -l app=userservice
```

---

## ❓ **Câu hỏi để clarify:**

1. **Bạn có ACR không?**
   ```bash
   az acr list --output table
   ```
   - Có → Tên là gì?
   - Không → Cần tạo

2. **Service đang chạy trên Azure không?**
   ```bash
   kubectl get pods -n uitgo
   ```
   - Có pods đang chạy → Deploy version mới
   - Không có → Setup từ đầu

3. **Bạn muốn gì bây giờ?**
   - A. Fix ngay lỗi test Postman → Manual deploy
   - B. Setup CI/CD tự động → Tạo ACR, enable workflow
   - C. Cả 2 → Làm A trước, B sau

---

## 💡 **Quick Fix (5 phút)**

Nếu chỉ muốn **fix lỗi Postman ngay**:

```bash
# 1. Tìm ACR
ACR_NAME=$(az acr list --query "[0].name" -o tsv)
echo "ACR: $ACR_NAME"

# 2. Build & push
az acr login --name $ACR_NAME
docker build -t ${ACR_NAME}.azurecr.io/userservice:fix-bcrypt ./UserService
docker push ${ACR_NAME}.azurecr.io/userservice:fix-bcrypt

# 3. Deploy
kubectl set image deployment/userservice \
  userservice=${ACR_NAME}.azurecr.io/userservice:fix-bcrypt \
  -n uitgo

# 4. Wait
kubectl rollout status deployment/userservice -n uitgo

# 5. Test Postman
```

Done! ✅
