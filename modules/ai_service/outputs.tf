output "openai_endpoint" {
  value = azurerm_cognitive_account.openai.endpoint
}

output "openai_account_id" {
  value = azurerm_cognitive_account.openai.id
}

output "search_service_name" {
  value = azurerm_search_service.search.name
}

output "search_service_id" {
  value = azurerm_search_service.search.id
}
