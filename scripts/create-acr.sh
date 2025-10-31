#!/bin/bash
# Script tạo Azure Container Registry

set -e

# Configuration
RESOURCE_GROUP="uitgo-rg"
ACR_NAME="uitgoregistry"
LOCATION="southeastasia"  # Change if needed
SKU="Basic"  # Basic, Standard, or Premium

echo "=================================="
echo "Creating Azure Container Registry"
echo "=================================="
echo "Resource Group: $RESOURCE_GROUP"
echo "ACR Name: $ACR_NAME"
echo "Location: $LOCATION"
echo "SKU: $SKU"
echo "=================================="
echo ""

# Check if resource group exists
echo "[1/4] Checking resource group..."
if ! az group show --name $RESOURCE_GROUP &>/dev/null; then
    echo "Resource group '$RESOURCE_GROUP' not found. Creating..."
    az group create --name $RESOURCE_GROUP --location $LOCATION
    echo "✅ Resource group created"
else
    echo "✅ Resource group exists"
fi

# Check if ACR already exists
echo ""
echo "[2/4] Checking if ACR exists..."
if az acr show --name $ACR_NAME --resource-group $RESOURCE_GROUP &>/dev/null; then
    echo "⚠️  ACR '$ACR_NAME' already exists!"
    az acr show --name $ACR_NAME --query "{Name:name, LoginServer:loginServer, ResourceGroup:resourceGroup}" -o table
    exit 0
fi

# Create ACR
echo ""
echo "[3/4] Creating ACR..."
az acr create \
  --resource-group $RESOURCE_GROUP \
  --name $ACR_NAME \
  --sku $SKU \
  --location $LOCATION

echo "✅ ACR created successfully"

# Enable admin access (optional, for testing)
echo ""
echo "[4/4] Enabling admin access..."
az acr update --name $ACR_NAME --admin-enabled true

echo ""
echo "=================================="
echo "✅ Setup Complete!"
echo "=================================="
echo ""
echo "ACR Details:"
az acr show --name $ACR_NAME --query "{Name:name, LoginServer:loginServer, Location:location}" -o table

echo ""
echo "Login Server: ${ACR_NAME}.azurecr.io"
echo ""
echo "Next steps:"
echo "1. Login to ACR:"
echo "   az acr login --name $ACR_NAME"
echo ""
echo "2. Get credentials (for GitHub secrets):"
echo "   az acr credential show --name $ACR_NAME"
echo ""
echo "3. Attach ACR to AKS (if you have AKS):"
echo "   az aks update --resource-group $RESOURCE_GROUP --name <aks-name> --attach-acr $ACR_NAME"
