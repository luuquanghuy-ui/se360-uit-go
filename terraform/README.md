# Terraform Deployment Guide

Hướng dẫn deploy infrastructure lên Azure sử dụng Terraform.

## 🚀 Chuẩn Bị

### 1. Cài đặt công cụ

```bash
# Cài Terraform (https://www.terraform.io/downloads)
# Cài Azure CLI (https://docs.microsoft.com/en-us/cli/azure/install-azure-cli)
```

### 2. Đăng nhập Azure

```bash
az login

# Kiểm tra subscription
az account show

# Nếu có nhiều subscription, chọn đúng cái
az account set --subscription "d8ece151-084a-418c-a446-0ff133a2d388"
```

### 3. Tạo file chứa mật khẩu database

**QUAN TRỌNG:** Không commit file này lên Git!

```bash
cd terraform

# Tạo file terraform.tfvars (đã có trong .gitignore)
cat > terraform.tfvars <<EOF
db_password = "YourStrongPassword123!"
EOF
```

## 📦 Triển khai Infrastructure

### Bước 1: Khởi tạo Terraform

```bash
cd terraform
terraform init
```

### Bước 2: Xem trước các thay đổi

```bash
terraform plan
```

Lệnh này sẽ hiển thị:
- ✅ Những gì sẽ được tạo mới (màu xanh)
- ⚠️ Những gì sẽ bị xóa (màu đỏ)
- 🔄 Những gì sẽ được thay đổi (màu vàng)

### Bước 3: Áp dụng thay đổi

```bash
terraform apply

# Terraform sẽ hỏi xác nhận, gõ: yes
```

**Lưu ý:** Việc tạo các database có thể mất 10-15 phút!

### Bước 4: Lấy connection strings

Sau khi apply thành công:

```bash
# Xem outputs
terraform output

# Lấy connection string cụ thể (sẽ không hiển thị vì là sensitive)
terraform output -raw postgres_connection_string
terraform output -raw cosmos_connection_string
terraform output -raw redis_connection_string
```

## 🔐 Cấu hình GitHub Secrets

Sau khi Terraform deploy xong, cần cập nhật GitHub Secrets:

```bash
# 1. Lấy PostgreSQL FQDN
terraform output -raw postgres_fqdn

# 2. Lấy CosmosDB connection string
terraform output -raw cosmos_connection_string

# 3. Lấy Redis hostname và key
terraform output redis_hostname
terraform output -raw redis_primary_key
```

Sau đó vào GitHub: **Settings → Secrets → Actions** và cập nhật:

- `DB_PASSWORD`: Mật khẩu bạn đã đặt trong terraform.tfvars
- Các secrets khác như JWT_SECRET_KEY, MAPBOX_ACCESS_TOKEN, v.v.

## 🔍 Các Resource Được Tạo

Terraform sẽ tạo:

1. **Resource Group**: `rg-uitgo-prod`
2. **Virtual Network**: `vnet-uitgo-prod` (172.16.0.0/16)
3. **AKS Cluster**: `aks-uitgo-prod` (1 node B2s)
4. **Container Registry**: `acruitgoprod`
5. **PostgreSQL Flexible Server**: `psql-uitgo-prod` (B_Standard_B1ms)
   - ✅ **Firewall rule để cho phép Azure services**
6. **CosmosDB (MongoDB)**: `cosmos-uitgo-prod` (Serverless)
   - Databases: `uitgo_trips`, `uitgo_drivers`, `uitgo_payments`
7. **Redis Cache**: `redis-uitgo-prod` (C0 Basic)
   - ✅ **Firewall rule để cho phép Azure services**

## 🛡️ Firewall Configuration

**PostgreSQL và Redis đã được cấu hình:**

- ✅ Cho phép tất cả Azure services (IP: 0.0.0.0)
- ✅ AKS pod có thể kết nối đến databases
- ✅ Public access enabled (cần thiết cho Azure-to-Azure connections)

**Giải thích:**
- IP `0.0.0.0` trong Azure firewall có nghĩa đặc biệt: cho phép tất cả services TRONG Azure
- Đây KHÔNG phải là cho phép toàn bộ internet!
- Chỉ các resources trong Azure subscription của bạn mới truy cập được

## 🧪 Kiểm tra kết nối

Sau khi deploy, kiểm tra xem AKS có kết nối được database không:

```bash
# Lấy AKS credentials
az aks get-credentials --resource-group rg-uitgo-prod --name aks-uitgo-prod

# Test PostgreSQL từ một pod
kubectl run psql-test --rm -it --image=postgres:15 -- \
  psql "postgresql://postgresadmin:YourPassword@psql-uitgo-prod.postgres.database.azure.com:5432/mydb"

# Nếu kết nối thành công, bạn sẽ thấy: mydb=>
```

## 🗑️ Xóa Infrastructure (Cẩn thận!)

**Chỉ làm khi bạn chắc chắn muốn xóa TẤT CẢ resources:**

```bash
cd terraform
terraform destroy

# Terraform sẽ hỏi xác nhận, gõ: yes
```

## 💰 Ước tính chi phí

Với cấu hình hiện tại (Southeast Asia):

- AKS (1 node B2s): ~$30/tháng
- PostgreSQL (B1ms): ~$15/tháng
- CosmosDB (Serverless): ~$0.25/1M requests
- Redis (C0): ~$15/tháng
- ACR (Basic): ~$5/tháng

**Tổng: ~$65-70/tháng** (chưa tính data transfer)

## 🔧 Troubleshooting

### Lỗi: "Resource already exists"

Nếu bạn đã tạo resources thủ công trước đó:

```bash
# Import resource vào Terraform state
terraform import azurerm_postgresql_flexible_server.postgres /subscriptions/YOUR_SUB_ID/resourceGroups/rg-uitgo-prod/providers/Microsoft.DBforPostgreSQL/flexibleServers/psql-uitgo-prod
```

### Lỗi: "Connection timeout" từ AKS pod

```bash
# Kiểm tra firewall rules
az postgres flexible-server firewall-rule list \
  --name psql-uitgo-prod \
  --resource-group rg-uitgo-prod

# Phải có rule với start_ip=0.0.0.0 và end_ip=0.0.0.0
```

### Thay đổi mật khẩu database

```bash
# 1. Đổi password trong terraform.tfvars
# 2. Apply lại
terraform apply

# 3. Cập nhật GitHub Secret DB_PASSWORD
```

## 📚 Tham khảo

- [Azure PostgreSQL Flexible Server Pricing](https://azure.microsoft.com/en-us/pricing/details/postgresql/flexible-server/)
- [CosmosDB Serverless Pricing](https://azure.microsoft.com/en-us/pricing/details/cosmos-db/autoscale-provisioned/)
- [AKS Pricing Calculator](https://azure.microsoft.com/en-us/pricing/calculator/)
