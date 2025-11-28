variable "prefix" {
  description = "Tiền tố cho tất cả tài nguyên (ví dụ: uitgo)"
  type        = string
  default     = "uitgohuy"
}

variable "location" {
  description = "Khu vực Azure (ví dụ: East US, Southeast Asia)"
  type        = string
  default     = "Malaysia West"
}

variable "db_password" {
  description = "Mật khẩu cho PostgreSQL và MongoDB (nên set qua TF_VAR_db_password hoặc terraform.tfvars)"
  type        = string
  sensitive   = true
}