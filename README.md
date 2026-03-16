## Terraform Azure Enterprise Grade RAG Architecture

## Project Scenario
This project is designed to build an automated enterprise **RAG (Retrieval-Augmented Generation)** knowledge base on Azure.
Employees can upload hundreds of PDF technical manuals and use AI for semantic search and question answering.

## Architecture Highlights
- **Multi-environment management:** Uses `.tfvars` and `.tfbackend` files to isolate Dev and Prod environments.
- **Cost optimization:** Dev can run on lower-cost tiers and smaller models, while Prod can use higher tiers and stronger models.
- **Production-ready engineering:** Structured with reusable modules and environment-specific configuration.
- **Security-first design:**

    - **Managed Identity for workload auth:** The Linux Web App uses `SystemAssigned` identity so services can authenticate without embedding credentials.
    - **No hardcoded secrets in IaC:** Terraform code and app settings avoid API keys and rely on identity-based access patterns.
    - **Public access disabled on Azure OpenAI:** `public_network_access_enabled = false` is set on the Cognitive Account, reducing internet exposure.
    - **Private connectivity for Azure OpenAI:** A private endpoint is provisioned in a dedicated private-endpoint subnet.
    - **Network segmentation by role:** The VNet separates App Service integration subnet and private-endpoint subnet to reduce lateral movement risk.
    - **Forced VNet egress path:** `vnet_route_all_enabled = true` ensures outbound traffic follows VNet routing controls.
    - **Transport hardening on app ingress:** The Web App enforces `https_only = true` with `minimum_tls_version = "1.2"`.
    - **Environment isolation for blast-radius control:** Separate backend and variable files support isolated Dev/Prod deployments and states.

## Recommended Next Security Hardening
- Add private endpoint and private DNS integration for Azure AI Search to align with the OpenAI private-access model.
- Apply App Service access restrictions and disable public ingress when fronted by private networking.
- Add NSGs/UDRs and centralized diagnostics (Log Analytics + Defender for Cloud) for stronger network governance and auditing.
- Use customer-managed keys and key rotation policies where compliance requires stronger encryption controls.

---

## Prerequisites
1. **Azure CLI:** Logged in and authorized for your target subscription.
2. **Terraform:** Version 1.5.0 or later.
3. **State Storage:** An existing Azure Storage Account for remote `.tfstate` backend.

---

## Quick Start

## 1. Initialize Terraform (Dev mode)
```bash
terraform init -backend-config=environment/dev.tfbackend
```

## 2. Preview changes
```bash
terraform plan -var-file=environment/dev.tfvars
```

## 3. Apply infrastructure
```bash
terraform apply -var-file=environment/dev.tfvars
```
