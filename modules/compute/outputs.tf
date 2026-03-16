output "web_app_name" {
  value = azurerm_linux_web_app.api.name
}

output "web_app_default_hostname" {
  value = azurerm_linux_web_app.api.default_hostname
}

output "web_app_principal_id" {
  value = azurerm_linux_web_app.api.identity[0].principal_id
}