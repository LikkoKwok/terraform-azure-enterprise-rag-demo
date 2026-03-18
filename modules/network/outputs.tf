output "app_subnet_id" { value = azurerm_subnet.app_snet.id }

output "pe_subnet_id" { value = azurerm_subnet.pe_snet.id }

output "openai_dns_zone_id" { value = azurerm_private_dns_zone.openai.id }