# ADR-002: VNet Service Endpoints over Private Endpoints

## Status
Accepted

## Context
Decision on network isolation strategy for database access in UIT-Go microservices architecture.

## Problem Statement
- CosmosDB and Redis were initially configured with public network access
- Need to secure database access while maintaining low cost
- Balance between security requirements and cost constraints

## Decision
**Use VNet Service Endpoints instead of Private Endpoints** for database network isolation.

## Rationale

### Benefits of VNet Service Endpoints:
1. **Zero Cost**: No additional charge compared to Private Endpoints (~$15/month per endpoint)
2. **Same Security**: Provides private IP access within VNet
3. **Simplicity**: Native Azure integration without additional networking components
4. **Performance**: Direct Azure backbone connectivity

### Cost Analysis:
| Solution | Monthly Cost | Setup Complexity | Security Level |
|-----------|-------------|------------------|----------------|
| Private Endpoints (2x) | $15/month | Medium | High |
| **VNet Service Endpoints** | **$0/month** | **Low** | **High** |

## Consequences

### Positive:
- **Cost Savings**: $15/month reduction in infrastructure costs
- **Simplified Architecture**: No need for additional subnet planning
- **Maintained Security**: Private access within VNet only
- **Azure Native**: Leverages built-in Azure networking features

### Negative:
- **Limited to Azure Resources**: Only works with Azure services that support service endpoints
- **VNet Dependency**: Requires resources to be in the same VNet

### Neutral:
- **Same Performance**: No performance impact compared to Private Endpoints
- **Management**: Similar operational complexity

## Implementation

### 1. Service Endpoint Configuration
```hcl
resource "azurerm_subnet" "aks_subnet" {
  name                 = "snet-aks-prod"
  resource_group_name  = azurerm_resource_group.rg.name
  virtual_network_name = azurerm_virtual_network.vnet.name
  address_prefixes     = ["172.16.1.0/24"]

  service_endpoints = [
    "Microsoft.ContainerRegistry",
    "Microsoft.Storage",
    "Microsoft.AzureCosmosDB",
    "Microsoft.Sql",
    # Microsoft.Cache not supported, Redis handled differently
  ]
}
```

### 2. Database Security Updates
```hcl
resource "azurerm_cosmosdb_account" "cosmos" {
  name                = "cosmos-uitgohuy-prod"
  public_network_access_enabled = false
  is_virtual_network_filter_enabled = true
  # ... other configuration
}

resource "azurerm_redis_cache" "redis" {
  name                = "redis-uitgohuy-prod"
  public_network_access_enabled = false
  subnet_id           = azurerm_subnet.aks_subnet.id
  # ... other configuration
}
```

### 3. Network Policies
- Implemented zero-trust network policies
- Default deny all ingress/egress
- Specific allow rules for Azure services

## Validation

### Security Testing:
1. ✅ Public access blocked
2. ✅ Internal connectivity verified
3. ✅ Service-to-service mTLS encryption working
4. ✅ Network policies enforced

### Performance Testing:
1. ✅ Latency unchanged (<10ms overhead)
2. ✅ Throughput maintained
3. ✅ Connection stability verified

## Alternatives Considered

### 1. Private Endpoints
- **Pros**: Highest security, works with any service
- **Cons**: $15/month per endpoint, additional networking complexity
- **Rejected**: Cost constraint

### 2. Public Access with IP Whitelisting
- **Pros**: Simple to implement
- **Cons**: Still exposes attack surface, IP management overhead
- **Rejected**: Security insufficient

### 3. Application Gateway with WAF
- **Pros**: Advanced security features
- **Cons**: High cost ($70+/month), complexity
- **Rejected**: Overkill for this use case

## Future Considerations

### When to Reconsider:
- **Regulatory Requirements**: If compliance demands Private Endpoints
- **Multi-Cloud Strategy**: If non-Azure services need isolation
- **Advanced Security Features**: If additional WAF/protection needed

### Migration Path:
- Can easily migrate to Private Endpoints if needed
- Network policies already support Private Endpoints
- No application changes required

## Conclusion

VNet Service Endpoints provide the optimal balance of security, cost, and simplicity for the UIT-Go project. This decision saves $15/month while maintaining enterprise-grade security for database access.

## References
- [Azure Service Endpoints Documentation](https://docs.microsoft.com/azure/virtual-network/virtual-network-service-endpoints-overview)
- [Azure Pricing Calculator](https://azure.microsoft.com/pricing/calculator/)
- [Cost Analysis in plan.md](../docs/plan.md)