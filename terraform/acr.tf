resource "azurerm_container_registry" "acr" {
  name                = "acruithuykhoigo" 
  resource_group_name = azurerm_resource_group.rg.name
  location            = azurerm_resource_group.rg.location
  sku                 = "Basic" # Dùng "Basic" cho tiết kiệm
  admin_enabled       = true    
}

# Cấp quyền cho cụm AKS để nó có thể KÉO (pull) image từ ACR
resource "azurerm_role_assignment" "aks_pull_acr" {
  scope                = azurerm_container_registry.acr.id
  role_definition_name = "AcrPull"
  # Sử dụng kubelet identity của AKS để kéo image từ ACR 
  principal_id         = azurerm_kubernetes_cluster.aks.kubelet_identity[0].object_id
}