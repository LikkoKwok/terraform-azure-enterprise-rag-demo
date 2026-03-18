variable "resource_group_name" {
  type = string
}

variable "openai_key" {
  type      = string
  sensitive = true
}

variable "chat_deployment" {
  type = string
}

variable "embedding_deployment" {
  type = string
}

variable "search_endpoint" {
  type = string
}

variable "search_key" {
  type      = string
  sensitive = true
}
variable "location" {
  type = string
}

variable "environment" {
  type = string
}

variable "sku_name" {
  type = string
}

variable "openai_endpoint" {
  type = string
}

variable "app_subnet_id" {
  type = string
}