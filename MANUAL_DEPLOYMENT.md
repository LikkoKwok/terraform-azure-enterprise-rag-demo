# Manual Azure App Deployment (No CI/CD)

This runbook updates the application code on Azure App Service manually for this repository.

It deploys both web apps created by Terraform:
- Backend FastAPI app (`app-rag-<env>-<suffix>`)
- Frontend Streamlit app (`app-rag-ui-<env>-<suffix>`)

Both apps run from the same repo package, so deploy the same zip to both.

## 1. Prerequisites

- Azure CLI installed and logged in.
- You are in the repository root.
- Terraform infrastructure for the target environment already exists.

## 2. Set Target Environment Variables

```bash
cd /workspaces/terraform-azure-enterprise-rag-demo

# Set deployment environment: dev or prod
ENV=dev
RG="rg-rag-${ENV}"
```

Optional: ensure correct subscription.

```bash
az account show --query "{name:name,id:id}" -o table
# az account set --subscription "<subscription-id-or-name>"
```

## 3. Discover App Service Names

The app names include a generated suffix, so resolve them from Azure:

```bash
BACKEND_APP=$(az webapp list -g "$RG" --query "[?starts_with(name, 'app-rag-${ENV}-') && !starts_with(name, 'app-rag-ui-')].name | [0]" -o tsv)
FRONTEND_APP=$(az webapp list -g "$RG" --query "[?starts_with(name, 'app-rag-ui-${ENV}-')].name | [0]" -o tsv)

echo "Backend:  $BACKEND_APP"
echo "Frontend: $FRONTEND_APP"
```

If either value is empty, verify `ENV` and resource group.

## 4. Build Deployment Zip

Create a clean package from repo root:

```bash
rm -f deploy.zip
zip -r deploy.zip . \
  -x ".git/*" \
     ".venv/*" \
     ".terraform/*" \
     "artifacts/*" \
     "**/__pycache__/*" \
     "*.pyc"
```

## 5. Deploy to Backend and Frontend Apps

```bash
az webapp deploy --resource-group "$RG" --name "$BACKEND_APP" --src-path deploy.zip --type zip
az webapp deploy --resource-group "$RG" --name "$FRONTEND_APP" --src-path deploy.zip --type zip
```

## 6. Restart Apps (Recommended)

```bash
az webapp restart --resource-group "$RG" --name "$BACKEND_APP"
az webapp restart --resource-group "$RG" --name "$FRONTEND_APP"
```

## 7. Smoke Test

Get hostnames:

```bash
BACKEND_HOST=$(az webapp show -g "$RG" -n "$BACKEND_APP" --query defaultHostName -o tsv)
FRONTEND_HOST=$(az webapp show -g "$RG" -n "$FRONTEND_APP" --query defaultHostName -o tsv)

echo "https://${BACKEND_HOST}"
echo "https://${FRONTEND_HOST}"
```

Check backend health and UI:

```bash
curl -fsS "https://${BACKEND_HOST}/healthz"
# Open UI in browser
"$BROWSER" "https://${FRONTEND_HOST}"
```

## 8. Verify Ingestion Endpoint

After opening the UI:
- Upload one PDF.
- Click **Ingest PDFs to Azure AI Search**.
- Confirm success message (chunks indexed).
- Ask a question in chat and verify response uses newly uploaded content.

## 9. Rollback (Manual)

If deployment fails and you need a fast rollback:

1. Checkout previous known-good commit locally.
2. Rebuild `deploy.zip`.
3. Re-run step 5 and step 6.

## Notes

- This repo relies on App Service build during deployment (`SCM_DO_BUILD_DURING_DEPLOYMENT=true` and `ENABLE_ORYX_BUILD=true`).
- Requirements were updated for ingestion (`pypdf`, `langchain-text-splitters`, `python-multipart`), so full redeploy is required.
