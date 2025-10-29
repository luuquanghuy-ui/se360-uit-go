terraform {
  required_providers {
    azurerm = {
      source  = "hashicorp/azurerm"
      version = ">= 4.0"
    }
  }
}

# --- THÊM PHẦN NÀY ---
  backend "azurerm" {
    resource_group_name  = "rg-uitgo-tfstate"    # Tên RG bạn đã tạo
    storage_account_name = "stuitgotfstate"      # Tên Storage Account bạn đã tạo
    container_name       = "tfstate"             # Tên Container bạn đã tạo
    key                  = "prod.terraform.tfstate" # Tên file state
  }
  # --- HẾT PHẦN THÊM ---


provider "azurerm" {
  features {}
}