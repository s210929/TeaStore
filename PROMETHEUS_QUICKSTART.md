# Quick Start: OpenTelemetry + Prometheus

Deploy TeaStore with complete metrics monitoring in one command.

## What You Get

✅ Complete TeaStore application running
✅ Automatic metrics collection (HTTP, database, JVM)
✅ Prometheus dashboard to visualize metrics
✅ Historical data storage for trend analysis
✅ Single `kubectl apply` command — no manual steps

## Quick Deploy (1 Command)

Everything is consolidated into a single YAML file for simple one-command deployment:

```bash
# Deploy everything at once: OTel Collector, Prometheus, and TeaStore
kubectl apply -f examples/kubernetes/teastore-with-otel-prometheus.yaml

# Verify everything is running
kubectl get pods -w
```

**Wait for all pods to be Ready** (~2-3 minutes)

Once all pods show `Running`, open Prometheus:

```bash
# Port forward to Prometheus
kubectl port-forward svc/prometheus 9090:9090

# Open browser: http://localhost:9090
```

**That's it!** All services are now:
- ✅ Running with OTel agent enabled
- ✅ Sending metrics to the Collector
- ✅ Collector exporting to Prometheus
- ✅ Prometheus UI accessible

## Common Queries in Prometheus UI

1. **Click Graph tab**
2. **Type a query** in the Expression box
3. **Click Execute**

### Pre-built Queries

**HTTP Requests Per Second**
```promql
sum(rate(teastore_http_server_request_count_total[1m])) by (service)
```

**Error Rate**
```promql
sum(rate(teastore_http_server_request_count_total{status=~"5.."}[1m]))
```

**Average Latency (ms)**
```promql
avg(rate(teastore_http_server_duration_milliseconds_sum[5m])) / avg(rate(teastore_http_server_request_count_total[5m]))
```

**JVM Memory Usage**
```promql
process_runtime_java_memory_usage_bytes{type="heap"}
```

**P95 Latency**
```promql
histogram_quantile(0.95, rate(teastore_http_server_duration_milliseconds_bucket[5m]))
```

## How Data Flows

```
TeaStore Services (with OTel Agent)
        ↓ OTLP/gRPC (port 4317)
OpenTelemetry Collector
        ↓ Prometheus format
Prometheus (port 9090)
        ↓
Your Browser
```

## Verify Data is Flowing

```bash
# Watch pods come up (wait for all to be Running)
kubectl get pods -w
# Press Ctrl+C once all are Ready

# Check Collector is receiving metrics
kubectl logs -l app=otel-collector | tail -20

# Check metrics endpoint
kubectl port-forward svc/otel-collector 8888:8888
# Visit: http://localhost:8888/metrics in browser

# Check Prometheus targets
# In Prometheus UI: http://localhost:9090/targets
# Should show "otel-collector" target as UP
```

**Note:** TeaStore services use `initContainers` to wait for the OTel Collector to be healthy before starting. This ensures metrics don't get lost on startup. The first deployment may take 2-3 minutes while the Collector initializes.

## Configuration

All configuration is in one file: `examples/kubernetes/teastore-with-otel-prometheus.yaml`

### Disable OTel for Debugging

In the YAML file, find the `ENABLE_OTEL` env var in each TeaStore service:
```yaml
- name: ENABLE_OTEL
  value: "false"  # Change from "true"
```

Then redeploy:
```bash
kubectl apply -f examples/kubernetes/teastore-with-otel-prometheus.yaml
```

### Change Scrape Interval (default: 15s)

In the YAML file, find the Prometheus ConfigMap and update:
```yaml
global:
  scrape_interval: 30s  # Change to 30 seconds
```

### Change Metric Retention (default: 7 days)

In the Prometheus Deployment section:
```yaml
args:
  - '--storage.tsdb.retention.time=30d'  # Keep 30 days of data
```

## Troubleshooting

### No metrics in Prometheus?

1. **Check Collector is up**:
   ```bash
   kubectl get pod -l app=otel-collector
   ```

2. **Check Collector logs**:
   ```bash
   kubectl logs -l app=otel-collector | grep error
   ```

3. **Check metrics endpoint**:
   ```bash
   kubectl port-forward svc/otel-collector 8888:8888
   curl http://localhost:8888/metrics
   ```

4. **Check Prometheus targets**:
   - Visit: http://localhost:9090/targets
   - Verify "otel-collector" is GREEN (UP)

### Services not sending data?

```bash
# Check if ENABLE_OTEL is set
kubectl get pod <teastore-pod> -o jsonpath='{.spec.containers[0].env[?(@.name=="ENABLE_OTEL")].value}'

# Check if OTel agent initialized
kubectl logs <teastore-pod> | grep -i "OpenTelemetry\|javaagent"
```

### Prometheus out of memory?

Reduce retention:
```bash
# Edit deployment
kubectl patch deployment prometheus -p '{"spec":{"template":{"spec":{"containers":[{"name":"prometheus","args":["--storage.tsdb.retention.time=3d"]}]}}}}'
```

## Next Steps

1. **Create a Custom Dashboard**:
   - In Prometheus: **+ → Create Dashboard**
   - Add panels with your favorite metrics

2. **Set Up Alerts** (optional):
   - Define alert rules based on thresholds

3. **Read Full Guide**:
   - See `OTEL_PROMETHEUS_GUIDE.md` for advanced configuration

## Useful Commands

```bash
# Deploy everything
kubectl apply -f examples/kubernetes/teastore-with-otel-prometheus.yaml

# Watch deployment progress
kubectl get pods -w

# Port forward all at once (in separate terminals)
kubectl port-forward svc/prometheus 9090:9090          # Prometheus UI
kubectl port-forward svc/otel-collector 8888:8888      # Metrics endpoint
kubectl port-forward svc/teastore-webui 8080:8080      # TeaStore app

# Check all monitoring pods
kubectl get pods | grep -E "prometheus|otel"

# View Collector config
kubectl get cm otel-collector-config -o jsonpath='{.data.otel-collector-config\.yaml}' | head -30

# Stream Collector logs
kubectl logs -f -l app=otel-collector --all-containers=true

# Check Prometheus storage size
kubectl exec -it <prometheus-pod> -- du -sh /prometheus

# Delete everything
kubectl delete -f examples/kubernetes/teastore-with-otel-prometheus.yaml
```

## Architecture

```
┌─────────────────────────────────────────┐
│    TeaStore Services (6 instances)      │
│  ├─ WebUI                               │
│  ├─ Persistence                         │
│  ├─ Auth                                │
│  ├─ Image                               │
│  ├─ Recommender                         │
│  └─ Registry                            │
│  (All with OTel Agent: -javaagent)      │
└────────────────┬────────────────────────┘
                 │
          OTLP/gRPC (4317)
                 │
                 ▼
    ┌───────────────────────────┐
    │ OpenTelemetry Collector   │
    │  (Receives all metrics)   │
    │  (Exposed on 8888)        │
    └────────────┬──────────────┘
                 │
          Prometheus format
                 │
                 ▼
    ┌───────────────────────────┐
    │   Prometheus              │
    │  (Time series DB)         │
    │  (UI on 9090)             │
    └───────────────────────────┘
```

## What's Being Monitored

- HTTP request count, duration, status codes
- JDBC/Database queries
- JVM memory, CPU, garbage collection
- Tomcat thread pools and sessions
- Service-to-service RPC calls

## Limits & Performance

| Component | Default | Max Recommended |
|-----------|---------|-----------------|
| Scrape Interval | 15s | 5s (high traffic) |
| Collector Pods | 1 | 3+ (HA) |
| Retention | 7 days | 30 days |
| Collector Memory | 512Mi | 2Gi |
| Sample/sec | ~1000 | 100k+ |

## Common Issues

| Issue | Solution |
|-------|----------|
| No metrics | Check Prometheus targets UI (status should be GREEN) |
| High memory | Reduce retention: `--storage.tsdb.retention.time=3d` |
| Slow queries | Create specific dashboards instead of wildcard queries |
| Missing labels | Verify `OTEL_SERVICE_NAME` env var is set |

## Support

For detailed configuration and advanced use cases, see:
- `OTEL_PROMETHEUS_GUIDE.md` - Full guide with examples
- `OPENTELEMETRY.md` - General OTel documentation
