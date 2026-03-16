resource "azurerm_cognitive_account" "openai" {
  name                = "cog-rag-openai-${var.environment}"
  location            = var.location
  resource_group_name = var.resource_group_name
  kind                = "OpenAI"
  sku_name            = "S0"
  public_network_access_enabled = false  # Disable public network access, only allow private endpoints
}

resource "azurerm_private_endpoint" "openai_pe" {
  name                = "pe-openai-${var.environment}"
  location            = var.location
  resource_group_name = var.resource_group_name
  subnet_id           = var.pe_subnet_id   # Put it in the PE subnet

  private_service_connection {
    name                           = "psc-openai"
    private_connection_resource_id = azurerm_cognitive_account.openai.id
    is_manual_connection           = false
    subresource_names              = ["account"]
  }

  # Register the private endpoint's NIC IP into the Private DNS Zone
  private_dns_zone_group {
    name                 = "openai-dns-zone-group"
    private_dns_zone_ids = [var.openai_dns_zone_id]
  }
}

resource "azurerm_cognitive_deployment" "model" {
  name                 = "chat-model"
  cognitive_account_id = azurerm_cognitive_account.openai.id
  sku {
    name = "Standard"
  }
  model {
    format  = "OpenAI"
    name    = var.openai_model
    version = "2024-05-13"
  }
}


resource "azurerm_search_service" "search" {
  name                = "srch-rag-${var.environment}"
  resource_group_name = var.resource_group_name
  location            = var.location
  sku                 = var.search_sku
}