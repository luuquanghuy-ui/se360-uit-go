provider "azurerm" {
  # --- THÊM KHỐI NÀY VÀO ĐÂY ---
  features {
    resource_group {
      prevent_deletion_if_contains_resources = false
    }
  }
  # ------------------------------

  subscription_id = "152428c8-7979-4fd1-be70-0c993c811514"
}