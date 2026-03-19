# Azure Enterprise RAG Architecture

This document visualizes the Terraform-deployed architecture for the enterprise RAG demo and summarizes how requests flow through the system.

## Architecture Diagram

```mermaid
flowchart TB
    U[Enterprise User]

    subgraph Azure[Azure Subscription]
      subgraph RG[Resource Group: rg-rag-{env}]

        subgraph VNET[VNet: vnet-rag-{env}]
          APP_SNET[Subnet: snet-app<br/>10.0.1.0/24<br/>Delegated to Microsoft.Web/serverFarms]
          PE_SNET[Subnet: snet-private-endpoints<br/>10.0.2.0/24]
          DNS[Private DNS Zone<br/>privatelink.openai.azure.com]
        end

        PLAN[App Service Plan<br/>Linux]

        UI[Linux Web App<br/>Streamlit UI<br/>app-rag-ui-{env}-suffix]
        API[Linux Web App<br/>FastAPI RAG API<br/>app-rag-{env}-suffix]

        SEARCH[Azure AI Search<br/>srch-rag-{env}-suffix]

        subgraph AOAI_GRP[Azure OpenAI]
          AOAI[Cognitive Account OpenAI<br/>Public access disabled]
          CHAT[Deployment: chat-model<br/>Model: gpt-4o]
          EMB[Deployment: embedding-model<br/>Model: text-embedding-3-large]
        end

        PE_OPENAI[Private Endpoint<br/>pe-openai-{env}<br/>subresource: account]
      end
    end

    U -->|HTTPS| UI
    UI -->|API_BASE_URL /query| API

    API -->|Retriever vectors + metadata| SEARCH
    API -->|Prompt + context| CHAT
    API -->|Embeddings generation| EMB

    CHAT -. hosted on .-> AOAI
    EMB -. hosted on .-> AOAI

    PE_OPENAI --> AOAI
    PE_OPENAI --> PE_SNET
    DNS --> VNET
    PE_OPENAI --> DNS

    PLAN --> UI
    PLAN --> API
    APP_SNET --> UI
    APP_SNET --> API

    TF[Terraform modules<br/>network, ai_service, compute] -. provisions .-> VNET
    TF -. provisions .-> AOAI
    TF -. provisions .-> SEARCH
    TF -. provisions .-> PLAN
    TF -. provisions .-> UI
    TF -. provisions .-> API

    DEVPROD[Environment isolation<br/>dev and prod tfvars/tfbackend<br/>Different SKU and cost profile]
    DEVPROD -. controls .-> TF
```

## Short Architecture Explanation

- User access path: End users access the Streamlit frontend web app over HTTPS. The frontend sends queries to the FastAPI backend using its configured API base URL.
- RAG execution path: The backend retrieves relevant chunks from Azure AI Search and combines them with user prompts for the Azure OpenAI chat deployment. It also calls the embedding deployment for vector operations.
- Compute layout: Both frontend and backend are Linux App Services running on one App Service Plan and integrated with the application subnet in the VNet.
- Network and security controls: Azure OpenAI has public network access disabled and is reached through a private endpoint in a dedicated private-endpoint subnet, with private DNS zone resolution inside the VNet.
- Environment isolation: Separate backend and variable files allow dev and prod isolation, including different SKUs for cost and performance profiles.

## How To Visualize

- Open this file in VS Code and use Markdown Preview to render the Mermaid diagram.
- The same diagram can be copied into wiki pages, architecture docs, or PR descriptions that support Mermaid.