# Azure Setup Scripts

## 🔍 Kiểm tra resources hiện có

```bash
bash scripts/check-azure-resources.sh
```

Script này sẽ show:
- Subscription hiện tại
- Tất cả resource groups
- Tất cả Container Registries (ACR)
- Tất cả AKS clusters
- Resources trong `uitgo-rg`

## 🚀 Tạo Azure Container Registry

```bash
bash scripts/create-acr.sh
```

Script này sẽ:
1. Tạo resource group `uitgo-rg` (nếu chưa có)
2. Tạo ACR tên `uitgoregistry`
3. Enable admin access
4. Show thông tin login

**Sau khi chạy script:**
```bash
# Test login
az acr login --name uitgoregistry

# Build và push image
docker build -t uitgoregistry.azurecr.io/userservice:v1.0 ./UserService
docker push uitgoregistry.azurecr.io/userservice:v1.0
```

## ⚙️ Customization

Nếu muốn dùng tên khác, edit `scripts/create-acr.sh`:

```bash
RESOURCE_GROUP="your-rg-name"
ACR_NAME="your-acr-name"
LOCATION="southeastasia"  # or "eastus", "westeurope", etc.
SKU="Basic"  # or "Standard", "Premium"
```

## 🔐 Setup GitHub Actions

Sau khi tạo ACR, setup GitHub secrets:

```bash
# 1. Tạo service principal
az ad sp create-for-rbac \
  --name "github-actions-uitgo" \
  --role contributor \
  --scopes /subscriptions/$(az account show --query id -o tsv)/resourceGroups/uitgo-rg \
  --sdk-auth

# 2. Copy JSON output → GitHub Settings → Secrets → AZURE_CREDENTIALS

# 3. Nếu ACR name khác "uitgoregistry"
# GitHub Settings → Secrets → ACR_NAME = "your-acr-name"
```

## 🎯 Enable deployment trong CI/CD

File `.github/workflows/ci-cd.yml` hiện tại **disable** các build/deploy jobs.

Để enable lại, remove `&& false` từ các dòng:

```yaml
# Before
if: github.ref == 'refs/heads/main' && false  # Disabled temporarily

# After
if: github.ref == 'refs/heads/main'
```

## ❌ Troubleshooting

### ACR login fail
```bash
# Check ACR exists
az acr list

# Check subscription
az account show

# Check permissions
az acr show --name uitgoregistry
```

### Resource group not found
```bash
# Create manually
az group create --name uitgo-rg --location southeastasia
```

### Permission denied
```bash
# Check your role
az role assignment list --assignee $(az account show --query user.name -o tsv)

# Need at least "Contributor" role on the resource group
```
