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

variable "management_allowed_cidrs" {
  description = "Danh sách CIDR được phép SSH vào subnet quản lý"
  type        = list(string)
  default     = ["203.0.113.10/32"]
}

variable "alert_emails" {
  description = "Danh sách email nhận cảnh báo Azure Monitor"
  type        = list(string)
  default     = ["security@example.com"]
}