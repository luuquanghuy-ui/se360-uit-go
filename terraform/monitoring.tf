resource "azurerm_monitor_action_group" "security" {
  name                = "ag-${var.prefix}-security"
  resource_group_name = azurerm_resource_group.rg.name
  short_name          = "uitgo-sec"

  dynamic "email_receiver" {
    for_each = var.alert_emails
    content {
      name          = replace(email_receiver.value, "@", "-")
      email_address = email_receiver.value
    }
  }
}

locals {
  log_workspace_id = azurerm_log_analytics_workspace.logs.id
}

resource "azurerm_monitor_scheduled_query_rules_alert" "aks_cpu_high" {
  name                = "sq-${var.prefix}-aks-cpu"
  resource_group_name = azurerm_resource_group.rg.name
  location            = azurerm_resource_group.rg.location
  data_source_id      = local.log_workspace_id
  description         = "Cảnh báo khi CPU node AKS vượt 80% trong 5 phút."
  severity            = 2
  frequency           = 5
  time_window         = 5
  enabled             = true
  query = <<QUERY
InsightsMetrics
| where Namespace == "container.azm.ms/node" and Name == "cpuUsageNanoCores"
| summarize AvgCpu = avg(Val / 10000000) by Computer, bin(TimeGenerated, 5m)
| where AvgCpu > 80
QUERY

  trigger {
    operator  = "GreaterThan"
    threshold = 0
  }

  action {
    action_group = [azurerm_monitor_action_group.security.id]
  }
}

resource "azurerm_monitor_scheduled_query_rules_alert" "aks_memory_high" {
  name                = "sq-${var.prefix}-aks-memory"
  resource_group_name = azurerm_resource_group.rg.name
  location            = azurerm_resource_group.rg.location
  data_source_id      = local.log_workspace_id
  description         = "Cảnh báo khi Memory node AKS vượt 80%."
  severity            = 2
  frequency           = 5
  time_window         = 5
  enabled             = true
  query = <<QUERY
InsightsMetrics
| where Namespace == "container.azm.ms/node" and Name == "memoryRssBytes"
| summarize AvgMem = avg(Val / 1073741824 * 100) by Computer, bin(TimeGenerated, 5m)
| where AvgMem > 80
QUERY

  trigger {
    operator  = "GreaterThan"
    threshold = 0
  }

  action {
    action_group = [azurerm_monitor_action_group.security.id]
  }
}

resource "azurerm_monitor_scheduled_query_rules_alert" "pod_restart" {
  name                = "sq-${var.prefix}-pod-restart"
  resource_group_name = azurerm_resource_group.rg.name
  location            = azurerm_resource_group.rg.location
  data_source_id      = local.log_workspace_id
  description         = "Cảnh báo khi pod restart liên tục (ready < 80%)."
  severity            = 3
  frequency           = 5
  time_window         = 10
  enabled             = true
  query = <<-EOT
KubePodInventory
| where TimeGenerated >= ago(10m)
| summarize count() by Name, Status
| where Status != "Running"
EOT

  trigger {
    operator  = "GreaterThan"
    threshold = 0
  }

  action {
    action_group = [azurerm_monitor_action_group.security.id]
  }
}

resource "azurerm_monitor_scheduled_query_rules_alert" "node_not_ready" {
  name                = "sq-${var.prefix}-node-notready"
  resource_group_name = azurerm_resource_group.rg.name
  location            = azurerm_resource_group.rg.location
  data_source_id      = local.log_workspace_id
  description         = "Phát hiện node AKS ở trạng thái NotReady."
  severity            = 2
  frequency           = 5
  time_window         = 5
  enabled             = true
  query = <<QUERY
KubeNodeInventory
| where Status != "Ready"
QUERY

  trigger {
    operator  = "GreaterThan"
    threshold = 0
  }

  action {
    action_group = [azurerm_monitor_action_group.security.id]
  }
}

resource "azurerm_monitor_scheduled_query_rules_alert" "linkerd_mtls_failure" {
  name                = "sq-${var.prefix}-linkerd-mtls"
  resource_group_name = azurerm_resource_group.rg.name
  location            = azurerm_resource_group.rg.location
  data_source_id      = local.log_workspace_id
  description         = "Thông báo khi Linkerd ghi nhận handshake/mTLS lỗi."
  severity            = 2
  frequency           = 5
  time_window         = 10
  enabled             = true
  query = <<QUERY
ContainerLog
| where LogEntry has "linkerd" and LogEntry has "TLS handshake error"
QUERY

  trigger {
    operator  = "GreaterThan"
    threshold = 0
  }

  action {
    action_group = [azurerm_monitor_action_group.security.id]
  }
}

resource "azurerm_monitor_metric_alert" "cosmos_high_requests" {
  name                = "metric-${var.prefix}-cosmos-requests"
  resource_group_name = azurerm_resource_group.rg.name
  scopes              = [azurerm_cosmosdb_account.cosmos.id]
  description         = "Tổng request CosmosDB vượt 1000/5 phút."
  severity            = 2
  frequency           = "PT5M"
  window_size         = "PT5M"
  criteria {
    metric_namespace = "Microsoft.DocumentDB/databaseAccounts"
    metric_name      = "TotalRequests"
    aggregation      = "Count"
    operator         = "GreaterThan"
    threshold        = 1000
  }
  action {
    action_group_id = azurerm_monitor_action_group.security.id
  }
}

resource "azurerm_monitor_metric_alert" "redis_cpu_high" {
  name                = "metric-${var.prefix}-redis-cpu"
  resource_group_name = azurerm_resource_group.rg.name
  scopes              = [azurerm_redis_cache.redis.id]
  description         = "Redis Memory > 80%."
  severity            = 2
  frequency           = "PT5M"
  window_size         = "PT5M"
  criteria {
    metric_namespace = "Microsoft.Cache/Redis"
    metric_name      = "usedMemoryPercentage"
    aggregation      = "Average"
    operator         = "GreaterThan"
    threshold        = 80
  }
  action {
    action_group_id = azurerm_monitor_action_group.security.id
  }
}

