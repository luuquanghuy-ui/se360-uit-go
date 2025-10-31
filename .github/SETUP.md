# GitHub Actions Setup Guide

## Required Secrets

Go to **Settings** → **Secrets and variables** → **Actions** → **New repository secret**

### 1. AZURE_CREDENTIALS

Login credentials for Azure CLI:

```bash
# Create service principal
az ad sp create-for-rbac \
  --name "github-actions-uitgo" \
  --role contributor \
  --scopes /subscriptions/{subscription-id}/resourceGroups/uitgo-rg \
  --sdk-auth
```

Copy the entire JSON output and add as secret `AZURE_CREDENTIALS`:

```json
{
  "clientId": "...",
  "clientSecret": "...",
  "subscriptionId": "...",
  "tenantId": "...",
  "activeDirectoryEndpointUrl": "https://login.microsoftonline.com",
  "resourceManagerEndpointUrl": "https://management.azure.com/",
  "activeDirectoryGraphResourceId": "https://graph.windows.net/",
  "sqlManagementEndpointUrl": "https://management.core.windows.net:8443/",
  "galleryEndpointUrl": "https://gallery.azure.com/",
  "managementEndpointUrl": "https://management.core.windows.net/"
}
```

### 2. ACR_NAME (Optional)

Azure Container Registry name. Default: `uitgoregistry`

```
ACR_NAME=your-acr-name
```

**To find your ACR name:**
```bash
az acr list --resource-group uitgo-rg --query "[].name" -o tsv
```

If you don't have ACR, create one:
```bash
az acr create \
  --resource-group uitgo-rg \
  --name uitgoregistry \
  --sku Basic
```

### 3. Check Existing Resources

```bash
# List all resources in resource group
az resource list --resource-group uitgo-rg --output table

# Check ACR
az acr list --resource-group uitgo-rg

# Check AKS
az aks list --resource-group uitgo-rg
```

## Workflow Configuration

Update `.github/workflows/ci-cd.yml` env section if needed:

```yaml
env:
  ACR_NAME: ${{ secrets.ACR_NAME || 'uitgoregistry' }}
  NAMESPACE: uitgo
  RESOURCE_GROUP: uitgo-rg        # Change if different
  AKS_CLUSTER: uitgo-aks-cluster  # Change if different
```

## Testing the Workflow

1. **Test without deploying:**
   - Create a PR to `main` branch
   - Only tests will run

2. **Full deployment:**
   - Push to `main` branch
   - Full CI/CD pipeline runs

3. **Manual trigger:**
   - Go to **Actions** → **Run Tests Only** → **Run workflow**

## Troubleshooting

### Error: ACR not found
```bash
# Check subscription
az account show

# List all ACRs
az acr list --output table

# Create if missing
az acr create --resource-group uitgo-rg --name uitgoregistry --sku Basic
```

### Error: AKS not found
```bash
# List AKS clusters
az aks list --output table

# Get credentials
az aks get-credentials --resource-group uitgo-rg --name uitgo-aks-cluster
```

### Error: Permission denied
```bash
# Check service principal permissions
az role assignment list --assignee {clientId}

# Grant ACR pull permission to AKS
az aks update \
  --resource-group uitgo-rg \
  --name uitgo-aks-cluster \
  --attach-acr uitgoregistry
```

### Tests fail
```bash
# Run tests locally
cd tests
pytest test_userservice.py -v

# Check dependencies
pip install -r requirements.txt
```

## Disable Auto-Deploy

If you only want to run tests without deploying:

1. Comment out the `deploy` and `smoke-test` jobs in `.github/workflows/ci-cd.yml`
2. Or change the condition:
   ```yaml
   if: github.ref == 'refs/heads/main' && contains(github.event.head_commit.message, '[deploy]')
   ```

Then only commits with `[deploy]` in message will trigger deployment.
