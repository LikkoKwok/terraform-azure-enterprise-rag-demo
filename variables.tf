variable "environment" {
  type = string
}

variable "location" {
  type    = string
  default = "East US"
}

variable "app_service_sku" {
  type = string
}

variable "openai_model_name" {
  type = string
}

variable "openai_model_version" {
  type = string
}

variable "search_sku" {
  type = string
}