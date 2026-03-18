resource "azurerm_resource_group" "rg" {
  name     = "rg-rag-${var.environment}"
  location = var.location
}

module "network" {
  source              = "./modules/network"
  resource_group_name = azurerm_resource_group.rg.name
  location            = azurerm_resource_group.rg.location
  environment         = var.environment
}

module "ai_core" {
  source               = "./modules/ai_service"
  resource_group_name  = azurerm_resource_group.rg.name
  location             = azurerm_resource_group.rg.location
  environment          = var.environment
  openai_model         = var.openai_model_name
  openai_model_version = var.openai_model_version
  search_sku           = var.search_sku
  pe_subnet_id         = module.network.pe_subnet_id
  openai_dns_zone_id   = module.network.openai_dns_zone_id
}

module "compute" {
  source              = "./modules/compute"
  resource_group_name = azurerm_resource_group.rg.name
  location            = azurerm_resource_group.rg.location
  environment         = var.environment
  sku_name            = var.app_service_sku
  openai_endpoint     = module.ai_core.openai_endpoint
  app_subnet_id       = module.network.app_subnet_id
}