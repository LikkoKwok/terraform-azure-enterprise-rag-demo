output "openai_endpoint" {
  value = azurerm_cognitive_account.openai.endpoint
}

output "openai_account_id" {
  value = azurerm_cognitive_account.openai.id
}

output "chat_deployment_name" {
  value = azurerm_cognitive_deployment.model.name
}

output "embedding_deployment_name" {
  value = azurerm_cognitive_deployment.embedding.name
}

output "search_service_name" {
  value = azurerm_search_service.search.name
}

output "search_service_id" {
  value = azurerm_search_service.search.id
}

output "search_endpoint" {
  value = "https://${azurerm_search_service.search.name}.search.windows.net"
}

output "search_primary_key" {
  value     = azurerm_search_service.search.primary_key
  sensitive = true
}

output "openai_primary_key" {
  value     = azurerm_cognitive_account.openai.primary_access_key
  sensitive = true
}

output "search_resource_group" {
  value = var.resource_group_name
}
