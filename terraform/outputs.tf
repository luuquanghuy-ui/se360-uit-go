output "acr_login_server" {
  description = "The ACR login server (e.g., acruithuykhoigo.azurecr.io)"
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

# Database outputs
output "postgres_fqdn" {
  description = "PostgreSQL server FQDN"
  value       = azurerm_postgresql_flexible_server.postgres.fqdn
}

output "postgres_connection_string" {
  description = "PostgreSQL connection string (dùng trong K8s secrets)"
  value       = "postgresql+asyncpg://postgresadmin:${var.db_password}@${azurerm_postgresql_flexible_server.postgres.fqdn}:5432/mydb"
  sensitive   = true
}

output "cosmos_connection_string" {
  description = "CosmosDB (MongoDB) connection string"
  value       = azurerm_cosmosdb_account.cosmos.primary_mongodb_connection_string
  sensitive   = true
}

output "redis_hostname" {
  description = "Redis cache hostname"
  value       = azurerm_redis_cache.redis.hostname
}

output "redis_primary_key" {
  description = "Redis primary access key"
  value       = azurerm_redis_cache.redis.primary_access_key
  sensitive   = true
}

output "redis_connection_string" {
  description = "Redis connection string"
  value       = "redis://:${azurerm_redis_cache.redis.primary_access_key}@${azurerm_redis_cache.redis.hostname}:6380?ssl=true"
  sensitive   = true
}
