terraform {
  required_providers {
    azurerm = {
      source  = "hashicorp/azurerm"
      version = ">= 4.0" # Phiên bản provider Azurerm tối thiểu
    }
  }

  # KHỐI BACKEND PHẢI NẰM BÊN TRONG KHỐI TERRAFORM
  backend "azurerm" {
    resource_group_name  = "rg-uitgo-tfstate"      # Tên resource group chứa storage
    storage_account_name = "stuitgotfstate"        # Tên storage account lưu state
    container_name       = "tfstate"               # Tên container lưu file state
    key                  = "prod.terraform.tfstate" # Đường dẫn file state
  }
}

provider "azurerm" {
  features {}
  subscription_id = "d8ece151-084a-418c-a446-0ff133a2d388" # ID của subscription Azure
}
