terraform {
  required_providers {
    azurerm = {
      source  = "hashicorp/azurerm"
      version = "~> 3.0"
    }
  }
  backend "azurerm" {} # inject .tfbackend file when init
}

provider "azurerm" {
  features {}
}