#!/bin/bash
# Script kiểm tra resources Azure hiện có

echo "=================================="
echo "Checking Azure Resources"
echo "=================================="

echo ""
echo "1. Current subscription:"
az account show --query "{Name:name, ID:id, State:state}" -o table

echo ""
echo "2. All resource groups:"
az group list --query "[].{Name:name, Location:location}" -o table

echo ""
echo "3. Container Registries (ACR):"
az acr list --query "[].{Name:name, ResourceGroup:resourceGroup, LoginServer:loginServer}" -o table

echo ""
echo "4. AKS Clusters:"
az aks list --query "[].{Name:name, ResourceGroup:resourceGroup, Location:location}" -o table

echo ""
echo "5. Resources in 'uitgo-rg' (if exists):"
az resource list --resource-group uitgo-rg --query "[].{Name:name, Type:type}" -o table 2>/dev/null || echo "Resource group 'uitgo-rg' not found"

echo ""
echo "=================================="
echo "Done!"
echo "=================================="
