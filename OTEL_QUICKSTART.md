# OpenTelemetry Quick Start Guide

## Quick Deploy with OpenTelemetry

This guide gets you up and running with TeaStore and OpenTelemetry in minutes.

### Prerequisite: OTel Collector (Optional but Recommended)

If you want to see traces and metrics, set up Jaeger all-in-one:

```bash
docker run -d \
  --name jaeger \
  -p 16686:16686 \
  -p 14250:14250 \
  jaegertracing/all-in-one:latest
```

Or deploy to Kubernetes:

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: jaeger
spec:
  replicas: 1
  selector:
    matchLabels:
      app: jaeger
  template:
    metadata:
      labels:
        app: jaeger
    spec:
      containers:
      - name: jaeger
        image: jaegertracing/all-in-one:latest
        ports:
        - containerPort: 16686
        - containerPort: 14250
---
apiVersion: v1
kind: Service
metadata:
  name: jaeger
spec:
  type: LoadBalancer
  ports:
  - port: 16686
    targetPort: 16686
  - port: 14250
    targetPort: 14250
  selector:
    app: jaeger
```

### Step 1: Build TeaStore with OTel

```bash
cd /path/to/TeaStore
mvn clean install
./tools/build_docker.sh
```

### Step 2: Deploy to Kubernetes

```bash
kubectl apply -f examples/kubernetes/teastore-ribbon.yaml
```

The deployment includes:
- ✅ OTel agent automatically injected
- ✅ OTLP exporter configured
- ✅ All services instrumented
- ✅ Traces sent to `localhost:4317` (configure as needed)

### Step 3: View Traces in Jaeger

Open Jaeger UI: http://localhost:16686

1. Select service (e.g., `teastore-webui`)
2. Find traces in the UI
3. Click on trace to see span details

### Configuration

#### Change OTLP Endpoint (for Jaeger, Prometheus, etc)

Edit `teastore-ribbon.yaml`:

```yaml
env:
- name: OTEL_EXPORTER_OTLP_ENDPOINT
  value: "http://your-collector:4317"
```

#### Disable OTel for Specific Service

```yaml
env:
- name: ENABLE_OTEL
  value: "false"
```

#### Change Service Name

```yaml
env:
- name: OTEL_SERVICE_NAME
  value: "my-custom-name"
```

### View Metrics with Prometheus

Configure OTel Collector to export to Prometheus and view metrics.

### View Logs

Check if agent loaded:

```bash
kubectl logs <pod-name> | grep -i opentelemetry
```

## Common Issues

### "No traces in Jaeger"

1. Check collector is running: `docker ps | grep jaeger`
2. Verify OTEL_EXPORTER_OTLP_ENDPOINT is correct
3. Check pod logs: `kubectl logs <pod-name> | tail -20`

### "High memory usage"

Reduce sampling rate in `teastore-ribbon.yaml`:

```yaml
env:
- name: OTEL_TRACES_SAMPLER
  value: "parentbased_traceidratio"
- name: OTEL_TRACES_SAMPLER_ARG
  value: "0.1"  # 10% sampling
```

### "Connection refused to OTLP endpoint"

Make sure collector is reachable and endpoint is correct:

```bash
kubectl exec <pod-name> -- curl http://collector:4317
```

## Next Steps

1. Explore traces in Jaeger to understand request flow
2. Set up alerts based on error rates
3. Create dashboards for key metrics
4. Read [OPENTELEMETRY.md](OPENTELEMETRY.md) for advanced config

## Useful Commands

```bash
# Check if OTel is enabled
kubectl get pods -o jsonpath='{range .items[*]}{.metadata.name}{"\t"}{.spec.containers[0].env[?(@.name=="ENABLE_OTEL")].value}{"\n"}{end}'

# View agent logs
kubectl logs <pod-name> | grep javaagent

# Port forward to Jaeger UI
kubectl port-forward svc/jaeger 16686:16686

# Port forward to collector
kubectl port-forward svc/otel-collector 4317:4317
```
