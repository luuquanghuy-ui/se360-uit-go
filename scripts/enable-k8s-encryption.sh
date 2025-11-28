#!/usr/bin/env bash
set -euo pipefail

# This script enables AKS secret encryption at rest by turning on
# secrets-encryption (with CMK) and host-based encryption if available.
# Required environment variables:
#   RESOURCE_GROUP  - Azure resource group chứa AKS
#   CLUSTER_NAME    - Tên AKS cluster
# Optional:
#   KEY_VAULT_KEY_ID - Azure Key Vault key ID dùng để mã hóa (nếu bỏ trống sẽ dùng Microsoft-managed key)

if [[ -z "${RESOURCE_GROUP:-}" || -z "${CLUSTER_NAME:-}" ]]; then
  echo "ERROR: RESOURCE_GROUP và CLUSTER_NAME phải được set." >&2
  exit 1
fi

echo "🔐 Bật mã hóa secrets cho AKS cluster ${CLUSTER_NAME}..."

if [[ -n "${KEY_VAULT_KEY_ID:-}" ]]; then
  az aks update \
    --resource-group "${RESOURCE_GROUP}" \
    --name "${CLUSTER_NAME}" \
    --enable-secret-rotation \
    --enable-secrets-encryption \
    --encryption-key-url "${KEY_VAULT_KEY_ID}" \
    --yes
else
  az aks update \
    --resource-group "${RESOURCE_GROUP}" \
    --name "${CLUSTER_NAME}" \
    --enable-secret-rotation \
    --enable-secrets-encryption \
    --yes
fi

echo "🔒 Bật host encryption cho nodepool..."
az aks nodepool update \
  --resource-group "${RESOURCE_GROUP}" \
  --cluster-name "${CLUSTER_NAME}" \
  --name default \
  --enable-encryption-at-host \
  --yes

echo "✅ Hoàn tất! Kiểm tra trạng thái:"
az aks show \
  --resource-group "${RESOURCE_GROUP}" \
  --name "${CLUSTER_NAME}" \
  --query "securityProfile" -o yaml

cat <<'EOF'
Verification checklist:
- securityProfile.secretsEncryption.status == "Enabled"
- securityProfile.secretsEncryption.keyVaultProperties populated (nếu dùng CMK)
- Node pool default: enableEncryptionAtHost = true
EOF

