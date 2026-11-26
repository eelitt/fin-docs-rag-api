# Azure setup

Status: **decided**
Updated: 2026-11-25

This setup was done before M2. Bicep in `infra/` describes these same resources and has not been deployed. Do not create a second copy of any of them.

Prices and the forbidden list are in `03-architecture.md`. A budget alert does not stop spending. The way to stay near a few dollars is to create only the resources below and to avoid the forbidden list.

## Names

Use Sweden Central (`swedencentral`) for every resource. If a name is taken, add a short suffix and write the final name in the record table at the bottom. Do not create the resource in another region to get the name.

| Resource | Name |
| --- | --- |
| Resource group | `rg-fin-docs-rag` |
| Foundry resource | `oai-fin-docs-rag` |
| Foundry project | `fin-docs-rag` |
| Chat deployment | `gpt-4.1-mini` |
| Embedding deployment | `text-embedding-3-small` |
| Search service | `srch-fin-docs-rag` |
| Storage account | `stfindocsrag` |
| Blob container | `documents` |
| Key Vault | `kv-fin-docs-rag` |

The record table is the names that exist. The Foundry resource, the project, and both deployment names there differ from this table. Do not create a second resource to match a row above.

## 1. Subscription

1. Sign in at [https://portal.azure.com](https://portal.azure.com).
2. Use an existing subscription you control, or create one. A free trial is fine.
3. Confirm you can create resources. Owner or Contributor on the subscription is enough.

## 2. Budget alert

1. Open Cost Management + Billing, then Budgets, then Add.
2. Scope: this subscription. After the resource group exists, a second budget scoped to `rg-fin-docs-rag` is useful and optional.
3. Amount: 20 in the subscription currency (USD or EUR). Reset monthly.
4. Alert at 50%, 80%, and 100% to your email.

The alert only sends mail. It does not delete resources or stop token use.

## 3. Resource group

1. Create a resource group named `rg-fin-docs-rag`.
2. Region: Sweden Central.
3. Leave it empty until the steps below. After each later step, open the group and check that nothing extra appeared.

## 4. Models

Create one Foundry resource and two Global Standard deployments. Global Standard is pay-per-token. It costs nothing while idle.

Portal path:

1. Open [https://ai.azure.com](https://ai.azure.com). Turn on New Foundry if the portal offers that toggle.
2. Create a project named `fin-docs-rag`.
3. Advanced options: resource group `rg-fin-docs-rag`, location Sweden Central. Do not let the wizard create a new resource group in another region.
4. Open Build, then Catalog, then Model catalog.
5. Deploy `gpt-4.1-mini`. Choose custom settings if needed. Deployment name: `gpt-4.1-mini`. Deployment type: **Global standard**. Leave tokens-per-minute at the smallest value the form allows. That number is a quota, not an hourly charge, and it is the per-minute spend ceiling for the public demo. Do not raise it. Global Standard can process prompts outside the EU. The app does not store question text.
6. Deploy `text-embedding-3-small` the same way. Deployment name: `text-embedding-3-small`. Deployment type: **Global standard**.

If Global standard is missing for a model in Sweden Central, use Data zone standard. Do not use Provisioned, Provisioned Managed, or any SKU priced per hour.

Then open `rg-fin-docs-rag` in the Azure portal. Keep the Foundry / AI Services resource. If the wizard also created a Storage account, Key Vault, Search service, Application Insights, or Container Registry, leave them only when they match the names and tiers in this file. Delete anything else, especially a Search service whose tier is not Free, and any Container Registry.

## 5. Search

1. In the Azure portal, create Azure AI Search (the portal may label it Foundry IQ).
2. Subscription and resource group: the ones above. Region: Sweden Central.
3. Name: `srch-fin-docs-rag`.
4. Pricing tier: **Free**.
5. Create.

Free is one service per subscription, 50 MB, and $0. If Free is disabled, this subscription already has a free search service. Use that service or delete it, then create this one. Do not select Basic.

After creation, open the service, then Semantic ranker / premium features. Leave the paid plan off. This tier does not include semantic ranker. The app uses hybrid keyword and vector search.

Do not create an index. The ingest command creates it.

## 6. Storage

1. Create a storage account named `stfindocsrag` in `rg-fin-docs-rag`, Sweden Central.
2. Performance: Standard. Redundancy: LRS. The account kind can be StorageV2.
3. On the networking and data-protection screens, keep the defaults. Disable anonymous blob access if the form offers it.
4. After the account exists, create a container named `documents`. Access level: Private.

Do not enable SFTP. That feature has an hourly charge.

## 7. Key Vault

1. Create a Key Vault named `kv-fin-docs-rag` in the same group and region.
2. Pricing tier: Standard.
3. Permission model: Azure role-based access control.
4. Leave soft delete on.

You do not need to add secrets yet. When a later milestone stores a key, it goes here, not in git.

## 8. Values to keep locally

Copy endpoints from the portal into a local `.env` that is not committed. Do not paste keys or connection strings into this file or into chat.

| Variable | Where to copy it |
| --- | --- |
| `AZURE_OPENAI_ENDPOINT` | Foundry resource, Keys and Endpoint. Use the Azure OpenAI endpoint. |
| `AZURE_OPENAI_API_KEY` | Foundry resource, Keys and Endpoint. Either key. |
| `AZURE_OPENAI_CHAT_DEPLOYMENT` | Chat deployment name in the record table. |
| `AZURE_OPENAI_EMBEDDING_DEPLOYMENT` | Embedding deployment name in the record table. |
| `AZURE_SEARCH_ENDPOINT` | Search service, Overview. |
| `AZURE_SEARCH_API_KEY` | Search service, Keys. Admin key. |
| `AZURE_STORAGE_ACCOUNT` | Storage account name. |
| `AZURE_STORAGE_CONTAINER` | `documents` |
| `AZURE_STORAGE_KEY` | Storage account, Security + networking, Access keys. Either key. Local ingest uses it to upload PDFs. Do not put it in the container later. |
| `AZURE_KEY_VAULT_URL` | Key Vault, Overview, vault URI. |

A playground message in the Foundry project is enough to prove the chat deployment. The embedding deployment has no playground. Ingest uses its endpoint and deployment name.

## Created on 2026-11-26

Do not create a second copy of these in the portal. The public URL is `https://ca-fin-docs-rag.thankfulflower-24c321f8.swedencentral.azurecontainerapps.io`. The setup notes are in `docs/m6-setup.md`, which is gitignored.

- Log Analytics workspace `log-fin-docs-rag` and Application Insights `appi-fin-docs-rag`, with a daily ingestion cap of 0.1 GB on the workspace and on the component. GenAI content capture stays off: the exporter sends the span fields only, and the process sets `OTEL_INSTRUMENTATION_GENAI_CAPTURE_MESSAGE_CONTENT` to `false`.
- Container Apps environment `cae-fin-docs-rag` on the Consumption plan, and one app named `ca-fin-docs-rag` with minimum replicas 0 and maximum 1. Liveness is `GET /health`. Readiness is `GET /ready`. `id-fin-docs-rag-web` is the only identity on the app. It can read the blob, query the index, and call the two model deployments. It cannot write the blob or the index. `id-fin-docs-rag-ingest` can write and is not attached to the app. Neither identity is a subscription owner. The container has no API keys. Do not add a second host for the frontend. The image is a public `ghcr.io` package, not an Azure Container Registry.
- A caller secret in Key Vault only when a second app is registered. That app's server holds the secret. The secret is not written into a browser bundle. Until then the demo is the only caller. See `03-architecture.md`.

## Teardown

One command deletes the resource group, including the models, the search service, the storage account, and the corpus:

```
az group delete --name rg-fin-docs-rag --yes --no-wait
```

## Do not create

- Azure AI Search Basic or any higher tier.
- A second search service.
- Semantic ranker on a paid plan.
- Provisioned throughput for either model.
- Azure Document Intelligence.
- Azure Container Registry.
- Databricks, Azure Machine Learning, or API Management.
- A virtual machine, a private endpoint, or SFTP on the storage account.

## Done when

- `rg-fin-docs-rag` is in Sweden Central.
- The group contains the Foundry resource, the Free search service, the storage account, and the Key Vault, and nothing from the forbidden list.
- Both deployments exist and their type is Global standard, or Data zone standard if Global was unavailable.
- The budget alert is on.
- Endpoints and keys are in a local `.env` only.

## Record

Fill this in after setup. Leave secrets out.

| Item | Value |
| --- | --- |
| Subscription name | Azure subscription 1|
| Resource group | `rg-fin-docs-rag` |
| Foundry resource name | `rg-fin-docs-rag-resource` |
| Foundry OpenAI endpoint | `https://rg-fin-docs-rag-resource.openai.azure.com/` |
| Foundry project endpoint | `https://rg-fin-docs-rag-resource.services.ai.azure.com/api/projects/rg-fin-docs-rag` |
| Chat deployment and type | `gpt-4.1-mini`, Global Standard, model version `2025-04-14`, capacity 100 (100,000 tokens per minute). |
| Embedding deployment and type | `text-embedding-3-small`, Global Standard, model version `1`, capacity 500 (500,000 tokens per minute). |
| Search service name and tier | `srch-fin-docs-rag`, Free |
| Storage account name | `stfindocsrag` |
| Blob container | `documents`, private. Ingest created it on 2026-11-25. |
| Key Vault name | `kv-fin-docs-rag` |
| Extra resources deleted | not recorded |
| Date finished | 2026-11-25 |
