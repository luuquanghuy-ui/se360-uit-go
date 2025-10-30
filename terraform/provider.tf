terraform {
  required_providers {
    azurerm = {
      source  = "hashicorp/azurerm"
      version = ">= 4.0" # Hoặc ">= 3.0"
    }
  }

  # --- KHỐI BACKEND PHẢI NẰM BÊN TRONG KHỐI TERRAFORM ---
  backend "azurerm" {
    resource_group_name  = "rg-uitgo-tfstate"
    storage_account_name = "stuitgotfstate"
    container_name       = "tfstate"
    key                  = "prod.terraform.tfstate"
  }
  # --- HẾT ---
}

provider "azurerm" {
  features {}
  subscription_id = "d8ece151-084a-418c-a446-0ff133a2d388"
}