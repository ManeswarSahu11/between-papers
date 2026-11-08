# Deployment

## Free hosting constraints

Three Render Docker web services were deployed on 8 November 2026 in Singapore,
all with `plan: free`, using the Render API. Existing unrelated services were
preserved. The agent runs `2873bfd38f98646141ec6f6ae65f5e21cad142e6`. The frontend
runs interface update `d060d7f45bbbb50e08ec0a2b2c5b54c996804e48`. The unchanged translator runs
`0e62affe945def11068fce93a97093595b7b75d3`.

| Component | Public endpoint |
| --- | --- |
| Workspace | https://between-papers.onrender.com |
| Agent health | https://between-papers-api.onrender.com/healthz |
| Translator health | https://between-papers-translator.onrender.com/healthz |

The homepage, frontend health, agent readiness, denied API access, PDF ingestion,
English and Spanish answers with source titles, French detection and French/Italian
translation passed live checks. See [validation](VALIDATION.md) for scope.

```mermaid
flowchart LR
    U[Public browser] --> F[Render Streamlit free service]
    F -->|HTTPS and service token| A[Render agent free service]
    A -->|HTTPS and service token| T[Render translator free service]
    A --> G[External Gemini API]
    A --> Z[External Zilliz collection]
    T --> GT[External Google Translate]
```

Environment values are set privately on the services. The local deployment key
stays in ignored `.env` and is not sent to application containers. Automatic
deployments are disabled; use Render to explicitly redeploy source changes after
checks pass. The repository can contain newer documentation than the deployed
runtime commit.

The inherited GKE manifests and Terraform describe an optional resource-consuming
deployment, not the live hosting infrastructure or a free hosting plan. Do not
apply them without checking costs in your own account.

The [Render free service documentation](https://render.com/docs/free) describes
idle spin-down and ephemeral storage. Checked 8 November 2026; service and
account limits can change and may differ by region. A persistent Milvus server
is not provided by a free Render web service. Hosting only the interface without
a working agent, credentials and database is not a complete deployment.

The live deployment uses a separately provisioned Zilliz vector service.
Reproducing this deployment needs a compatible vector service,
model API access within the account's free allowance, and hosting capacity for
the Python services. No paid plan is authorized. The original multi-service
architecture is retained rather than replaced with an undisclosed demo fallback.

## Containers

```sh
docker build -t research-agent:local agent-service
docker build -t research-translator:local Docker-NLP
docker build -t research-frontend:local frontend
```

Each Dockerfile starts the service on its declared port (8080, 8000, 8501).
Configure secrets using hosting environment settings. Never bake `.env` into an
image. The frontend image includes its Streamlit theme configuration.

## Existing Kubernetes option

```mermaid
flowchart LR
    Browser --> LB[Frontend LoadBalancer]
    LB --> UI[Streamlit pod]
    UI --> A[Internal agent service]
    A --> T[Internal translator service]
    A --> Alias[Milvus DNS alias]
    Alias --> M[Milvus Helm installation]
    A --> G[External Gemini API]
    T --> GT[External Google Translate]
    Secret[Cluster Secret] -.-> A
```

`milvus-gke/` installs Milvus into an **existing** Kubernetes cluster. It does not
create a GKE cluster. Several inherited variables are unused. The chart is not
version-pinned; validate it against the target cluster before applying. The
inherited Attu LoadBalancer is another externally exposed component.

`infra/k8s/` retains namespace `option1` to avoid silently migrating existing
resources. Image references now use local development tags instead of another
person's registry. Build and push images into your own registry, then replace
all three references with immutable image digests before rollout. Local tags are
not a production deployment configuration and may not be reachable by a cluster.
Create the real Secret privately; `secret.example.yaml` contains placeholders.

The APIs support a shared `API_ACCESS_TOKEN` sent through `X-API-Key`. Set the
same strong token on all services before exposing the APIs. It protects service
access, not individual users. There is no request quota or tenant isolation.
Uploaded papers are shared. Liveness `/healthz` confirms only the API process;
`/readyz` initializes provider clients and the Milvus collection but does not
prove a generation call will succeed. Frontend health is `/_stcore/health`.

## Release verification

1. Build each container and check its startup and health endpoint.
2. Verify missing-key and unavailable-database errors without disclosing secrets.
3. Upload a permission-cleared text PDF into a fresh test domain/collection.
4. Ask a question whose answer is in that paper; inspect returned titles and answer.
5. Exercise Spanish, French and Italian translation and provider failure handling.
6. Test the public homepage and core workflow on phone, tablet and desktop.
7. Record the deployment URL, service region, verified commit and known limitations.

No successful deployment should be inferred from configuration files alone.


## Render blueprint (alternative setup)

[`render.yaml`](../render.yaml) declares three Docker web services with `plan: free`
and one generated shared service token. Connect the repository in Render and use
the Blueprint flow. Set private Gemini and Milvus values when prompted. Set
`TRANSLATOR_BASE_URL` on the agent to the translator's public HTTPS URL, and
`AGENT_BASE_URL` on the frontend to the agent's public HTTPS URL. URLs must come
from the actual service creation results, not guessed hostnames.

Three active services share the account's free instance-hour allowance. Idle
spin-down can cause cold starts and timeouts; this architecture is not guaranteed
to run continuously within that allowance. Free memory limits may also be too
small for the agent plus its Python dependencies. Validate actual resource use
before claiming compatibility. Do not upgrade to a paid instance automatically.

The blueprint has been checked locally for YAML syntax and free-plan declarations.
The running services were created through the API rather than this Blueprint.
Their Docker images built and live workflows passed. Blueprint-flow acceptance
has not been independently tested.

## App name

The app is now branded Pagewise. Existing `between-papers` repository and Render
service identifiers are retained so existing URLs and service connections keep
working. The brand update does not rename collections or move stored documents.
