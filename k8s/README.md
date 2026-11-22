# Deploying SearchSphere to Kubernetes

These manifests stand up the same three services as `docker-compose.yml`
(Postgres, Redis, the FastAPI app), plus the probes, resource limits, and
config/secret separation `docker-compose` doesn't need to care about.

## Prerequisites

- A cluster you can `kubectl apply` to (`kind`/`minikube` locally, or a
  real cluster). `kustomize` support is built into `kubectl` 1.14+.
- The API image pushed somewhere the cluster can pull from. CI already
  builds and pushes `ghcr.io/nikanwar3/searchsphere` on every push to
  `main` (see `.github/workflows/ci-cd.yml`); point `k8s/kustomization.yaml`
  at that image, or build+load a local image into `kind`/`minikube` instead.

## Deploy

```bash
# 1. Namespace + ConfigMap + Postgres + Redis + API Deployment/Service
kubectl create secret generic searchsphere-secrets \
  --namespace searchsphere --dry-run=client -o yaml \
  --from-literal=DATABASE_URL='postgresql+psycopg://searchsphere:<password>@searchsphere-postgres:5432/searchsphere' \
  --from-literal=REDIS_URL='redis://searchsphere-redis:6379/0' \
  --from-literal=POSTGRES_PASSWORD='<password>' \
  | kubectl apply -f -   # namespace must exist first: kubectl apply -f k8s/namespace.yaml

kubectl apply -k k8s/

# 2. Check rollout
kubectl -n searchsphere rollout status deployment/searchsphere-api

# 3. Reach it
kubectl -n searchsphere port-forward svc/searchsphere-api 8000:80
curl localhost:8000/health
```

To point at a freshly-built image instead of `:latest` (what CD does
automatically):

```bash
cd k8s && kustomize edit set image ghcr.io/nikanwar3/searchsphere=ghcr.io/nikanwar3/searchsphere:<commit-sha>
```

## Why the API Deployment is pinned to `replicas: 1`

The in-memory `IndexManager` (inverted index + trie, see
`app/services/index_manager.py`) is rebuilt from Postgres once per
process, on startup, and lives only in that process's memory after that.
Running more than one API pod today means a document ingested through one
pod is invisible to searches landing on another pod until that pod
restarts — the root README's
["Limitations & future scaling work"](../README.md#limitations--future-scaling-work)
section covers this in depth and lays out the fix (Pub/Sub index-delta
broadcast, then sharded ownership). Bump `replicas` (or add an HPA) only
after one of those lands; until then, scale the single pod vertically via
the `resources` block instead.

## What's intentionally not here

- **No Secret committed.** `secret.example.yaml` is a template; create the
  real `searchsphere-secrets` Secret with `kubectl create secret generic`
  (above) so credentials never touch git history.
- **No managed Postgres/Redis.** `postgres.yaml`/`redis.yaml` are
  self-contained Deployments so the whole stack is reproducible with one
  command on a demo cluster. A real production deploy would point
  `DATABASE_URL`/`REDIS_URL` at a managed instance (RDS/Cloud SQL/
  ElastiCache/etc.) instead and drop those two manifests from the
  kustomization.
- **Ingress is opt-in.** `ingress.yaml` assumes an `ingress-nginx`
  controller is already installed; it's commented out of
  `kustomization.yaml`'s resource list so a bare cluster doesn't fail to
  apply. Uncomment it, or use `port-forward`/a `LoadBalancer` Service
  instead.
