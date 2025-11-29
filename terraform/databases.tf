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

  delegated_subnet_id           = azurerm_subnet.postgres_subnet.id
  private_dns_zone_id           = azurerm_private_dns_zone.postgres_dns.id
  
  # QUAN TRỌNG: PostgreSQL dùng VNet Injection nên phải TẮT public access
  public_network_access_enabled = false

  # Tắt các tính năng không cần thiết để tiết kiệm chi phí
  backup_retention_days        = 7
  geo_redundant_backup_enabled = false

  zone = "1"

  depends_on = [azurerm_private_dns_zone_virtual_network_link.postgres_dns_link]
}

# Database trong PostgreSQL server
resource "azurerm_postgresql_flexible_server_database" "postgres_db" {
  name      = "mydb"
  server_id = azurerm_postgresql_flexible_server.postgres.id
  charset   = "UTF8"
  collation = "en_US.utf8"
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

  # --- CẤU HÌNH FIX LỖI KẾT NỐI ---
  # Bật truy cập công khai để TripService/DriverService kết nối dễ dàng
  public_network_access_enabled     = true
  
  # Tắt bộ lọc VNet để tránh lỗi 400 Conflict và cho phép kết nối từ AKS
  is_virtual_network_filter_enabled = false

  consistency_policy {
    consistency_level = "Session"
  }

  geo_location {
    location          = azurerm_resource_group.rg.location
    failover_priority = 0
    zone_redundant    = false # Tắt Availability Zones để tránh lỗi capacity
  }
  
  # MongoDB capabilities
  capabilities {
    name = "EnableMongo"
  }

  capabilities {
    name = "EnableServerless" # Serverless để tiết kiệm chi phí
  }

  # LƯU Ý: Đã xóa block virtual_network_rule để tránh xung đột
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

  # Cho phép truy cập từ Azure (Basic tier cần public access)
  public_network_access_enabled = true

  redis_configuration {
    # Không cần maxmemory-policy cho Basic tier
  }
}

# Firewall Rule cho Redis (QUAN TRỌNG: Mở để AKS kết nối được vào Redis Public)
resource "azurerm_redis_firewall_rule" "allow_all" {
  name                = "AllowAll"
  redis_cache_name    = azurerm_redis_cache.redis.name
  resource_group_name = azurerm_resource_group.rg.name
  start_ip            = "0.0.0.0"
  end_ip              = "255.255.255.255"
}