resource "azurerm_virtual_network" "vnet" {
  name                = "vnet-rag-${var.environment}"
  address_space       = ["10.0.0.0/16"]
  location            = var.location
  resource_group_name = var.resource_group_name
}

# subnet A: delegated to App Service
resource "azurerm_subnet" "app_snet" {
  name                 = "snet-app"
  resource_group_name  = var.resource_group_name
  virtual_network_name = azurerm_virtual_network.vnet.name
  address_prefixes     = ["10.0.1.0/24"]

  delegation {
    name = "app-delegation"
    service_delegation {
      name    = "Microsoft.Web/serverFarms"
      actions = ["Microsoft.Network/virtualNetworks/subnets/action"]
    }
  }
}

# subnet B: for Private Endpoints (where OpenAI/Search private IPs are hosted)
resource "azurerm_subnet" "pe_snet" {
  name                 = "snet-private-endpoints"
  resource_group_name  = var.resource_group_name
  virtual_network_name = azurerm_virtual_network.vnet.name
  address_prefixes     = ["10.0.2.0/24"]
}

# Private DNS Zone for Azure OpenAI — required so the private endpoint FQDN resolves to the private IP
resource "azurerm_private_dns_zone" "openai" {
  name                = "privatelink.openai.azure.com"
  resource_group_name = var.resource_group_name
}

# Link the DNS zone to the VNet so resources inside the VNet use it automatically
resource "azurerm_private_dns_zone_virtual_network_link" "openai" {
  name                  = "vnetlink-openai-${var.environment}"
  resource_group_name   = var.resource_group_name
  private_dns_zone_name = azurerm_private_dns_zone.openai.name
  virtual_network_id    = azurerm_virtual_network.vnet.id
  registration_enabled  = false
}