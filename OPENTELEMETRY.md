# OpenTelemetry Integration for TeaStore

This document describes the OpenTelemetry implementation for the TeaStore application, which enables automatic collection of traces and metrics when deploying with `teastore-ribbon.yaml`.

## Overview

OpenTelemetry Java Agent has been integrated into the TeaStore application to provide automatic instrumentation of HTTP requests, JDBC calls, and other Java operations. The agent is downloaded from the official GitHub releases and runs as a Java agent during application startup.

## Quick Start with Prometheus

To get started with **Prometheus monitoring** (recommended for metrics):

```bash
# Deploy everything with one command (OTel Collector, Prometheus, and all TeaStore services)
kubectl apply -f examples/kubernetes/teastore-with-otel-prometheus.yaml

# Wait for all pods to be ready (~2-3 minutes)
kubectl get pods -w

# Access Prometheus UI
kubectl port-forward svc/prometheus 9090:9090
# Open: http://localhost:9090
```

**Documentation:**
1. **[PROMETHEUS_QUICKSTART.md](PROMETHEUS_QUICKSTART.md)** - Quick reference and common queries
2. **[OTEL_PROMETHEUS_GUIDE.md](OTEL_PROMETHEUS_GUIDE.md)** - Full guide with dashboards and troubleshooting

For **technical details** of OTel configuration, continue reading below.

## Architecture

### Components

1. **OpenTelemetry Java Agent** (Official from GitHub)
   - Version: 1.31.0
   - Downloaded from: https://github.com/open-telemetry/opentelemetry-java-instrumentation/releases
   - Location in container: `/otel/agent/opentelemetry-javaagent.jar`
   - Provides automatic instrumentation for Servlets, HTTP clients, JDBC, and more

2. **Docker Configuration**
   - Updated `Dockerfile` to download the OTel agent JAR
   - Created `/metrics` directory for metrics storage
   - Updated startup script to enable/disable agent via `ENABLE_OTEL` environment variable

3. **Kubernetes Configuration**
   - Updated `teastore-ribbon.yaml` to configure OTel environment variables
   - Each service has `ENABLE_OTEL=true` to activate instrumentation
   - OTLP exporter endpoint configured via `OTEL_EXPORTER_OTLP_ENDPOINT`

## How It Works

### Agent Activation

The OpenTelemetry Java agent is activated when:
1. The `ENABLE_OTEL` environment variable is set to `"true"`
2. The agent JAR is injected into the Java startup command via `-javaagent` flag
3. The agent automatically instruments common Java frameworks and libraries

### Automatic Instrumentation

The agent automatically instruments:
- **HTTP Servlets**: All HTTP requests and responses
- **Apache HTTP Client**: Outbound HTTP calls
- **JDBC**: Database queries
- **Tomcat**: Application server operations
- **Logging**: Slf4j/Log4j

### Metrics and Traces

The agent collects:
- **Traces**: Distributed traces for request flows across services
- **Metrics**: Request counts, latencies, error rates, database metrics
- **Span Events**: Detailed events within operations

## Configuration

### Environment Variables

All OTel agent configuration is controlled via environment variables:

```yaml
ENABLE_OTEL: "true"                                    # Enable/disable instrumentation
OTEL_SERVICE_NAME: "teastore-webui"                    # Service identifier
OTEL_EXPORTER_OTLP_ENDPOINT: "http://localhost:4317"   # OTLP collector endpoint
OTEL_EXPORTER_OTLP_PROTOCOL: "grpc"                    # Protocol (grpc or http/protobuf)
OTEL_TRACES_SAMPLER: "always_on"                       # Sampling strategy
```

### Configuration File

Optional configuration file at `/otel/config/otel-config.properties`:
```properties
otel.service.name=teastore
otel.exporter.otlp.protocol=grpc
otel.exporter.otlp.endpoint=http://localhost:4317
otel.instrumentation.servlet.enabled=true
otel.traces.sampler=always_on
```

## Building and Deploying

### Build the Application

```bash
# Build all modules (OTel is now integrated at Docker level, not Maven)
mvn clean install
```

### Build Docker Images

The docker images will now download and include the OpenTelemetry Java agent:

```bash
./tools/build_docker.sh
```

### Deploy to Kubernetes

Deploy using the updated manifest with OTel enabled:

```bash
kubectl apply -f examples/kubernetes/teastore-ribbon.yaml
```

## Collecting Metrics and Traces

### Option 1: OTLP Collector (Recommended)

Set up an OpenTelemetry Collector to receive data:

```bash
# Create a collector configuration
cat > otel-collector-config.yaml << EOF
receivers:
  otlp:
    protocols:
      grpc:
        endpoint: 0.0.0.0:4317

exporters:
  logging:
    loglevel: debug
  jaeger:
    endpoint: jaeger:14250
  prometheus:
    endpoint: "0.0.0.0:8889"

service:
  pipelines:
    traces:
      receivers: [otlp]
      exporters: [logging, jaeger]
    metrics:
      receivers: [otlp]
      exporters: [prometheus]
EOF

# Deploy the collector
docker run -d \
  -p 4317:4317 \
  -p 8889:8889 \
  -v ./otel-collector-config.yaml:/etc/otel-collector-config.yaml \
  otel/opentelemetry-collector-k8s:latest \
  --config=/etc/otel-collector-config.yaml
```

### Option 2: Using Jaeger for Distributed Tracing

```bash
# Deploy Jaeger all-in-one
docker run -d \
  -p 6831:6831/udp \
  -p 16686:16686 \
  jaegertracing/all-in-one:latest

# Update OTEL_EXPORTER_OTLP_ENDPOINT to point to Jaeger:
# OTEL_EXPORTER_OTLP_ENDPOINT: "http://jaeger:4317"
```

### Option 3: Cloud Export (Datadog, GCP, AWS)

Configure via environment variables:

```yaml
# Datadog
OTEL_EXPORTER_OTLP_ENDPOINT: "https://api.datadoghq.com"
OTEL_EXPORTER_OTLP_HEADERS: "dd-api-key=<your-key>"

# Google Cloud Trace
OTEL_EXPORTER_OTLP_ENDPOINT: "https://cloudtrace.googleapis.com/opentelemetry.proto.collector.trace.v1.TraceService"
```

## Monitoring Metrics and Traces

### Jaeger UI (if using Jaeger collector)

Access traces at: `http://localhost:16686`

Search for traces by:
- Service name: `teastore-webui`, `teastore-persistence`, etc.
- Operation name: HTTP endpoints
- Tags: status_code, http.method, etc.

### Prometheus Metrics (if using Prometheus exporter)

Metrics available at: `http://localhost:9090`

Common metrics:
- `otel_http_requests_total`: Total HTTP requests
- `otel_http_request_duration_seconds`: Request latency
- `otel_rpc_server_duration_seconds`: Server request duration

### Using kubectl to access metrics

```bash
# Forward Jaeger UI from Kubernetes
kubectl port-forward svc/jaeger 16686:16686

# Forward Prometheus
kubectl port-forward svc/prometheus 9090:9090
```

## Kubernetes Deployment with Collector

Example complete stack:

```yaml
---
# OpenTelemetry Collector
apiVersion: v1
kind: ConfigMap
metadata:
  name: otel-collector-config
data:
  otel-collector-config.yaml: |
    receivers:
      otlp:
        protocols:
          grpc:
            endpoint: 0.0.0.0:4317
    exporters:
      logging:
        loglevel: debug
      jaeger:
        endpoint: jaeger:14250
    service:
      pipelines:
        traces:
          receivers: [otlp]
          exporters: [logging, jaeger]
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: otel-collector
spec:
  replicas: 1
  selector:
    matchLabels:
      app: otel-collector
  template:
    metadata:
      labels:
        app: otel-collector
    spec:
      containers:
      - name: otel-collector
        image: otel/opentelemetry-collector-k8s:latest
        ports:
        - containerPort: 4317
        volumeMounts:
        - name: config
          mountPath: /etc/otel-collector-config.yaml
      volumes:
      - name: config
        configMap:
          name: otel-collector-config
---
apiVersion: v1
kind: Service
metadata:
  name: otel-collector
spec:
  ports:
  - port: 4317
    protocol: TCP
  selector:
    app: otel-collector
---
# Jaeger Deployment
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
        - containerPort: 14250
        - containerPort: 16686
---
apiVersion: v1
kind: Service
metadata:
  name: jaeger
spec:
  type: NodePort
  ports:
  - port: 14250
    protocol: TCP
    targetPort: 14250
  - port: 16686
    protocol: TCP
    targetPort: 16686
    nodePort: 30686
  selector:
    app: jaeger
```

## Configuration Examples

### Disable OTel for a Service

Set `ENABLE_OTEL: "false"` in the Kubernetes manifest for that service.

### Change Sampling Rate

Only sample 10% of requests:
```yaml
OTEL_TRACES_SAMPLER: "parentbased_traceidratio"
OTEL_TRACES_SAMPLER_ARG: "0.1"
```

### Export to Prometheus

```yaml
OTEL_EXPORTER_OTLP_PROTOCOL: "http/protobuf"
OTEL_EXPORTER_OTLP_ENDPOINT: "http://prometheus:4318"
```

## Troubleshooting

### Agent Not Loading

1. Check logs for agent initialization:
   ```bash
   kubectl logs <pod-name> | grep -i opentelemetry
   ```

2. Verify ENABLE_OTEL is set to "true":
   ```bash
   kubectl get pod <pod-name> -o jsonpath='{.spec.containers[0].env[?(@.name=="ENABLE_OTEL")].value}'
   ```

3. Check that agent JAR exists:
   ```bash
   kubectl exec -it <pod-name> -- ls -la /otel/agent/
   ```

### No Traces Appearing in Jaeger

1. Verify collector is reachable:
   ```bash
   kubectl exec -it <pod-name> -- curl http://otel-collector:4317
   ```

2. Check OTEL_EXPORTER_OTLP_ENDPOINT configuration
3. Verify sampling is enabled (default is `always_on`)
4. Check collector logs for errors

### High Memory Usage

The agent instruments many operations. To optimize:
1. Reduce sampling rate (see Configuration Examples)
2. Disable specific instrumentations:
   ```yaml
   OTEL_INSTRUMENTATION_JDBC_ENABLED: "false"
   ```
3. Reduce batch size:
   ```yaml
   OTEL_BSP_MAX_QUEUE_SIZE: "256"
   ```

## Performance Considerations

The OpenTelemetry agent has minimal overhead:
- **Memory**: ~50-100 MB per service
- **CPU**: <1% additional overhead (with sampling)
- **Network**: Depends on sampling rate and export endpoint

## Next Steps

1. **Set up Jaeger/Prometheus** for visualization
2. **Create dashboards** for key metrics
3. **Set up alerts** for error rates and latency
4. **Analyze traces** to identify bottlenecks
5. **Integrate with APM** (Datadog, New Relic, etc.)

## References

- [OpenTelemetry Java Agent GitHub](https://github.com/open-telemetry/opentelemetry-java-instrumentation)
- [OpenTelemetry Documentation](https://opentelemetry.io/docs/)
- [OpenTelemetry Java Configuration](https://opentelemetry.io/docs/instrumentation/java/automatic/)
- [Jaeger Getting Started](https://www.jaegertracing.io/docs/getting-started/)
- [OpenTelemetry Collector Documentation](https://opentelemetry.io/docs/collector/)

