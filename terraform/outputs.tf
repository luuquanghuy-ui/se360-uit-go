output "acr_login_server" {
  description = "The ACR login server (e.g., acruitgoprod.azurecr.io)"
  value       = azurerm_container_registry.acr.login_server
}

output "acr_name" {
  description = "The name of the Azure Container Registry"
  value       = azurerm_container_registry.acr.name
}

output "aks_kubelet_object_id" {
  description = "Object ID of the AKS kubelet identity used to pull images from ACR"
  value       = azurerm_kubernetes_cluster.aks.kubelet_identity[0].object_id
}
