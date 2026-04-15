data "azurerm_client_config" "current" {}

locals {
  name_suffix = substr(replace(data.azurerm_client_config.current.subscription_id, "-", ""), 0, 6)
}

resource "azurerm_service_plan" "app" {
  name                = "asp-rag-${var.environment}"
  resource_group_name = var.resource_group_name
  location            = var.location
  os_type             = "Linux"
  sku_name            = var.sku_name
}

# backend on App Service with private endpoint, hosting the API and the frontend (Streamlit)
resource "azurerm_linux_web_app" "api" {
  name                      = "app-rag-${var.environment}-${local.name_suffix}"
  resource_group_name       = var.resource_group_name
  location                  = var.location
  service_plan_id           = azurerm_service_plan.app.id
  https_only                = true
  virtual_network_subnet_id = var.app_subnet_id

  identity {
    type = "SystemAssigned"
  }

  site_config {
    minimum_tls_version    = "1.2"
    always_on              = true
    vnet_route_all_enabled = true
    app_command_line       = "gunicorn -w 2 -k uvicorn.workers.UvicornWorker --timeout 180 --graceful-timeout 30 -b 0.0.0.0:8000 app.main:app" # Reduce memory pressure and allow longer AI requests

    application_stack {
      python_version = "3.11"
    }
  }

  app_settings = {
    "ENVIRONMENT"                         = var.environment
    "AZURE_OPENAI_ENDPOINT"               = var.openai_endpoint
    "AZURE_OPENAI_API_KEY"                = var.openai_key
    "AZURE_SEARCH_ENDPOINT"               = var.search_endpoint
    "AZURE_SEARCH_KEY"                    = var.search_key
    "CHAT_DEPLOYMENT"                     = var.chat_deployment
    "EMBEDDING_DEPLOYMENT"                = var.embedding_deployment
    "OPENAI_API_VERSION"                  = "2024-02-15-preview"
    "EVALUATOR_OPENAI_API_VERSION"        = "2024-02-15-preview"
    "AZURE_SEARCH_INDEX"                  = "manuals-index"
    "WEBSITES_PORT"                       = "8000"
    "WEBSITES_CONTAINER_START_TIME_LIMIT" = "1800"
    "WEBSITE_WARMUP_PATH"                 = "/healthz"
    "SCM_DO_BUILD_DURING_DEPLOYMENT"      = "true"
    "ENABLE_ORYX_BUILD"                   = "true"
    "WEBSITE_RUN_FROM_PACKAGE"            = "0"
  }
}

# frontend on App Service with private endpoint, hosting the Streamlit UI
resource "azurerm_linux_web_app" "frontend" {
  name                      = "app-rag-ui-${var.environment}-${local.name_suffix}"
  resource_group_name       = var.resource_group_name
  location                  = var.location
  service_plan_id           = azurerm_service_plan.app.id
  https_only                = true
  virtual_network_subnet_id = var.app_subnet_id

  identity {
    type = "SystemAssigned"
  }

  site_config {
    minimum_tls_version    = "1.2"
    always_on              = true
    vnet_route_all_enabled = true
    app_command_line       = "streamlit run frontend/ui.py --server.address 0.0.0.0 --server.port 8000"

    application_stack {
      python_version = "3.11"
    }
  }

  app_settings = {
    "ENVIRONMENT"                         = var.environment
    "API_BASE_URL"                        = "https://${azurerm_linux_web_app.api.default_hostname}"
    "WEBSITES_PORT"                       = "8000"
    "WEBSITES_CONTAINER_START_TIME_LIMIT" = "1800"
    "WEBSITE_WARMUP_PATH"                 = "/"
    "SCM_DO_BUILD_DURING_DEPLOYMENT"      = "true"
    "ENABLE_ORYX_BUILD"                   = "true"
    "WEBSITE_RUN_FROM_PACKAGE"            = "0"
  }
}
