resource "azurerm_resource_group" "rg" {
  name     = "rg-${var.prefix}-prod"
  location = var.location
}

# Đã đổi sang dải 172.16.0.0/16
resource "azurerm_virtual_network" "vnet" {
  name                = "vnet-${var.prefix}-prod"
  address_space       = ["172.16.0.0/16"] # <-- ĐÃ THAY ĐỔI
  location            = azurerm_resource_group.rg.location
  resource_group_name = azurerm_resource_group.rg.name
}

# Đã đổi sang dải 172.16.1.0/24
resource "azurerm_subnet" "aks_subnet" {
  name                 = "snet-aks-prod"
  resource_group_name  = azurerm_resource_group.rg.name
  virtual_network_name = azurerm_virtual_network.vnet.name
  address_prefixes     = ["172.16.1.0/24"] # <-- ĐÃ THAY ĐỔI
}

resource "azurerm_kubernetes_cluster" "aks" {
  name                = "aks-${var.prefix}-prod"
  location            = azurerm_resource_group.rg.location
  resource_group_name = azurerm_resource_group.rg.name
  dns_prefix          = "${var.prefix}-prod"

  default_node_pool {
    name           = "default"
    node_count     = 1
    vm_size        = "Standard_B2s"
    vnet_subnet_id = azurerm_subnet.aks_subnet.id
  }

  identity {
    type = "SystemAssigned"
  }
}