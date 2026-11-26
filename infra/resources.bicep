param location string
param foundryName string
param searchName string
param storageName string
param containerName string
param vaultName string
param chatDeploymentName string
param embeddingDeploymentName string
param chatCapacity int
param embeddingCapacity int
param logAnalyticsName string
param appInsightsName string
param containerImage string = ''
param environmentName string = 'cae-fin-docs-rag'
param appName string = 'ca-fin-docs-rag'
param webIdentityName string = 'id-fin-docs-rag-web'
param ingestIdentityName string = 'id-fin-docs-rag-ingest'

resource foundry 'Microsoft.CognitiveServices/accounts@2024-10-01' = {
  name: foundryName
  location: location
  kind: 'AIServices'
  sku: {
    name: 'S0'
  }
  properties: {
    customSubDomainName: foundryName
    publicNetworkAccess: 'Enabled'
    disableLocalAuth: false
  }
}

resource chat 'Microsoft.CognitiveServices/accounts/deployments@2024-10-01' = {
  parent: foundry
  name: chatDeploymentName
  sku: {
    name: 'GlobalStandard'
    capacity: chatCapacity
  }
  properties: {
    model: {
      format: 'OpenAI'
      name: 'gpt-4.1-mini'
      version: '2025-04-14'
    }
  }
}

resource embedding 'Microsoft.CognitiveServices/accounts/deployments@2024-10-01' = {
  parent: foundry
  name: embeddingDeploymentName
  sku: {
    name: 'GlobalStandard'
    capacity: embeddingCapacity
  }
  properties: {
    model: {
      format: 'OpenAI'
      name: 'text-embedding-3-small'
      version: '1'
    }
  }
}

resource search 'Microsoft.Search/searchServices@2024-06-01-preview' = {
  name: searchName
  location: location
  sku: {
    name: 'free'
  }
  properties: {
    publicNetworkAccess: 'enabled'
    disableLocalAuth: false
    authOptions: {
      aadOrApiKey: {
        aadAuthFailureMode: 'http401WithBearerChallenge'
      }
    }
  }
}

resource storage 'Microsoft.Storage/storageAccounts@2023-05-01' = {
  name: storageName
  location: location
  sku: {
    name: 'Standard_LRS'
  }
  kind: 'StorageV2'
  properties: {
    allowBlobPublicAccess: false
    allowSharedKeyAccess: true
    isHnsEnabled: false
    isSftpEnabled: false
    minimumTlsVersion: 'TLS1_2'
    supportsHttpsTrafficOnly: true
  }
}

resource blobService 'Microsoft.Storage/storageAccounts/blobServices@2023-05-01' = {
  parent: storage
  name: 'default'
}

resource container 'Microsoft.Storage/storageAccounts/blobServices/containers@2023-05-01' = {
  parent: blobService
  name: containerName
  properties: {
    publicAccess: 'None'
  }
}

resource vault 'Microsoft.KeyVault/vaults@2023-07-01' = {
  name: vaultName
  location: location
  properties: {
    tenantId: tenant().tenantId
    sku: {
      family: 'A'
      name: 'standard'
    }
    enableRbacAuthorization: true
    enableSoftDelete: true
    softDeleteRetentionInDays: 90
    publicNetworkAccess: 'Enabled'
    enablePurgeProtection: false
  }
}

resource logAnalytics 'Microsoft.OperationalInsights/workspaces@2023-09-01' = {
  name: logAnalyticsName
  location: location
  properties: {
    sku: {
      name: 'PerGB2018'
    }
    retentionInDays: 30
    workspaceCapping: {
      dailyQuotaGb: 0.1
    }
  }
}

resource appInsights 'Microsoft.Insights/components@2020-02-02' = {
  name: appInsightsName
  location: location
  kind: 'web'
  properties: {
    Application_Type: 'web'
    WorkspaceResourceId: logAnalytics.id
    IngestionMode: 'LogAnalytics'
  }
}

resource appInsightsCap 'Microsoft.Insights/components/currentBillingFeatures@2015-05-01' = {
  parent: appInsights
  name: 'current'
  properties: {
    CurrentBillingFeatures: [
      'Basic'
    ]
    DataVolumeCap: {
      Cap: 0.1
      StopSendNotificationWhenHitCap: true
    }
  }
}

var blobReaderRole = '2a2b9908-6ea1-4ae2-8e65-a410df84e7d1'
var blobContributorRole = 'ba92f5b4-2d11-453d-a403-e96b0029c9fe'
var searchReaderRole = '1407120a-92aa-4202-b7e9-c0e197c71c8f'
var searchContributorRole = '8ebe5a00-799e-43f5-93ac-243d3dce84a7'
var searchServiceRole = '7ca78c08-252a-4471-8644-bb5ff32d4ba0'
var openAiUserRole = '5e0bd9bd-7b93-4f28-af87-19fc36ad61bd'

resource webIdentity 'Microsoft.ManagedIdentity/userAssignedIdentities@2023-01-31' = {
  name: webIdentityName
  location: location
}

resource ingestIdentity 'Microsoft.ManagedIdentity/userAssignedIdentities@2023-01-31' = {
  name: ingestIdentityName
  location: location
}

resource webBlobReader 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(storage.id, webIdentity.id, blobReaderRole)
  scope: storage
  properties: {
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', blobReaderRole)
    principalId: webIdentity.properties.principalId
    principalType: 'ServicePrincipal'
  }
}

resource webSearchReader 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(search.id, webIdentity.id, searchReaderRole)
  scope: search
  properties: {
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', searchReaderRole)
    principalId: webIdentity.properties.principalId
    principalType: 'ServicePrincipal'
  }
}

resource webOpenAiUser 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(foundry.id, webIdentity.id, openAiUserRole)
  scope: foundry
  properties: {
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', openAiUserRole)
    principalId: webIdentity.properties.principalId
    principalType: 'ServicePrincipal'
  }
}

resource ingestBlobContributor 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(storage.id, ingestIdentity.id, blobContributorRole)
  scope: storage
  properties: {
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', blobContributorRole)
    principalId: ingestIdentity.properties.principalId
    principalType: 'ServicePrincipal'
  }
}

resource ingestSearchContributor 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(search.id, ingestIdentity.id, searchContributorRole)
  scope: search
  properties: {
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', searchContributorRole)
    principalId: ingestIdentity.properties.principalId
    principalType: 'ServicePrincipal'
  }
}

resource ingestSearchService 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(search.id, ingestIdentity.id, searchServiceRole)
  scope: search
  properties: {
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', searchServiceRole)
    principalId: ingestIdentity.properties.principalId
    principalType: 'ServicePrincipal'
  }
}

resource ingestOpenAiUser 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(foundry.id, ingestIdentity.id, openAiUserRole)
  scope: foundry
  properties: {
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', openAiUserRole)
    principalId: ingestIdentity.properties.principalId
    principalType: 'ServicePrincipal'
  }
}

resource environment 'Microsoft.App/managedEnvironments@2024-03-01' = {
  name: environmentName
  location: location
  properties: {
    appLogsConfiguration: {
      destination: 'log-analytics'
      logAnalyticsConfiguration: {
        customerId: logAnalytics.properties.customerId
        sharedKey: logAnalytics.listKeys().primarySharedKey
      }
    }
  }
}

resource app 'Microsoft.App/containerApps@2024-03-01' = if (containerImage != '') {
  name: appName
  location: location
  identity: {
    type: 'UserAssigned'
    userAssignedIdentities: {
      '${webIdentity.id}': {}
    }
  }
  properties: {
    managedEnvironmentId: environment.id
    configuration: {
      activeRevisionsMode: 'Single'
      ingress: {
        external: true
        targetPort: 8000
        transport: 'auto'
        allowInsecure: false
      }
      secrets: [
        {
          name: 'app-insights'
          value: appInsights.properties.ConnectionString
        }
      ]
    }
    template: {
      containers: [
        {
          name: 'api'
          image: containerImage
          env: [
            { name: 'AZURE_CLIENT_ID', value: webIdentity.properties.clientId }
            { name: 'AZURE_OPENAI_ENDPOINT', value: 'https://${foundryName}.openai.azure.com/' }
            { name: 'AZURE_OPENAI_CHAT_DEPLOYMENT', value: chatDeploymentName }
            { name: 'AZURE_OPENAI_EMBEDDING_DEPLOYMENT', value: embeddingDeploymentName }
            { name: 'AZURE_SEARCH_ENDPOINT', value: 'https://${searchName}.search.windows.net' }
            { name: 'AZURE_STORAGE_ACCOUNT', value: storageName }
            { name: 'AZURE_STORAGE_CONTAINER', value: containerName }
            { name: 'OTEL_INSTRUMENTATION_GENAI_CAPTURE_MESSAGE_CONTENT', value: 'false' }
            { name: 'APPLICATIONINSIGHTS_CONNECTION_STRING', secretRef: 'app-insights' }
          ]
          resources: {
            cpu: json('0.5')
            memory: '1Gi'
          }
          probes: [
            {
              type: 'Liveness'
              httpGet: {
                path: '/health'
                port: 8000
                scheme: 'HTTP'
              }
              initialDelaySeconds: 10
              periodSeconds: 30
              failureThreshold: 3
            }
            {
              type: 'Readiness'
              httpGet: {
                path: '/ready'
                port: 8000
                scheme: 'HTTP'
              }
              initialDelaySeconds: 10
              periodSeconds: 30
              failureThreshold: 3
            }
          ]
        }
      ]
      scale: {
        minReplicas: 0
        maxReplicas: 1
      }
    }
  }
  dependsOn: [
    webBlobReader
    webSearchReader
    webOpenAiUser
  ]
}

output appUrl string = containerImage == '' ? '' : 'https://${app.properties.configuration.ingress.fqdn}'
