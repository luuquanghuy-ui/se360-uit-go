# 1. Resource Group chính cho ứng dụng
resource "azurerm_resource_group" "rg" {
  name     = "rg-${var.prefix}-prod"
  location = var.location
}

# 2. Mạng ảo (VNet)
resource "azurerm_virtual_network" "vnet" {
  name                = "vnet-${var.prefix}-prod"
  address_space       = ["10.0.0.0/16"]
  location            = azurerm_resource_group.rg.location
  resource_group_name = azurerm_resource_group.rg.name
}

# 3. Subnet cho cụm AKS
resource "azurerm_subnet" "aks_subnet" {
  name                 = "snet-aks-prod"
  resource_group_name  = azurerm_resource_group.rg.name
  virtual_network_name = azurerm_virtual_network.vnet.name
  address_prefixes     = ["10.0.1.0/24"]
}

# 4. Cụm AKS (Azure Kubernetes Service)
resource "azurerm_kubernetes_cluster" "aks" {
  name                = "aks-${var.prefix}-prod"
  location            = azurerm_resource_group.rg.location
  resource_group_name = azurerm_resource_group.rg.name
  dns_prefix          = "${var.prefix}-prod"

  default_node_pool {
    name       = "default"
    node_count = 1
    vm_size    = "Standard_B2s" # Dùng size nhỏ để tiết kiệm chi phí
    vnet_subnet_id = azurerm_subnet.aks_subnet.id
  }

  identity {
    type = "SystemAssigned"
  }
}