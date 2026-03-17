variable "environment" {
	type = string
}

variable "location" {
	type    = string
	default = "East Asia"
}

variable "app_service_sku" {
	type = string
}

variable "openai_model_name" {
	type = string
}

variable "search_sku" {
	type = string
}