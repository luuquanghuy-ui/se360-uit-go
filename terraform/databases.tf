# ================================================
# Private DNS Zone cho PostgreSQL (BẮT BUỘC cho VNet Integration)
# ================================================
resource "azurerm_private_dns_zone" "postgres_dns" {
  name                = "private.postgres.database.azure.com"
  resource_group_name = azurerm_resource_group.rg.name
}

# Link DNS Zone với VNet
resource "azurerm_private_dns_zone_virtual_network_link" "postgres_dns_link" {
  name                  = "postgres-dns-link"
  resource_group_name   = azurerm_resource_group.rg.name
  private_dns_zone_name = azurerm_private_dns_zone.postgres_dns.name
  virtual_network_id    = azurerm_virtual_network.vnet.id
}

# ================================================
# PostgreSQL Flexible Server (cho UserService)
# ================================================
resource "azurerm_postgresql_flexible_server" "postgres" {
  name                = "psql-${var.prefix}-prod"
  resource_group_name = azurerm_resource_group.rg.name
  location            = azurerm_resource_group.rg.location

  administrator_login    = "postgresadmin"
  administrator_password = var.db_password # Sẽ định nghĩa trong variables.tf

  sku_name   = "B_Standard_B1ms" # Basic tier, rẻ nhất
  version    = "15"
  storage_mb = 32768 # 32 GB

  # --- Public access enabled (for Azure CNI compatibility) ---
  public_network_access_enabled = true # Đã enable trên Azure Portal
  # VNet integration bị xóa vì conflict với public access
  # --- HẾT THAY ĐỔI ---

  # Không cần depends_on nữa

  # Tắt các tính năng không cần thiết để tiết kiệm chi phí
  backup_retention_days        = 7
  geo_redundant_backup_enabled = false

  zone = "1"
}

# Database trong PostgreSQL server
resource "azurerm_postgresql_flexible_server_database" "postgres_db" {
  name      = "mydb"
  server_id = azurerm_postgresql_flexible_server.postgres.id
  charset   = "UTF8"
  collation = "en_US.utf8"
}

# ================================================
# FIREWALL RULES: Cho phép tất cả IPs (test mode)
# ================================================
resource "azurerm_postgresql_flexible_server_firewall_rule" "allow_all" {
  name             = "AllowAll"
  server_id        = azurerm_postgresql_flexible_server.postgres.id
  start_ip_address = "0.0.0.0"
  end_ip_address   = "255.255.255.255"
}

# ================================================
# CosmosDB (MongoDB API) - cho các services khác
# ================================================
resource "azurerm_cosmosdb_account" "cosmos" {
  name                = "cosmos-${var.prefix}-prod"
  location            = azurerm_resource_group.rg.location
  resource_group_name = azurerm_resource_group.rg.name
  offer_type          = "Standard"
  kind                = "MongoDB"

  consistency_policy {
    consistency_level = "Session"
  }

  geo_location {
    location          = azurerm_resource_group.rg.location
    failover_priority = 0
    zone_redundant    = false  # Tắt Availability Zones để tránh lỗi capacity
  }

  # Cho phép truy cập từ Azure services
  public_network_access_enabled     = true
  is_virtual_network_filter_enabled = false

  # MongoDB capabilities
  capabilities {
    name = "EnableMongo"
  }

  capabilities {
    name = "EnableServerless" # Serverless để tiết kiệm chi phí
  }
}

# Cosmos databases cho từng service
resource "azurerm_cosmosdb_mongo_database" "trips_db" {
  name                = "uitgo_trips"
  resource_group_name = azurerm_resource_group.rg.name
  account_name        = azurerm_cosmosdb_account.cosmos.name
}

resource "azurerm_cosmosdb_mongo_database" "drivers_db" {
  name                = "uitgo_drivers"
  resource_group_name = azurerm_resource_group.rg.name
  account_name        = azurerm_cosmosdb_account.cosmos.name
}

resource "azurerm_cosmosdb_mongo_database" "payments_db" {
  name                = "uitgo_payments"
  resource_group_name = azurerm_resource_group.rg.name
  account_name        = azurerm_cosmosdb_account.cosmos.name
}

# ================================================
# Azure Cache for Redis (cho LocationService)
# ================================================
resource "azurerm_redis_cache" "redis" {
  name                = "redis-${var.prefix}-prod"
  location            = azurerm_resource_group.rg.location
  resource_group_name = azurerm_resource_group.rg.name

  capacity            = 0 # C0 = 250 MB (rẻ nhất)
  family              = "C"
  sku_name            = "Basic"
  minimum_tls_version = "1.2"

  # Cho phép truy cập từ Azure
  public_network_access_enabled = true

  redis_configuration {
    # Không cần maxmemory-policy cho Basic tier
  }
}

# Firewall rule cho Redis (cho phép Azure services)
resource "azurerm_redis_firewall_rule" "allow_azure_services" {
  name                = "AllowAzureServices"
  redis_cache_name    = azurerm_redis_cache.redis.name
  resource_group_name = azurerm_resource_group.rg.name
  start_ip            = "0.0.0.0"
  end_ip              = "0.0.0.0"
}
