# CI/CD and DevOps Guide

This repository is structured for multi-environment Terraform delivery on Azure. The recommended model is a GitOps-style workflow with automated validation for Dev and a controlled promotion path into Prod.

## Delivery Workflow

1. Pull request to `main`
- Run `terraform fmt -check -recursive`.
- Run `terraform init -backend=false`.
- Run `terraform validate`.
- Run `terraform plan` for Dev using `environment/dev.tfvars`.
- Publish the plan output as a build artifact for review.

2. Merge to `main`
- Re-run validation.
- Apply the reviewed plan to Dev.
- Run smoke tests against the deployed Dev environment.

3. Promote to Prod
- Require manual approval through protected environments.
- Generate a fresh Prod plan using `environment/prod.tfvars`.
- Apply to Prod only after approval and policy checks pass.

## Branch and Environment Strategy

- Keep `main` as the deployment branch.
- Use short-lived feature branches for infrastructure changes.
- Protect `main` with required checks and at least one reviewer.
- Configure separate GitHub Environments for `dev` and `prod`.
- Store environment-specific credentials and approval rules separately.

## Identity and Secret Handling

- Prefer GitHub Actions OpenID Connect (OIDC) to Azure over long-lived client secrets.
- Use least-privilege role assignments per environment.
- Do not store secrets in `.tfvars` files.
- Use GitHub environment secrets and Azure Key Vault where needed.

## Terraform State and Safety Controls

- Keep separate remote backends for Dev and Prod.
- Commit only `environment/*.tfbackend.example` templates, never real backend files.
- For local runs, create `environment/dev.tfbackend` or `environment/prod.tfbackend` from the examples.
- For CI runs, generate backend config from GitHub Environment secrets.
- Enable blob versioning and state locking on the backend storage account.
- Use saved plan files with `-out` and apply only those plans in automation.
- Add `-lock-timeout=5m` in CI to reduce failures from transient state locks.

## Recommended Pipeline Stages

1. Lint and format
- `terraform fmt -check -recursive`

2. Validate
- `terraform init -backend=false`
- `terraform validate`

3. Plan
- `terraform init -backend-config environment/dev.tfbackend` (local) or generated `backend.hcl` (CI)
- `terraform plan -var-file environment/dev.tfvars -out dev.tfplan`

4. Policy and security
- Run Checkov or tfsec for IaC security scanning.
- Run OPA/Conftest or Sentinel for policy guardrails.

5. Apply
- `terraform apply dev.tfplan` for Dev.
- `terraform apply prod.tfplan` for Prod after approval.

## Example GitHub Actions Workflow

Create `.github/workflows/terraform.yml`:

```yaml
name: Terraform CI/CD

on:
  pull_request:
    branches: [main]
  push:
    branches: [main]

permissions:
  id-token: write
  contents: read

jobs:
  validate:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: hashicorp/setup-terraform@v3
      - name: Terraform Format Check
        run: terraform fmt -check -recursive
      - name: Terraform Validate
        run: |
          terraform init -backend=false
          terraform validate

  plan-dev:
    if: github.event_name == 'pull_request'
    runs-on: ubuntu-latest
    needs: validate
    environment: dev
    steps:
      - uses: actions/checkout@v4
      - uses: hashicorp/setup-terraform@v3
      - name: Azure Login (OIDC)
        uses: azure/login@v2
        with:
          client-id: ${{ secrets.AZURE_CLIENT_ID }}
          tenant-id: ${{ secrets.AZURE_TENANT_ID }}
          subscription-id: ${{ secrets.AZURE_SUBSCRIPTION_ID }}
      - name: Terraform Plan Dev
        run: |
          terraform init -backend-config environment/dev.tfbackend
          terraform plan -var-file environment/dev.tfvars -out dev.tfplan

  apply-dev:
    if: github.event_name == 'push'
    runs-on: ubuntu-latest
    needs: validate
    environment: dev
    steps:
      - uses: actions/checkout@v4
      - uses: hashicorp/setup-terraform@v3
      - name: Azure Login (OIDC)
        uses: azure/login@v2
        with:
          client-id: ${{ secrets.AZURE_CLIENT_ID }}
          tenant-id: ${{ secrets.AZURE_TENANT_ID }}
          subscription-id: ${{ secrets.AZURE_SUBSCRIPTION_ID }}
      - name: Terraform Apply Dev
        run: |
          terraform init -backend-config environment/dev.tfbackend
          terraform plan -var-file environment/dev.tfvars -out dev.tfplan
          terraform apply -auto-approve dev.tfplan

  plan-prod:
    if: github.event_name == 'push'
    runs-on: ubuntu-latest
    needs: apply-dev
    environment: prod
    steps:
      - uses: actions/checkout@v4
      - uses: hashicorp/setup-terraform@v3
      - name: Azure Login (OIDC)
        uses: azure/login@v2
        with:
          client-id: ${{ secrets.AZURE_CLIENT_ID }}
          tenant-id: ${{ secrets.AZURE_TENANT_ID }}
          subscription-id: ${{ secrets.AZURE_SUBSCRIPTION_ID }}
      - name: Terraform Plan Prod
        run: |
          terraform init -backend-config environment/prod.tfbackend
          terraform plan -var-file environment/prod.tfvars -out prod.tfplan

  apply-prod:
    if: github.event_name == 'push'
    runs-on: ubuntu-latest
    needs: plan-prod
    environment: prod
    steps:
      - uses: actions/checkout@v4
      - uses: hashicorp/setup-terraform@v3
      - name: Azure Login (OIDC)
        uses: azure/login@v2
        with:
          client-id: ${{ secrets.AZURE_CLIENT_ID }}
          tenant-id: ${{ secrets.AZURE_TENANT_ID }}
          subscription-id: ${{ secrets.AZURE_SUBSCRIPTION_ID }}
      - name: Terraform Apply Prod
        run: |
          terraform init -backend-config environment/prod.tfbackend
          terraform plan -var-file environment/prod.tfvars -out prod.tfplan
          terraform apply -auto-approve prod.tfplan
```

## Operational Best Practices

- Tag all resources with `environment`, `owner`, `cost_center`, and `managed_by=terraform`.
- Run scheduled drift detection using `terraform plan` without apply.
- Keep module versioning explicit as the repository grows.
- Add post-deployment checks for app startup, private endpoint DNS resolution, and service health.

## Required GitHub Environment Secrets

Set these secrets in both `dev` and `prod` GitHub Environments:

- `AZURE_CLIENT_ID`
- `AZURE_TENANT_ID`
- `AZURE_SUBSCRIPTION_ID`
- `TFSTATE_RESOURCE_GROUP`
- `TFSTATE_STORAGE_ACCOUNT`
- `TFSTATE_CONTAINER`