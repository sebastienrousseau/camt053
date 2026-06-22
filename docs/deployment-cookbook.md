# Deployment cookbook

End-to-end recipes for deploying the `camt053` REST API in
realistic environments, with the surrounding stack you'll
typically want next to it: a queue, a metric store, and a
dashboard.

The recipes are **opinionated minimums**: enough to be
production-shaped, small enough to read in one sitting. Adapt
network policies, secret management, and resource limits to your
environment.

## Contents

- [1. Local Docker Compose: REST API + Redis + Prometheus + Grafana](#1-local-docker-compose)
- [2. Single-host systemd: REST API behind nginx](#2-single-host-systemd)
- [3. Kubernetes: REST API + HPA + Prometheus ServiceMonitor](#3-kubernetes)
- [4. Cloud Run / Lambda one-off](#4-cloud-run--lambda-one-off)

## Common assumptions

Every recipe assumes:

- Python 3.12 (3.10 / 3.11 also supported).
- The REST API is `camt053.api.app:app` (a FastAPI ASGI app).
- TLS terminates at a reverse proxy (nginx, Cloud Load Balancer,
  ingress controller). The API itself runs HTTP on a local
  socket.
- Metrics are exposed at `/metrics` via the OpenTelemetry RED
  counters that ship with the `[telemetry]` extra
  (`pip install 'camt053[telemetry]'`).
- The audit log is written to a local append-only file unless
  you mount object storage at the configured path.

---

## 1. Local Docker Compose

The smallest "production-shaped" stack: REST API, Redis (for
rate-limiting + dedupe), Prometheus (scrapes `/metrics`),
Grafana (dashboards), all wired with a single
`docker compose up`.

### `compose.yaml`

```yaml
services:
  api:
    image: python:3.12-slim
    working_dir: /app
    command: >
      sh -c "pip install --no-cache-dir 'camt053[telemetry]' uvicorn[standard] &&
             uvicorn camt053.api.app:app --host 0.0.0.0 --port 8080"
    environment:
      CAMT053_AUDIT_LOG_PATH: /var/lib/camt053/audit.log
      OTEL_EXPORTER_OTLP_ENDPOINT: http://otel-collector:4317
      OTEL_SERVICE_NAME: camt053-api
    volumes:
      - audit-log:/var/lib/camt053
    ports:
      - "8080:8080"
    depends_on:
      - redis
    healthcheck:
      test: ["CMD", "python", "-c", "import urllib.request; urllib.request.urlopen('http://localhost:8080/health')"]
      interval: 10s
      timeout: 3s
      retries: 5
    restart: unless-stopped

  redis:
    image: redis:7-alpine
    command: ["redis-server", "--appendonly", "yes"]
    volumes:
      - redis-data:/data
    restart: unless-stopped

  prometheus:
    image: prom/prometheus:latest
    volumes:
      - ./prometheus.yml:/etc/prometheus/prometheus.yml:ro
      - prometheus-data:/prometheus
    ports:
      - "9090:9090"
    restart: unless-stopped

  grafana:
    image: grafana/grafana:latest
    environment:
      GF_SECURITY_ADMIN_PASSWORD: admin
    ports:
      - "3000:3000"
    volumes:
      - grafana-data:/var/lib/grafana
    restart: unless-stopped

volumes:
  audit-log:
  redis-data:
  prometheus-data:
  grafana-data:
```

### `prometheus.yml`

```yaml
global:
  scrape_interval: 15s
  evaluation_interval: 15s

scrape_configs:
  - job_name: camt053-api
    metrics_path: /metrics
    static_configs:
      - targets: ["api:8080"]
```

### Bring it up

```sh
docker compose up -d
# wait ~10 s for the API health check to flip green
curl -s http://localhost:8080/health
```

### Verify the RED metrics

```sh
curl -s http://localhost:9090/api/v1/query \
  --data-urlencode 'query=camt053_requests_total' \
  | jq '.data.result[] | {op: .metric.op, status: .metric.status, value: .value[1]}'
```

You should see counters for `parse`, `validate`, and `reverse`
operations.

### A minimal Grafana dashboard

Add Prometheus as a data source (URL: `http://prometheus:9090`),
then a panel with `rate(camt053_requests_total{status="ok"}[5m])`
and a second panel with `rate(camt053_requests_total{status="error"}[5m])`.
A third panel with the p99 latency from the
`camt053_request_duration_seconds_bucket` histogram closes the
loop on the **RED** triad (Rate, Errors, Duration).

---

## 2. Single-host systemd

For deployments that own their own VM. nginx terminates TLS
and proxies to a `uvicorn` worker pool managed by `systemd`.

### `/etc/systemd/system/camt053-api.service`

```ini
[Unit]
Description=camt053 REST API
After=network.target

[Service]
Type=notify
User=camt053
Group=camt053
WorkingDirectory=/srv/camt053
Environment=PATH=/srv/camt053/venv/bin
Environment=CAMT053_AUDIT_LOG_PATH=/var/lib/camt053/audit.log
Environment=OTEL_SERVICE_NAME=camt053-api
ExecStart=/srv/camt053/venv/bin/uvicorn camt053.api.app:app \
  --uds /run/camt053/api.sock \
  --workers 4 \
  --loop uvloop \
  --http httptools \
  --proxy-headers \
  --forwarded-allow-ips=127.0.0.1
Restart=on-failure
RestartSec=5
RuntimeDirectory=camt053
RuntimeDirectoryMode=0755
LimitNOFILE=65536
NoNewPrivileges=true
ProtectSystem=strict
ProtectHome=true
ReadWritePaths=/var/lib/camt053
PrivateTmp=true

[Install]
WantedBy=multi-user.target
```

### nginx site

```nginx
server {
  listen 443 ssl http2;
  server_name camt053.example.com;

  ssl_certificate     /etc/letsencrypt/live/camt053.example.com/fullchain.pem;
  ssl_certificate_key /etc/letsencrypt/live/camt053.example.com/privkey.pem;

  client_max_body_size 32m;          # large camt.053 payloads
  client_body_timeout  60s;

  location / {
    proxy_pass http://unix:/run/camt053/api.sock;
    proxy_set_header Host              $host;
    proxy_set_header X-Real-IP         $remote_addr;
    proxy_set_header X-Forwarded-For   $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;
    proxy_read_timeout 60s;
  }
}
```

### Bring it up

```sh
sudo useradd --system --home /srv/camt053 --shell /usr/sbin/nologin camt053
sudo install -d -o camt053 -g camt053 /srv/camt053 /var/lib/camt053
sudo -u camt053 python3 -m venv /srv/camt053/venv
sudo -u camt053 /srv/camt053/venv/bin/pip install 'camt053[telemetry]' 'uvicorn[standard]'
sudo systemctl daemon-reload
sudo systemctl enable --now camt053-api.service
sudo systemctl reload nginx
```

Tail logs with `journalctl -u camt053-api.service -f`.

---

## 3. Kubernetes

A `Deployment` + `Service` + `HorizontalPodAutoscaler` + a
`prometheus-operator` `ServiceMonitor`.

### `deployment.yaml`

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: camt053-api
  labels: { app: camt053-api }
spec:
  replicas: 3
  selector:
    matchLabels: { app: camt053-api }
  template:
    metadata:
      labels: { app: camt053-api }
    spec:
      securityContext:
        runAsNonRoot: true
        runAsUser: 1000
        runAsGroup: 1000
        fsGroup: 1000
      containers:
        - name: api
          image: ghcr.io/sebastienrousseau/camt053:0.0.6
          imagePullPolicy: IfNotPresent
          ports:
            - { name: http, containerPort: 8080 }
            - { name: metrics, containerPort: 8080 }
          env:
            - name: CAMT053_AUDIT_LOG_PATH
              value: /var/lib/camt053/audit.log
            - name: OTEL_SERVICE_NAME
              value: camt053-api
            - name: OTEL_EXPORTER_OTLP_ENDPOINT
              value: http://otel-collector.observability.svc:4317
          resources:
            requests: { cpu: 100m, memory: 256Mi }
            limits:   { cpu: 500m, memory: 512Mi }
          readinessProbe:
            httpGet: { path: /health, port: 8080 }
            initialDelaySeconds: 3
            periodSeconds: 5
          livenessProbe:
            httpGet: { path: /health, port: 8080 }
            initialDelaySeconds: 30
            periodSeconds: 15
          volumeMounts:
            - { name: audit, mountPath: /var/lib/camt053 }
          securityContext:
            allowPrivilegeEscalation: false
            readOnlyRootFilesystem: true
            capabilities: { drop: [ALL] }
      volumes:
        - name: audit
          persistentVolumeClaim: { claimName: camt053-audit }
```

### `hpa.yaml`

```yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata: { name: camt053-api }
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: camt053-api
  minReplicas: 3
  maxReplicas: 20
  metrics:
    - type: Resource
      resource: { name: cpu, target: { type: Utilization, averageUtilization: 70 } }
```

### `servicemonitor.yaml`

```yaml
apiVersion: monitoring.coreos.com/v1
kind: ServiceMonitor
metadata:
  name: camt053-api
  labels: { release: kube-prometheus-stack }
spec:
  selector: { matchLabels: { app: camt053-api } }
  endpoints:
    - port: http
      path: /metrics
      interval: 30s
```

### Bring it up

```sh
kubectl apply -f deployment.yaml -f hpa.yaml -f servicemonitor.yaml
kubectl rollout status deploy/camt053-api
```

---

## 4. Cloud Run / Lambda one-off

For workloads that don't need always-on capacity (audit one-off
batches, scheduled reconciliation jobs).

### Cloud Run

```sh
gcloud run deploy camt053-api \
  --image=ghcr.io/sebastienrousseau/camt053:0.0.6 \
  --port=8080 \
  --set-env-vars="CAMT053_AUDIT_LOG_PATH=/tmp/audit.log,OTEL_SERVICE_NAME=camt053-api" \
  --memory=512Mi --cpu=1 \
  --concurrency=20 \
  --max-instances=10 \
  --allow-unauthenticated=false
```

The audit log under `/tmp` is ephemeral; for retention, stream
to a logging sink or mount Cloud Storage via Cloud Run's
volume mount feature.

### AWS Lambda (ASGI via Mangum)

```python
# handler.py
from mangum import Mangum
from camt053.api.app import app

handler = Mangum(app, lifespan="off")
```

Package with:

```sh
pip install --target package camt053 mangum
cd package && zip -r ../bundle.zip . && cd ..
zip bundle.zip handler.py
aws lambda update-function-code \
  --function-name camt053-api \
  --zip-file fileb://bundle.zip
```

Front Lambda with API Gateway HTTP API; configure the audit log
path to `/tmp/audit.log` (the only writable location).

---

## Recipes you'll likely want next

These are intentionally out of scope here, but flagged for your
roadmap:

- **Tier-0 rate-limiting** at the reverse proxy (nginx
  `limit_req_zone`, Cloudflare Rules, AWS WAF) — every
  ISO 20022-shaped POST is a XSD-validation operation; bound it.
- **Body-size hard cap** at the reverse proxy. The library is
  hardened against 1 GiB inputs but you shouldn't let one in.
- **`X-Forwarded-For` reconciliation** if you front the API with
  multiple proxies; the audit log records the apparent client
  address.
- **Audit-log shipping** to immutable object storage
  (S3 Object Lock, GCS Bucket Lock, Azure Immutable Blob) for
  regulatory retention.
- **Replay sigstore attestation verification** on every container
  pull (`gh attestation verify` or `cosign verify-attestation`).
  Every release artefact carries SLSA Build L3 provenance.
