# OpenTelemetry with Prometheus Integration Guide

## Overview

This guide explains how to use OpenTelemetry with TeaStore to collect metrics and visualize them in Prometheus. The setup uses an OpenTelemetry Collector that receives metrics from all TeaStore services and exports them to Prometheus.

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    TeaStore Services                         │
│  (webui, persistence, auth, image, recommender, registry)   │
│          (OTel Agent enabled via -javaagent)                │
└──────────────────────────┬──────────────────────────────────┘
                           │
                           │ OTLP/gRPC (port 4317)
                           ▼
            ┌──────────────────────────────┐
            │   OpenTelemetry Collector    │
            │  (Receives OTLP metrics)     │
            │   (Port 4317 receiver)       │
            │   (Port 8888 Prometheus exp) │
            └──────────────┬───────────────┘
                           │
                           │ Prometheus format
                           │ (localhost:8888/metrics)
                           ▼
              ┌────────────────────────┐
              │     Prometheus         │
              │   (Time series DB)     │
              │   (Web UI: 9090)       │
              └────────────────────────┘
```

## What Gets Collected

The OTel agent automatically collects:

### Metrics
- **HTTP Requests**: Method, path, status code, duration
- **Database Operations**: JDBC query execution time
- **JVM Metrics**: Memory, CPU, garbage collection
- **Tomcat Metrics**: Request processing, thread pools
- **RPC Calls**: Service-to-service communication

### Example Metrics Available in Prometheus
```
teastore_http_server_duration_milliseconds_bucket
teastore_http_server_request_count_total
teastore_rpc_server_duration_milliseconds_bucket
process_runtime_go_memory_heap_alloc_bytes
tomcat_sessions_active_max
```

## Setup Instructions

### Deploy Everything with One Command

All TeaStore services, OTel Collector, and Prometheus are consolidated in a single manifest file:

```bash
# Deploy the complete stack (everything in one command)
kubectl apply -f examples/kubernetes/teastore-with-otel-prometheus.yaml

# Verify all deployments are running
kubectl get pods -w

# Services use init containers that wait for Collector health (~2-3 minutes total)
```

**Key Features:**
- ✅ Single YAML file with everything: Collector, Prometheus, all 6 TeaStore services, Database
- ✅ Init containers on TeaStore pods wait for Collector to be healthy before starting
- ✅ Automatic service discovery via Kubernetes DNS (`otel-collector:4317`)
- ✅ All services pre-configured with `ENABLE_OTEL=true` and `OTEL_SERVICE_NAME`
- ✅ No manual endpoint configuration needed — just one deploy

### Verify Deployment

```bash
# Check all pods are running
kubectl get pods

# Check OTel Collector logs
kubectl logs -l app=otel-collector -f

# Verify metrics endpoint
kubectl port-forward svc/otel-collector 8888:8888
# Visit: http://localhost:8888/metrics
```

### Access Prometheus UI

```bash
# Port forward to Prometheus
kubectl port-forward svc/prometheus 9090:9090

# Open browser to http://localhost:9090
```

## Using Prometheus

### Finding Metrics

1. **Open Prometheus Web UI**: http://localhost:9090

2. **Use the Search/Graph Interface**:
   - Click on the **Graph** tab
   - In the "Expression" field, type a metric name
   - Click "Execute" to see data

### Common Queries

#### HTTP Request Duration
```promql
# Average HTTP request duration per service (last 5 minutes)
avg by (service) (rate(teastore_http_server_duration_milliseconds_sum[5m]))

# HTTP request error rate
rate(teastore_http_server_request_count_total{status=~"5.."}[5m])
```

#### Database Operations
```promql
# Average JDBC query duration
avg(rate(teastore_db_client_operation_duration_milliseconds_sum[5m]))

# Total JDBC queries per service
sum by (service) (rate(teastore_db_client_operation_count_total[5m]))
```

#### JVM Metrics
```promql
# JVM memory usage
process_runtime_java_memory_usage_bytes{type="heap"}

# GC time
rate(process_runtime_java_gc_duration_seconds_sum[5m])
```

#### Service Health
```promql
# Services with errors in last 5 minutes
teastore_http_server_request_count_total{status=~"5.."}

# Request latency percentiles
histogram_quantile(0.95, rate(teastore_http_server_duration_milliseconds_bucket[5m]))
```

### Creating Dashboards

1. **Create a Dashboard**:
   - Click **+** icon in Prometheus UI
   - Select **Create Dashboard**

2. **Add Charts**:
   - Click **Add Panel**
   - Enter a PromQL query
   - Choose visualization type (Graph, Gauge, Table)
   - Set title and labels

3. **Example Dashboard Setup**:

```yaml
# Panel 1: Request Rate
Query: sum(rate(teastore_http_server_request_count_total[5m])) by (service)
Visualization: Graph
Title: "Requests per Second by Service"

# Panel 2: Error Rate
Query: sum(rate(teastore_http_server_request_count_total{status=~"5.."}[5m])) by (service)
Visualization: Graph
Title: "Error Rate by Service"

# Panel 3: P95 Latency
Query: histogram_quantile(0.95, rate(teastore_http_server_duration_milliseconds_bucket[5m]))
Visualization: Gauge
Title: "P95 Latency (ms)"

# Panel 4: JVM Heap Usage
Query: process_runtime_java_memory_usage_bytes{type="heap"}
Visualization: Graph
Title: "JVM Heap Memory Usage"
```

## Monitoring TeaStore Services

### Key Metrics to Monitor

1. **WebUI Service**
   ```promql
   # Average response time
   avg(rate(teastore_http_server_duration_milliseconds_sum{service="teastore-webui"}[5m]))
   
   # Error rate
   rate(teastore_http_server_request_count_total{service="teastore-webui", status=~"5.."}[5m])
   ```

2. **Persistence Service**
   ```promql
   # Database query duration
   avg(rate(teastore_db_client_operation_duration_milliseconds_sum[5m]))
   
   # Active connections
   teastore_db_client_connections_usage
   ```

3. **Recommender Service**
   ```promql
   # Algorithm computation time
   rate(teastore_rpc_server_duration_milliseconds_sum{service="teastore-recommender"}[5m])
   
   # Training job status
   teastore_recommender_training_duration_seconds
   ```

## Configuration Options

All configuration is in the single file: `examples/kubernetes/teastore-with-otel-prometheus.yaml`

### Adjust Collection Interval

Edit the Prometheus ConfigMap section in the YAML file:

```yaml
data:
  prometheus.yml: |
    global:
      scrape_interval: 30s  # Change from 15s to 30s
```

Then redeploy:
```bash
kubectl apply -f examples/kubernetes/teastore-with-otel-prometheus.yaml
```

### Change Retention Period

Edit the Prometheus Deployment section:

```yaml
args:
  - '--storage.tsdb.retention.time=30d'  # Keep metrics for 30 days
```

### Adjust OTel Collector Resource Limits

Edit the OTel Collector Deployment resources section:

```yaml
resources:
  limits:
    cpu: 1000m      # Increase from 500m
    memory: 1Gi     # Increase from 512Mi
```

### Enable/Disable OTel Agent

In each TeaStore service Deployment, find the env section:

```yaml
env:
  - name: ENABLE_OTEL
    value: "false"  # Change from "true" to disable
```

## Troubleshooting


### No Metrics Appearing in Prometheus

1. **Check OTel Collector is receiving data**:
   ```bash
   kubectl logs -l app=otel-collector -f | grep -i "metric"
   ```

2. **Verify services are sending data**:
   ```bash
   kubectl logs -l run=teastore-webui | grep -i "opentelemetry"
   ```

3. **Check Prometheus targets**:
   - Go to Prometheus: http://localhost:9090/targets
   - Verify `otel-collector` target is "UP"

### Collector Memory Issues

```bash
# Check memory usage
kubectl top pod -l app=otel-collector

# If high, reduce batch size in otel-collector-config.yaml:
processors:
  batch:
    send_batch_size: 512  # Reduce from 1024
```

### Missing Service Labels

```bash
# Query with service label
teastore_http_server_request_count_total{service="teastore-webui"}

# If service label missing, verify OTEL_SERVICE_NAME env var:
kubectl get pod <pod-name> -o jsonpath='{.spec.containers[0].env[?(@.name=="OTEL_SERVICE_NAME")].value}'
```

## Performance Tuning

### For High-Traffic Deployments

1. **Enable Sampling** (reduce by 50%):
   ```yaml
   env:
   - name: OTEL_TRACES_SAMPLER
     value: "parentbased_traceidratio"
   - name: OTEL_TRACES_SAMPLER_ARG
     value: "0.5"
   ```

2. **Increase Collector Resources**:
   ```yaml
   resources:
     limits:
       cpu: 2000m
       memory: 2Gi
   ```

3. **Batch Processing**:
   ```yaml
   processors:
     batch:
       send_batch_size: 2048
       timeout: 5s
   ```

### For Low-Traffic Deployments

1. **Reduce Scrape Frequency**:
   ```yaml
   scrape_interval: 30s
   ```

2. **Decrease Retention**:
   ```yaml
   --storage.tsdb.retention.time=3d
   ```

## Advanced: Export to External Systems

### Export to Grafana Cloud

Update OTel Collector config to add remote write:

```yaml
exporters:
  prometheusremotewrite:
    endpoint: https://prometheus-blocks-prod-us-central1.grafana.net/api/prom/push
    headers:
      Authorization: "Bearer YOUR_TOKEN"

service:
  pipelines:
    metrics:
      exporters: [prometheus, prometheusremotewrite]
```

### Export to Datadog

```yaml
exporters:
  datadog:
    hostname_source: "resource_attribute"
    env: "production"
    version: "1.0"
    tags: ["service:teastore"]

service:
  pipelines:
    metrics:
      exporters: [prometheus, datadog]
```

## Quick Troubleshooting Checklist

- [ ] OTel Collector pod is running: `kubectl get pods | grep otel`
- [ ] Prometheus pod is running: `kubectl get pods | grep prometheus`
- [ ] OTel Collector service is accessible: `kubectl get svc otel-collector`
- [ ] TeaStore pods have `ENABLE_OTEL=true`: `kubectl get pod <pod> -o yaml | grep ENABLE_OTEL`
- [ ] Metrics endpoint responds: `curl http://localhost:8888/metrics`
- [ ] Prometheus can access Collector: `http://prometheus:9090/targets`
- [ ] No errors in OTel Collector logs: `kubectl logs -l app=otel-collector`

## Next Steps

1. **Create custom dashboards** for your business metrics
2. **Set up alerts** for critical thresholds
3. **Export metrics** to external monitoring systems
4. **Analyze traces** using distributed tracing (optional Jaeger integration)
5. **Optimize performance** based on collected data

## References

- [OpenTelemetry Documentation](https://opentelemetry.io/)
- [Prometheus Documentation](https://prometheus.io/docs/)
- [OTel Collector Configuration](https://opentelemetry.io/docs/collector/configuration/)
- [PromQL Query Language](https://prometheus.io/docs/prometheus/latest/querying/basics/)
