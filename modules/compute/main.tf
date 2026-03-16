resource "azurerm_service_plan" "app" {
  name                = "asp-rag-${var.environment}"
  resource_group_name = var.resource_group_name
  location            = var.location
  os_type             = "Linux"
  sku_name            = var.sku_name
}

resource "azurerm_linux_web_app" "api" {
  name                = "app-rag-${var.environment}"
  resource_group_name = var.resource_group_name
  location            = var.location
  service_plan_id     = azurerm_service_plan.app.id
  https_only          = true
  virtual_network_subnet_id = var.app_subnet_id

  identity {
    type = "SystemAssigned"
  }

  site_config {
    minimum_tls_version = "1.2"
    always_on           = var.environment == "prod"  #  Only enable always on If environment is prod
    vnet_route_all_enabled = true     # Ensure all traffic goes through VNet, not just private traffic

    application_stack {
      python_version = "3.11"
    }
  }

  app_settings = {
    "ENVIRONMENT"              = var.environment
    "OPENAI_ENDPOINT"          = var.openai_endpoint
    "WEBSITE_RUN_FROM_PACKAGE" = "1"
  }
}
