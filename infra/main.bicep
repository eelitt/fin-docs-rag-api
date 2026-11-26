targetScope = 'subscription'

param location string = 'swedencentral'
param resourceGroupName string = 'rg-fin-docs-rag'
param foundryName string = 'rg-fin-docs-rag-resource'
param searchName string = 'srch-fin-docs-rag'
param storageName string = 'stfindocsrag'
param containerName string = 'documents'
param vaultName string = 'kv-fin-docs-rag'
param logAnalyticsName string = 'log-fin-docs-rag'
param appInsightsName string = 'appi-fin-docs-rag'
param containerImage string = ''
param chatDeploymentName string = 'gpt-4.1-mini'
param embeddingDeploymentName string = 'text-embedding-3-small'
@description('Thousands of tokens per minute. Match the quota already set in the portal.')
param chatCapacity int = 100
param embeddingCapacity int = 500

resource resourceGroup 'Microsoft.Resources/resourceGroups@2024-03-01' = {
  name: resourceGroupName
  location: location
}

module app 'resources.bicep' = {
  name: 'fin-docs-rag'
  scope: resourceGroup
  params: {
    location: location
    foundryName: foundryName
    searchName: searchName
    storageName: storageName
    containerName: containerName
    vaultName: vaultName
    chatDeploymentName: chatDeploymentName
    embeddingDeploymentName: embeddingDeploymentName
    chatCapacity: chatCapacity
    embeddingCapacity: embeddingCapacity
    logAnalyticsName: logAnalyticsName
    appInsightsName: appInsightsName
    containerImage: containerImage
  }
}
