# Auto Ontology v1 Semantic Layer for AI Agents — Railway template spec

## Listing

| Field | Value |
|---|---|
| Name | **Auto Ontology v1 Semantic Layer for AI Agents** (`v1` = major of the pinned release `1.1.0`; no "NVIDIA" in the name: community template) |
| Description | Semantic layer and NL-to-SQL for AI agents: MCP server, API and web UI. (71 chars) |
| Category | AI/ML |
| Tags | auto-ontology, semantic-layer, text-to-sql, nl-to-sql, mcp, ai-agents, ontology, pgvector |
| Icon | `https://cdn.jsdelivr.net/npm/lucide-static@1.59.0/icons/network.svg` (neutral Lucide icon, ISC; no NVIDIA logo) |
| Repo | `baranberkay96/auto-ontology-railway`, services in `/services/<svc>` |
| User input at deploy | **One:** `DEFAULT_MODELS_API_KEY` on Backend (NVIDIA API key `nvapi-...`, free from build.nvidia.com). Everything else is generated or defaulted. |

The listing is delivered as written: "semantic layer" = the ontology/catalog Auto Ontology compiles over connected databases; "NL-to-SQL" = the chat and `/api/chat/completions`; "MCP server" = the MCP Server service, signed in through Auto Ontology's own OAuth (Better Auth); "API" = the authenticated Next.js API with API tokens; "web UI" = Frontend. The Chinook sample database makes the first question work without connecting anything.

## Base market templates

Checked 2026-11-03 (data supplied with the task): **no Auto Ontology template exists on Railway.** Nearest neighbours: "Ontology Browser" (6 active projects), WrenAI and Vanna (0 active). None deploys Auto Ontology, so Rule 1 has nothing to start from; the package is built from upstream's `docker-compose.yml`, the Helm chart `helm/auto-ontology` and the three published images. No market files or text were used.

## Pinned versions

| Service | Source | Version | Built / released | Checked |
|---|---|---|---|---|
| Backend | `nvcr.io/nvidia/auto-ontology:1.1.0@sha256:d6d50ee5…aef57b` (index; amd64 `sha256:ada247f0…581563`) | 1.1.0 | 2026-10-08 | 2026-11-03 |
| Ingestion | same image (`AUTO_ONTOLOGY_IMAGE` build argument) + `services/ingestion` wrapper | 1.1.0 | 2026-10-08 | 2026-11-03 |
| Frontend | `nvcr.io/nvidia/auto-ontology-frontend:1.1.0@sha256:c45cbd9a…716b97` (amd64 `sha256:95ec9069…d36ab`) | 1.1.0 | 2026-10-08 | 2026-11-03 |
| MCP Server | `nvcr.io/nvidia/auto-ontology-mcp:1.1.0@sha256:3b8f9e57…cfcaa26` (amd64 `sha256:8d41beb4…5af1d2`) | 1.1.0 (FastMCP 3.4.7) | 2026-10-08 | 2026-11-03 |
| Postgres | `ghcr.io/railwayapp-templates/postgres-ssl:18` (Railway base; index `sha256:4fc833b4…7c863` on 2026-11-03) | PostgreSQL 18.6, pgvector 0.8.* | image 2026-10-23 | 2026-11-03 |
| Sample Data | same image + Chinook 1.4.5 (`lerocha/chinook-database@7f677725`, SHA-256 `e3fde5c1…03db695e`) | Chinook 1.4.5 | 2024-02 (data) | 2026-11-03 |

- Upstream has no GitHub releases or tags. `pyproject.toml`, `mcp/pyproject.toml`, `frontend/package.json` and `helm/auto-ontology/Chart.yaml` all say 1.1.0. Releases are built by `.github/workflows/release-docker.yml` from `release/vX.Y` branches; the 1.1.0 images were created 2026-10-08 15:41–15:44 UTC, four minutes after the head of `release/v1.1.0` (`d14214e9`, 2026-10-08 15:38). The Python code in the backend image layer is byte-identical to that branch (`diff -r` of the extracted `auto_ontology/` layer), as is the MCP package. `main` (checked at `6c4fb71e`, 2026-11-02) is 114 commits ahead; this template follows the published release, not `main`.
- All three images pull anonymously (token from `https://nvcr.io/proxy_auth?scope=repository:<repo>:pull`, then manifest HEAD = 200) and are multi-arch (amd64 + arm64).
- **One version per deployment:** Backend, Ingestion (`AUTO_ONTOLOGY_IMAGE`), Frontend and MCP Server must run the same release. The Ingestion wrapper waits for the schema revision its image ships and logs the mismatch if they differ.

## Architecture

```
Internet ─HTTPS─▶ Frontend (Next.js 16, Better Auth, the only web/API entry)        public :3000
                    │  session cookie / x-api-key / OAuth bearer → resolves the user
                    ├─ PYTHON_API_URL ─▶ Backend (FastAPI :3001, trusts x-auto-ontology-user-id)  private
                    │                      └─ INGESTION_SERVICE_URL ─▶ Ingestion (FastAPI :3002)   private
                    └─ Prisma ─▶ Postgres schema `frontend` (users, sessions, API keys, OAuth clients, settings)
Internet ─HTTPS─▶ MCP Server (FastMCP :3003, /mcp)                                    public :3003
                    └─ every call ─HTTPS─▶ Frontend public URL (UserInfo check, then the API as the signed-in user)
Backend + Ingestion ─▶ Postgres (pgvector): schema `public` (Alembic: catalog, semantic layer), `vdb` (embeddings, halfvec HNSW)
Ingestion ─read-only─▶ Sample Data (Postgres 18, database `chinook`, login ao_reader)  private
Backend + Ingestion ─HTTPS─▶ NVIDIA API catalog (chat, embeddings, reranking) or any configured endpoint
```

## Design decisions (verified in the 1.1.0 sources and image layers)

### Prebuilt images, runtime configuration only

- **Frontend `PYTHON_API_URL` is not baked in.** The Dockerfile comment and `release-docker.yml` still say it is "baked into the Next.js rewrites", but `next.config.ts` at `release/v1.1.0` has *no* `rewrites()` (every `/api/*` path is a permission-gated route handler that forwards with `fetch`). The compiled standalone bundle in the image (`/app/app/.next/server`, layer `sha256:0c8264cc…`, downloaded and grepped) reads `process.env.PYTHON_API_URL ?? "http://127.0.0.1:3001"` at runtime in every route, and contains no `auto-ontology:3001` or `localhost:3000` literal. `APP_URL`, `AUTH_SECRET`, `AUTO_ONTOLOGY_MCP_PUBLIC_URL`, the admin seed and `POSTGRES_*` are also read at runtime (`auth/auth.ts`, `lib/prisma.ts`, `instrumentation.ts`). The Helm chart sets `PYTHON_API_URL` as a runtime env too. So the published image is used as is; no source build needed.
- **Backend and MCP have no build-time values** (`ENV` in the image config: `PORT=3001`; MCP `AUTO_ONTOLOGY_MCP_HOST=0.0.0.0`, `AUTO_ONTOLOGY_MCP_PORT=3003`); all settings are environment variables.
- Railway's start command replaces the image ENTRYPOINT (exec form, per Railway docs), so no service overrides the start command except Postgres (Railway base pattern) and every pre-deploy command is a full path under `/bin/sh -c`.

### Migrations before the processes that need them

- **Alembic (`public` schema):** Backend pre-deploy `/bin/sh -c 'cd /app || exit 1; i=1; until /usr/local/bin/entrypoint.sh migrate; do … sleep 10; done'` (60 attempts, `preDeployTimeoutSeconds` 900). `entrypoint.sh migrate` is the image's own `exec alembic upgrade head`; Alembic applies each revision in a transaction and records it, so every redeploy is a no-op once current. The retry loop covers Postgres still starting (Rule 8.5/8.6).
- **Prisma (`frontend` schema):** Frontend pre-deploy runs the image's own `/app/migrate/prisma/migrate.sh` (creates the schema, the guarded `conversation_analytics` cleanup, `prisma db push` without `--accept-data-loss`) in the same retry loop. It runs before the Next.js server starts, so `instrumentation.ts` always finds `frontend.user` when it seeds the admin (otherwise the seed fails once and only retries on the next start; the Helm chart needs an init container for the same reason).
- **Ingestion** refuses to start against an unexpected schema (`require_current_schema()` in its lifespan). It only reads the schema, so instead of migrating twice it waits (`services/ingestion/railway-ingestion.py`) until `public.alembic_version` equals the head revision its image ships (`b3aed65e49b7` in 1.1.0), up to `TEMPLATE_STARTUP_WAIT_SECONDS` (900 s, below the 1200 s healthcheck window), then exits 1 so Railway restarts it.
- Ordering between the two migrations does not matter (they own different schemas; upstream compose says the same).

### Admin account, sign-up closed

- `auth/auth.ts` (1.1.0): `emailAndPassword: { enabled: true, disableSignUp: true }` — self-service sign-up is off upstream, so no first visitor can claim the instance. `auth/seed-admin.ts` creates (or resets the password of) `AUTO_ONTOLOGY_ADMIN_EMAIL` with `AUTO_ONTOLOGY_ADMIN_PASSWORD` on every start, email-verified, role admin. The template defaults the email to `admin@example.com` and generates the password with `secret(24)`; rotation = change the variable and redeploy Frontend.
- Further users in 1.1.0: SSO (Settings → SSO; redirect URI `{APP_URL}/api/auth/sso/callback`; SSO users join as viewers) or Better Auth's admin endpoint `POST /api/auth/admin/create-user` from an admin session (the admin role carries Better Auth's `user:create`; 1.1.0 has no UI for it). Invitations exist on upstream `main` only (post-1.1.0).
- `AUTH_SECRET` = `secret(48)`; `APP_URL` = `https://${{RAILWAY_PUBLIC_DOMAIN}}` of Frontend (Better Auth `baseURL`, trusted origin, OAuth issuer).
- Backend and Ingestion get **no public domain and no TCP proxy**: the Backend trusts the `x-auto-ontology-user-id` header set by the Next.js gateway, and the Ingestion API is unauthenticated. Both bind `0.0.0.0` (hardcoded in `auto_ontology/server/__main__.py` and `ingestion_service/__main__.py`), which also satisfies Railway's IPv4 healthcheck (Rule 8.2).

### MCP server, signed in through Auto Ontology

- `mcp/auto_ontology_mcp/auto_ontology_auth.py`: FastMCP `RemoteAuthProvider` with `authorization_servers=[AUTO_ONTOLOGY_API_URL]`; tokens are opaque and checked on every call against `{AUTO_ONTOLOGY_API_URL}/api/auth/oauth2/userinfo`, then forwarded to the public API as the signed-in user. Clients (Cursor, Claude, the MCP SDK) register themselves (dynamic client registration) and the user signs in on Auto Ontology's normal login page.
- Because the URL is handed to MCP clients as the authorization server, `AUTO_ONTOLOGY_API_URL` must be the **public** Frontend URL (`${{Frontend.APP_URL}}`), not the private domain; tool calls therefore leave and re-enter Railway (small egress).
- Better Auth binds MCP access tokens to `${AUTO_ONTOLOGY_MCP_PUBLIC_URL}/mcp` (`mcp({ resource })` in `auth/auth.ts`), and FastMCP advertises the same resource. The value lives once on Frontend (`https://${{MCP Server.RAILWAY_PUBLIC_DOMAIN}}`) and MCP Server references it, so they cannot drift; a custom domain is changed on Frontend only.
- Healthcheck `/.well-known/oauth-protected-resource/mcp` (RFC 9728 metadata route created by `mcp` 1.29 `create_protected_resource_routes`, unauthenticated, no upstream dependency). `/mcp` itself answers 401 without a token.

### Sample data (Chinook) so the first question works

- The chat refuses to answer until the semantic layer exists (`server/chat/router.py`: 409 "The semantic layer hasn't been created yet"), and semantic compilation is opt-in (`ingestion_service/config.py`: absent row = off). A fresh upstream install therefore needs: a source database, an ingest, the Semantic Compilation toggle, and a compile.
- **Chinook** (digital media store: artists, albums, 3,503 tracks, 59 customers, 412 invoices 2021–2025, 11 tables; MIT licence, Luis Rocha) is small, well known for text-to-SQL demos, and cheap to compile. Pagila (PostgreSQL licence) was the alternative; it is larger (partitioned payments, full-text columns), so compiling it costs more model calls on a rate-limited trial key.
- `services/sample-data`: Railway's Postgres 18 image; the build downloads the Chinook PostgreSQL script from a commit URL and checks its SHA-256; `load-chinook.sh` (first boot only) loads it into `POSTGRES_DB=chinook` (the script's own `DROP/CREATE DATABASE`/`\c` header is removed and the remainder checked) and creates `ao_reader`: `SELECT` on the Chinook tables only, `default_transaction_read_only=on`, `statement_timeout=120s`, `CONNECT` revoked from `PUBLIC` on `chinook` and `postgres`. Tested locally against PostgreSQL 15: load 0.4 s, 11 tables; the reader can select, cannot write even after `SET default_transaction_read_only=off` (no privilege), cannot open `postgres`; guard cases (extra `CREATE DATABASE`, `\connect`, changed header) fail the boot.
- **Why not `CONNECTION_STRINGS`:** when it is set, `GET /api/connections/source` reports env-managed connections and the Settings → Connections page is hidden (`app/settings/connections/page.tsx` redirects), so users could not add their own database in the UI. Instead the Ingestion wrapper registers the sample once as an ordinary UI-managed connection — the same `catalog_database.connection` row `create_connection` writes (`auto_ontology.dal.connections.insert_connection`; Vault honoured if configured), after the same connector check the Settings "Test" button runs. The startup ingest pass then picks it up (`DataScheduler` reloads connections from the catalog each pass), and an admin can edit or delete it like any other connection. `CONNECTION_STRINGS` stays available (empty by default); if set, the sample step is skipped.
- **Semantic compilation on at first boot:** the wrapper inserts `frontend.configurations(semantic_compilation_enabled=true)` *only if the row is absent* (`ON CONFLICT DO NOTHING`), before the service starts, so the lifespan starts the semantic scheduler, which waits for the first ingest pass. Both first-boot steps are recorded in `railway_template.first_boot` (its own schema: Alembic only manages `public`, Prisma only `frontend`) under a Postgres advisory lock and never repeat; any failure is logged and the service starts anyway. Turning compilation off later in the UI sticks. Set `TEMPLATE_SAMPLE_CONNECTION=false` / `TEMPLATE_ENABLE_SEMANTIC_COMPILATION=false` before the first deploy to get upstream's empty, opt-in behaviour.
- Wrapper logic was tested with in-memory fakes of psycopg and the image internals (25 cases: fresh boot, second boot, existing connections, `CONNECTION_STRINGS`, unreachable/late sample DB, schema never/late ready, missing variables, Vault, missing settings table, failing connector check, invalid variables, self-test); its SQL (advisory lock, marker table, settings insert, `to_regclass`) ran against local PostgreSQL 15. The Docker build runs `railway-ingestion --self-test`, which imports every internal it uses and reads the Alembic head, so a future base image that drops one fails the build.

### Models and the one required input

- `auto_ontology/utils/model_config.py`: every role (`REASONING`, `NON_REASONING`, `EMBED`, `RERANK`) is an `<PREFIX>_ENDPOINT/_API_KEY/_MODEL` triplet falling back field by field to `DEFAULT_MODELS_*`. Upstream warns that an unset `EMBED_*` would fall back to the *chat* model once `DEFAULT_MODELS_MODEL` is set, so the template sets every endpoint/model explicitly to upstream's `.env.example` defaults and leaves the per-role keys unset (they use `DEFAULT_MODELS_API_KEY`). Values live on Backend; Ingestion references them.
- Chat roles use `ChatOpenAI` for `openai/`, `azure/`, `aws/` model prefixes and `ChatNVIDIA` otherwise (OpenAI-compatible `/chat/completions`), so `REASONING_*` / `NON_REASONING_*` can point at any OpenAI-compatible endpoint. Embeddings (`nemo_retriever` NIM embed client) and reranking (`/reranking` API) expect NVIDIA NIM-compatible endpoints (API catalog or self-hosted NIM); the pgvector table is created for 2048-dimension embeddings (`vdb/postgres.py`), so changing the embedding model means a re-ingest and possibly a code-level change.

### Sizing and concurrency

- `LLM_MAX_INFLIGHT=6` (Backend, referenced by Ingestion): upstream's `.env.example` documents 6 as the cap that stays under the hosted endpoint's per-worker limit (HTTP 503 beyond); upstream's code default is unbounded. `SEMANTIC_LLM_MAX_INFLIGHT=6`, `PII_LLM_MAX_WORKERS=6` (upstream defaults, explicit so they can be lowered on a rate-limited key). `LLM_INVOKE_TIMEOUT_S=120`.
- `OMP_NUM_THREADS=4` on Backend and Ingestion: numpy/onnxruntime (pulled in by `nemo-retriever`) otherwise size thread pools from the host's cores (Rule 8.15).
- Ingest itself uses 4 worker threads (`catalog/ingest.py`), the embed client batches 32 × 32 concurrent requests and retries 429s with backoff (`utils/embedding.py`).
- Postgres: the 56-pgvector container-aware tuning (shared_buffers, maintenance_work_mem for the halfvec HNSW build, parallel workers from the cgroup quota) and `/dev/shm` 1 GiB.

### Things deliberately left out

- **pgAdmin** (Railway has a Data panel), **HashiCorp Vault** (optional upstream; without it connection credentials are stored in plaintext JSON on the catalog row — README says so), **Neo4j-backed checks** (`DB_PROBE_JOIN_PATH_CHECK`, `HUB_SIBLING_EXPANSION_ENABLED`; off by default upstream, and 1.1.0 has no Neo4j service in compose or Helm), **KumoRFM** (off unless `KUMO_RFM_API_KEY` is set), **backups** (Railway volume backups cover Postgres; a `pg_dump` cron like 56-pgvector could be added later).

## Services

Create in this order. Values are entered exactly as shown (Railway resolves `${{...}}`).

### Postgres

- **Source:** image `ghcr.io/railwayapp-templates/postgres-ssl:18` (Railway base)
- **Start command:** the 56-pgvector tuning command (2,604 chars; readable source `services/postgres/pgvector-tune.sh`, regenerate/check with `python3 services/postgres/to-start-command.py --check`)
- **Volume:** `/var/lib/postgresql/data` · **Healthcheck:** none (TCP) · **Public domain / TCP proxy:** none · **Restart:** ON_FAILURE (10)

| Variable | Value | Description |
|---|---|---|
| `PGDATA` | `/var/lib/postgresql/data/pgdata` | Data directory inside the volume (Railway base layout; the image refuses anything outside /var/lib/postgresql/data). |
| `PGHOST` | `${{RAILWAY_PRIVATE_DOMAIN}}` | Private hostname of this database (postgres.railway.internal), used by the Data panel and the other services. |
| `PGPORT` | `5432` | Postgres port. |
| `PGUSER` | `${{POSTGRES_USER}}` | User for the Data panel and the other services. |
| `PGPASSWORD` | `${{POSTGRES_PASSWORD}}` | Password for the Data panel and the other services. |
| `PGDATABASE` | `${{POSTGRES_DB}}` | Database for the Data panel and the other services. |
| `POSTGRES_USER` | `postgres` | Superuser created on first boot. |
| `POSTGRES_PASSWORD` | `${{ secret(32, "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ") }}` | Superuser password, generated at deploy (letters only: the app builds URLs from it without escaping). Changing it later needs ALTER USER too. |
| `POSTGRES_DB` | `railway` | Database created on first boot; the vector and pg_stat_statements extensions are created in it. |
| `DATABASE_URL` | `postgresql://${{PGUSER}}:${{POSTGRES_PASSWORD}}@${{RAILWAY_PRIVATE_DOMAIN}}:5432/${{PGDATABASE}}` | Private connection string (Railway convention). |
| `SSL_CERT_DAYS` | `820` | Validity of the self-signed TLS certificate. |
| `RAILWAY_DEPLOYMENT_DRAINING_SECONDS` | `60` | Time Postgres gets to shut down cleanly on redeploy. |
| `RAILWAY_SHM_SIZE_BYTES` | `1073741824` | Size of /dev/shm (1 GiB; Railway default 64 MB) for parallel HNSW index builds and parallel queries; only memory in use is billed. |
| `PGVECTOR_TUNING` | `auto` | auto = size memory and parallelism from the container limits at every boot; off = Postgres defaults. |
| `PG_MEMORY_LIMIT_MB` | `auto` | RAM the tuning plans for. auto = the container limit capped at 8192 MB. |
| `PG_CPU_LIMIT` | `auto` | CPUs the tuning plans for. auto = the container CPU quota capped at 8. |

### Backend

- **Source:** image `nvcr.io/nvidia/auto-ontology:1.1.0@sha256:d6d50ee5fb3617dce218ea9706e737c181e3eb6afcaf15cd954364a341aef57b`
- **Start command:** image default (`tini -- entrypoint.sh server` → `python -m auto_ontology.server`, 0.0.0.0:3001)
- **Pre-deploy:** `/bin/sh -c 'cd /app || exit 1; i=1; until /usr/local/bin/entrypoint.sh migrate; do if [ "$i" -ge 60 ]; then echo "[railway] alembic upgrade failed 60 times, giving up" >&2; exit 1; fi; echo "[railway] alembic upgrade attempt $i failed (Postgres still starting?), retrying in 10 s" >&2; i=$((i+1)); sleep 10; done'` (timeout 900 s)
- **Healthcheck:** `/api/health` (Postgres + schema revision; timeout 600 s) · **Public domain:** none (never add one) · **Restart:** ALWAYS

| Variable | Value | Description |
|---|---|---|
| `PORT` | `3001` | Port Railway health-checks (the API server always listens on 0.0.0.0:3001). Never add a public domain: this service trusts the x-auto-ontology-user-id header from the Frontend. |
| `APP_VERSION` | `1.1.0` | Version shown in logs (matches the pinned image). |
| `POSTGRES_HOST` | `${{Postgres.PGHOST}}` | Postgres private host (pgvector database for the catalog, auth tables and embeddings). |
| `POSTGRES_PORT` | `${{Postgres.PGPORT}}` | Postgres port. |
| `POSTGRES_USER` | `${{Postgres.PGUSER}}` | Postgres user. |
| `POSTGRES_PASSWORD` | `${{Postgres.PGPASSWORD}}` | Postgres password. |
| `POSTGRES_DATABASE` | `${{Postgres.PGDATABASE}}` | Database holding the public (Alembic), frontend (Prisma) and vdb (pgvector) schemas. |
| `INGESTION_SERVICE_URL` | `http://${{Ingestion.RAILWAY_PRIVATE_DOMAIN}}:3002` | Ingestion service on the private network (ingest and semantic compilation triggers). |
| `DEFAULT_MODELS_API_KEY` | *(empty)* | **Required.** NVIDIA API key (nvapi-...), free from build.nvidia.com; used by every model below unless REASONING_API_KEY, NON_REASONING_API_KEY, EMBED_API_KEY or RERANK_API_KEY is set. Hosted endpoints are governed by NVIDIA's API trial terms. |
| `DEFAULT_MODELS_ENDPOINT` | `https://integrate.api.nvidia.com/v1` | Shared default endpoint (OpenAI-compatible) for any model field left unset. |
| `DEFAULT_MODELS_MODEL` | `nvidia/nemotron-3-ultra-550b-a55b` | Shared default model for any model field left unset (upstream 1.1.0's id was retired; see below). |
| `REASONING_ENDPOINT` | `https://integrate.api.nvidia.com/v1` | Main chat / NL-to-SQL model endpoint. Any OpenAI-compatible chat endpoint works; set REASONING_API_KEY for another provider. |
| `REASONING_MODEL` | `nvidia/nemotron-3-ultra-550b-a55b` | Main chat / NL-to-SQL model (upstream 1.1.0's id was retired; see below). |
| `NON_REASONING_ENDPOINT` | `https://integrate.api.nvidia.com/v1` | Lighter model endpoint (entity extraction). OpenAI-compatible; set NON_REASONING_API_KEY for another provider. |
| `NON_REASONING_MODEL` | `nvidia/nemotron-3-ultra-550b-a55b` | Lighter model (upstream 1.1.0's id was retired; see below). |
| `EMBED_ENDPOINT` | `https://integrate.api.nvidia.com/v1` | Embedding endpoint (NVIDIA NIM API). Ingest and query must use the same model; changing it needs a re-ingest. |
| `EMBED_MODEL` | `nvidia/nemotron-3-embed-1b` | Embedding model (upstream default; the vector table is created for 2048 dimensions). |
| `RERANK_ENDPOINT` | `https://ai.api.nvidia.com/v1/retrieval/nvidia/llama-nemotron-rerank-vl-1b-v2/reranking` | Reranking endpoint (NVIDIA NIM reranking API). |
| `RERANK_MODEL` | `nvidia/llama-nemotron-rerank-vl-1b-v2` | Reranking model (upstream 1.1.0's id was retired; see below). |
| `CONNECTION_STRINGS` | *(empty)* | Optional. Comma-separated source database URLs (postgresql://user:pass@host:5432/db, snowflake://..., ...). When set, connections come only from here and the Connections settings page is hidden. Leave empty to manage connections in the UI. |
| `LLM_MAX_INFLIGHT` | `6` | Max concurrent model requests per process (0 = unbounded). 6 stays under the hosted endpoint's per-key concurrency; lower it if you see HTTP 429/503. |
| `LLM_INVOKE_TIMEOUT_S` | `120` | Timeout per model call, in seconds. |
| `OMP_NUM_THREADS` | `4` | Caps native thread pools (numpy, onnxruntime) to the service's CPU share instead of the host's core count. |
| `RAILWAY_DEPLOYMENT_DRAINING_SECONDS` | `30` | Seconds between SIGTERM and SIGKILL on redeploy (lets running chat turns finish). |

### Ingestion

- **Source:** repo `baranberkay96/auto-ontology-railway`, root `/services/ingestion` (Dockerfile `FROM ${AUTO_ONTOLOGY_IMAGE}` + `railway-ingestion.py`)
- **Start command:** image default (`tini -- railway-ingestion` → waits for the schema, first-boot steps, then `exec python -m auto_ontology.ingestion_service`, 0.0.0.0:3002)
- **Healthcheck:** `/health` (Postgres + schema; timeout 1200 s) · **Public domain:** none (never add one) · **Restart:** ALWAYS · **Replicas:** 1 (the 24 h schedulers run per process)

| Variable | Value | Description |
|---|---|---|
| `AUTO_ONTOLOGY_IMAGE` | `nvcr.io/nvidia/auto-ontology:1.1.0@sha256:d6d50ee5fb3617dce218ea9706e737c181e3eb6afcaf15cd954364a341aef57b` | Base image for this service's Docker build (Railway passes it as a build argument). Must match the Backend service's image. |
| `PORT` | `3002` | Port Railway health-checks. |
| `INGESTION_PORT` | `3002` | Port the ingestion service listens on (0.0.0.0, private network only). |
| `APP_VERSION` | `1.1.0` | Version shown in logs (matches the pinned image). |
| `POSTGRES_HOST` | `${{Postgres.PGHOST}}` | Postgres private host (pgvector database for the catalog, auth tables and embeddings). |
| `POSTGRES_PORT` | `${{Postgres.PGPORT}}` | Postgres port. |
| `POSTGRES_USER` | `${{Postgres.PGUSER}}` | Postgres user. |
| `POSTGRES_PASSWORD` | `${{Postgres.PGPASSWORD}}` | Postgres password. |
| `POSTGRES_DATABASE` | `${{Postgres.PGDATABASE}}` | Database holding the public (Alembic), frontend (Prisma) and vdb (pgvector) schemas. |
| `DEFAULT_MODELS_API_KEY` | `${{Backend.DEFAULT_MODELS_API_KEY}}` | Same as DEFAULT_MODELS_API_KEY on Backend (change it there). |
| `DEFAULT_MODELS_ENDPOINT` | `${{Backend.DEFAULT_MODELS_ENDPOINT}}` | Same as DEFAULT_MODELS_ENDPOINT on Backend (change it there). |
| `DEFAULT_MODELS_MODEL` | `${{Backend.DEFAULT_MODELS_MODEL}}` | Same as DEFAULT_MODELS_MODEL on Backend (change it there). |
| `REASONING_ENDPOINT` | `${{Backend.REASONING_ENDPOINT}}` | Same as REASONING_ENDPOINT on Backend (change it there). |
| `REASONING_MODEL` | `${{Backend.REASONING_MODEL}}` | Same as REASONING_MODEL on Backend (change it there). |
| `NON_REASONING_ENDPOINT` | `${{Backend.NON_REASONING_ENDPOINT}}` | Same as NON_REASONING_ENDPOINT on Backend (change it there). |
| `NON_REASONING_MODEL` | `${{Backend.NON_REASONING_MODEL}}` | Same as NON_REASONING_MODEL on Backend (change it there). |
| `EMBED_ENDPOINT` | `${{Backend.EMBED_ENDPOINT}}` | Same as EMBED_ENDPOINT on Backend (change it there). |
| `EMBED_MODEL` | `${{Backend.EMBED_MODEL}}` | Same as EMBED_MODEL on Backend (change it there). |
| `RERANK_ENDPOINT` | `${{Backend.RERANK_ENDPOINT}}` | Same as RERANK_ENDPOINT on Backend (change it there). |
| `RERANK_MODEL` | `${{Backend.RERANK_MODEL}}` | Same as RERANK_MODEL on Backend (change it there). |
| `CONNECTION_STRINGS` | `${{Backend.CONNECTION_STRINGS}}` | Same as CONNECTION_STRINGS on Backend (change it there). |
| `LLM_MAX_INFLIGHT` | `${{Backend.LLM_MAX_INFLIGHT}}` | Same as LLM_MAX_INFLIGHT on Backend. |
| `LLM_INVOKE_TIMEOUT_S` | `${{Backend.LLM_INVOKE_TIMEOUT_S}}` | Same as LLM_INVOKE_TIMEOUT_S on Backend. |
| `SEMANTIC_LLM_MAX_INFLIGHT` | `6` | Concurrent model calls during semantic compilation (upstream default 6). Lower it on rate-limited keys. |
| `PII_LLM_MAX_WORKERS` | `6` | Concurrent model calls for PII classification, when enabled in Settings (upstream default 6). |
| `OMP_NUM_THREADS` | `4` | Caps native thread pools (numpy, onnxruntime) to the service's CPU share instead of the host's core count. |
| `TEMPLATE_SAMPLE_CONNECTION` | `true` | On the first boot of a fresh catalog, register the Chinook database on Sample Data as a normal connection (removable in Settings -> Connections). Runs once; false skips it. |
| `TEMPLATE_ENABLE_SEMANTIC_COMPILATION` | `true` | On the first boot, switch Settings -> Semantic Compilation on (only if never set), so questions work without manual steps. It re-runs every 24 h over every connected database and uses model calls; turn it off in the UI anytime. |
| `TEMPLATE_SAMPLE_DB_HOST` | `${{Sample Data.RAILWAY_PRIVATE_DOMAIN}}` | Sample Data private host. |
| `TEMPLATE_SAMPLE_DB_PORT` | `${{Sample Data.PGPORT}}` | Sample Data port. |
| `TEMPLATE_SAMPLE_DB_NAME` | `${{Sample Data.PGDATABASE}}` | Sample database name (chinook). |
| `TEMPLATE_SAMPLE_DB_USER` | `${{Sample Data.SAMPLE_DB_READER_USER}}` | Read-only login for the sample database. |
| `TEMPLATE_SAMPLE_DB_PASSWORD` | `${{Sample Data.SAMPLE_DB_READER_PASSWORD}}` | Password of that login. |
| `TEMPLATE_STARTUP_WAIT_SECONDS` | `900` | Max seconds the start wrapper waits for the Backend migration (and the first-boot steps) before giving up; keep it below the healthcheck timeout. |
| `TEMPLATE_SAMPLE_WAIT_SECONDS` | `300` | Max seconds the first boot waits for Sample Data to accept connections. |
| `RAILWAY_DEPLOYMENT_DRAINING_SECONDS` | `60` | Seconds between SIGTERM and SIGKILL on redeploy (schedulers stop cleanly). |

### Frontend

- **Source:** image `nvcr.io/nvidia/auto-ontology-frontend:1.1.0@sha256:c45cbd9a15169d159a5752ab054595773324393af9aac23acef9221fbe716b97`
- **Start command:** image default (`tini -- node app/server.js`)
- **Pre-deploy:** `/bin/sh -c 'cd /app/migrate || exit 1; i=1; until sh prisma/migrate.sh; do if [ "$i" -ge 60 ]; then echo "[railway] prisma schema sync failed 60 times, giving up" >&2; exit 1; fi; echo "[railway] prisma schema sync attempt $i failed (Postgres still starting?), retrying in 10 s" >&2; i=$((i+1)); sleep 10; done'` (timeout 900 s)
- **Healthcheck:** `/api/health` (Postgres; timeout 600 s) · **Public domain:** yes, target port `3000` · **Restart:** ALWAYS

| Variable | Value | Description |
|---|---|---|
| `PORT` | `3000` | Port the Next.js server listens on (public domain target, healthcheck). |
| `HOSTNAME` | `0.0.0.0` | Bind address of the Next.js server. |
| `APP_VERSION` | `1.1.0` | Version shown in the UI footer and logs. |
| `POSTGRES_HOST` | `${{Postgres.PGHOST}}` | Postgres private host (pgvector database for the catalog, auth tables and embeddings). |
| `POSTGRES_PORT` | `${{Postgres.PGPORT}}` | Postgres port. |
| `POSTGRES_USER` | `${{Postgres.PGUSER}}` | Postgres user. |
| `POSTGRES_PASSWORD` | `${{Postgres.PGPASSWORD}}` | Postgres password. |
| `POSTGRES_DATABASE` | `${{Postgres.PGDATABASE}}` | Database holding the public (Alembic), frontend (Prisma) and vdb (pgvector) schemas. |
| `PYTHON_API_URL` | `http://${{Backend.RAILWAY_PRIVATE_DOMAIN}}:3001` | Backend API on the private network (read at runtime by the route handlers). |
| `APP_URL` | `https://${{RAILWAY_PUBLIC_DOMAIN}}` | Public origin of the web app, required by Better Auth (sessions, CSRF, OAuth issuer, SSO callback). Change it when you add a custom domain. |
| `AUTH_SECRET` | `${{secret(48, "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789")}}` | Better Auth signing secret, generated at deploy. Changing it signs everyone out. |
| `AUTO_ONTOLOGY_ADMIN_EMAIL` | `admin@example.com` | Login email of the bootstrap admin, created (or reset) on every start. Change it to yours. |
| `AUTO_ONTOLOGY_ADMIN_PASSWORD` | `${{secret(24, "abcdefghijkmnopqrstuvwxyzABCDEFGHJKLMNPQRSTUVWXYZ23456789")}}` | Password of the bootstrap admin, generated at deploy and re-applied on every start (change it here and redeploy to rotate). |
| `AUTO_ONTOLOGY_MCP_PUBLIC_URL` | `https://${{MCP Server.RAILWAY_PUBLIC_DOMAIN}}` | Public origin of the MCP server (without /mcp); OAuth tokens for MCP clients are bound to it. The MCP Server service references this value. |
| `NEXT_TELEMETRY_DISABLED` | `1` | No Next.js telemetry. |
| `RAILWAY_DEPLOYMENT_DRAINING_SECONDS` | `15` | Seconds between SIGTERM and SIGKILL on redeploy. |

### MCP Server

- **Source:** image `nvcr.io/nvidia/auto-ontology-mcp:1.1.0@sha256:3b8f9e5703c99d6521a572f1c777c0723e0f377dfcd7d08df6ff03475cfcaa26`
- **Start command:** image default (`tini -- auto-ontology-mcp`, streamable HTTP on `/mcp`)
- **Healthcheck:** `/.well-known/oauth-protected-resource/mcp` (timeout 300 s) · **Public domain:** yes, target port `3003` · **Restart:** ALWAYS · **Replicas:** 1 (MCP sessions live in memory)
- Optional: deleting this service is safe for the web app and API; then set `AUTO_ONTOLOGY_MCP_PUBLIC_URL` on Frontend to `http://localhost:3003` (upstream default) so it no longer references a missing service.

| Variable | Value | Description |
|---|---|---|
| `PORT` | `3003` | Port Railway health-checks (MCP endpoint is /mcp). |
| `AUTO_ONTOLOGY_MCP_HOST` | `0.0.0.0` | Bind address of the MCP server. |
| `AUTO_ONTOLOGY_MCP_PORT` | `3003` | Port of the MCP server (public domain target). |
| `AUTO_ONTOLOGY_API_URL` | `${{Frontend.APP_URL}}` | Public Auto Ontology web app: the OAuth authorization server MCP clients sign in with, and the API every tool call goes through as the signed-in user. |
| `AUTO_ONTOLOGY_MCP_PUBLIC_URL` | `${{Frontend.AUTO_ONTOLOGY_MCP_PUBLIC_URL}}` | This server's public origin (set on Frontend, so both always agree). |
| `AUTO_ONTOLOGY_MCP_TIMEOUT_S` | `30` | Timeout for catalog and glossary API calls, in seconds. |
| `AUTO_ONTOLOGY_MCP_CHAT_TIMEOUT_S` | `900` | Timeout for one ask_question run (many model calls), in seconds. |

### Sample Data

- **Source:** repo `baranberkay96/auto-ontology-railway`, root `/services/sample-data` (Dockerfile `FROM ghcr.io/railwayapp-templates/postgres-ssl:18` + Chinook + `load-chinook.sh`)
- **Volume:** `/var/lib/postgresql/data` (required by the image) · **Healthcheck:** none (TCP) · **Public domain / TCP proxy:** none · **Restart:** ON_FAILURE (10)
- Optional: delete the service (and set `TEMPLATE_SAMPLE_CONNECTION=false` on Ingestion) if you do not want the demo; remove the `chinook` connection in Settings → Connections first.

| Variable | Value | Description |
|---|---|---|
| `PGDATA` | `/var/lib/postgresql/data/pgdata` | Data directory inside the volume (Railway base layout). |
| `PGHOST` | `${{RAILWAY_PRIVATE_DOMAIN}}` | Private hostname (sample-data.railway.internal). |
| `PGPORT` | `5432` | Postgres port. |
| `PGUSER` | `${{POSTGRES_USER}}` | User for the Data panel. |
| `PGPASSWORD` | `${{POSTGRES_PASSWORD}}` | Password for the Data panel. |
| `PGDATABASE` | `${{POSTGRES_DB}}` | Database the Data panel and Auto Ontology open (the Chinook sample). |
| `POSTGRES_USER` | `postgres` | Superuser created on first boot. |
| `POSTGRES_PASSWORD` | `${{ secret(32, "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ") }}` | Superuser password, generated at deploy. |
| `POSTGRES_DB` | `chinook` | Database created on first boot and filled with the Chinook sample (do not change after the first deploy). |
| `DATABASE_URL` | `postgresql://${{PGUSER}}:${{POSTGRES_PASSWORD}}@${{RAILWAY_PRIVATE_DOMAIN}}:5432/${{PGDATABASE}}` | Superuser connection string (private network). |
| `SAMPLE_DB_READER_USER` | `ao_reader` | Read-only login created on first boot for Auto Ontology (SELECT on Chinook only). |
| `SAMPLE_DB_READER_PASSWORD` | `${{secret(32, "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789")}}` | Password of that login, generated at deploy; applied on first boot only. |
| `SAMPLE_DB_READER_STATEMENT_TIMEOUT` | `120s` | statement_timeout of the read-only login (protects the demo from runaway SQL). |
| `SAMPLE_DATABASE_URL` | `postgresql://${{SAMPLE_DB_READER_USER}}:${{SAMPLE_DB_READER_PASSWORD}}@${{RAILWAY_PRIVATE_DOMAIN}}:5432/${{PGDATABASE}}` | Read-only connection string for the sample (private network). |
| `SSL_CERT_DAYS` | `820` | Validity of the self-signed TLS certificate. |
| `RAILWAY_DEPLOYMENT_DRAINING_SECONDS` | `30` | Time Postgres gets to shut down cleanly on redeploy. |

## Improvements over market templates

No market template exists. Compared with upstream's `docker-compose.yml` / Helm chart, run as-is on Railway:

- Migrations in pre-deploy commands with retries instead of one-shot containers that other services wait on (Rule 8.6); Ingestion waits for the schema instead of crash-looping.
- Admin seeded from generated variables; sign-up stays disabled; no placeholder passwords (`.env.example` ships `autoontologypassword123`, `myverylongsecret123`).
- MCP server included and wired (public URL, resource binding, authorization server), which compose does not ship.
- Works on first login: read-only Chinook sample registered as a normal, removable connection; semantic compilation switched on once.
- pgvector Postgres 18 with container-aware tuning and 1 GiB `/dev/shm` instead of a bare `pgvector/pgvector:pg17`; Railway Data panel variables kept.
- Images pinned by digest; explicit model triplets (no accidental fallback of embeddings to the chat model); concurrency and thread caps; private-only Backend/Ingestion.

## Scaling

- **Frontend:** stateless (sessions in Postgres) — replicas are fine.
- **Backend:** scale vertically. Each chat turn runs in a spawned worker process (plus one prewarmed standby), so RAM grows with concurrent conversations; connector caches are per process, so keep 1 replica unless you accept cache refresh delays after connection edits.
- **Ingestion:** 1 replica (the ingest and semantic schedulers are per process; replicas would duplicate the 24 h passes). Give it RAM for large catalogs.
- **MCP Server:** 1 replica (sessions in memory, no sticky routing).
- Concurrency knobs: `LLM_MAX_INFLIGHT`, `SEMANTIC_LLM_MAX_INFLIGHT`, `PII_LLM_MAX_WORKERS`; lower them on HTTP 429, raise them with a paid or self-hosted endpoint.

## Resource estimate

Prices: RAM $10/GB-month, vCPU $20/vCPU-month, volume $0.15/GB-month, egress $0.05/GB. **Not measured** (no container run this round); derived from the processes each image starts (Python services import LangChain, nemo-retriever, pandas, duckdb; Backend keeps one prewarmed chat worker process).

| Service | Idle RAM / vCPU | Typical RAM / vCPU | Notes |
|---|---|---|---|
| Frontend | 0.20 GB / 0.01 | 0.30 GB / 0.05 | Next.js standalone |
| Backend | 0.80 GB / 0.02 | 1.50 GB / 0.30 | API + prewarmed worker; +~0.4 GB per concurrent chat |
| Ingestion | 0.45 GB / 0.01 | 1.00 GB / 0.20 (bursts 2–3 GB during ingest/compile) | daily passes |
| MCP Server | 0.10 GB / 0.005 | 0.15 GB / 0.02 | |
| Postgres | 0.15 GB / 0.01 | 0.60 GB / 0.10 | volume 0.3 GB idle, ~3 GB typical |
| Sample Data | 0.05 GB / 0.005 | 0.06 GB / 0.01 | volume ~0.1 GB |

- **Idle ≈ $19/month** (1.75 GB × $10 + 0.06 vCPU × $20 + 0.4 GB × $0.15).
- **Typical ≈ $50/month** (3.6 GB × $10 + 0.68 vCPU × $20 + 3.1 GB × $0.15 + ~1 GB egress).
- Model calls are not billed by Railway: NVIDIA's trial endpoints are free within their credits/rate limits; other providers bill separately.
- **Minimum plan:** Hobby. Trial's 1 GB per service is below Backend under load and Ingestion during an ingest.

## Verification checklist

1. **Builds and pulls:** Backend, Frontend, MCP Server pull from nvcr.io. Ingestion build logs `self-test ok (alembic head b3aed65e49b7)`; Sample Data build passes `sha256sum -c`.
2. **Pre-deploy:** Backend log shows Alembic `Running upgrade … -> b3aed65e49b7`; Frontend shows `migrate: running prisma db push...` and Prisma's "in sync" message.
3. **Health:** Backend `/api/health` and Ingestion `/health` 200 with `postgres: ok, migrations: ok`; `https://{frontend-domain}/api/health` 200; `https://{mcp-domain}/.well-known/oauth-protected-resource/mcp` 200 with `resource: https://{mcp-domain}/mcp` and `authorization_servers: [https://{frontend-domain}/]`.
4. **Sample Data** log: `load-chinook: done: 3503 tracks, 412 invoices`.
5. **Ingestion** log: `schema: at revision b3aed65e49b7`, `sample_connection: added connection 'chinook'`, `semantic_compilation: switched on`, `semantic: compilation enabled; scheduler started`, `ingest: starting (1 connection(s))`, later a successful semantic pass.
6. **Login:** `https://{frontend-domain}` → login page; `AUTO_ONTOLOGY_ADMIN_EMAIL` / `AUTO_ONTOLOGY_ADMIN_PASSWORD` work. Sign-up is refused: `curl -s -X POST https://{frontend-domain}/api/auth/sign-up/email -H 'content-type: application/json' -d '{"email":"x@example.com","password":"Passw0rd!x","name":"x"}'` → error, no user created.
7. **UI:** Settings → Connections lists `chinook` (editable, deletable); Settings → Semantic Compilation is on with a successful run.
8. **Chat:** "Which three countries had the highest invoice totals in 2024?" → USA 127.98, Brazil 53.46, Canada 42.57 (checked against the data locally), with the SQL shown.
9. **API:** user menu → API Tokens → new token; `curl -N -H "x-api-key: {token}" -H 'content-type: application/json' -d '{"question":"How many tracks are there per genre?"}' https://{frontend-domain}/api/chat/completions` streams `step`/`result` events and `[DONE]`.
10. **MCP:** `curl -i https://{mcp-domain}/mcp` → 401 with `WWW-Authenticate` pointing at the resource metadata; add `https://{mcp-domain}/mcp` to Cursor or Claude, sign in through Auto Ontology's login, `check_readiness` → ready, `ask_question` answers.
11. **Private services:** Backend and Ingestion have no domain; from a Railway shell in Frontend, `node -e "fetch('http://backend.railway.internal:3001/api/health/live').then(r=>console.log(r.status))"` prints 200 (the image has no curl).
12. **Redeploy everything:** login, connection, compiled layer persist; Ingestion logs `already handled on an earlier boot`; changing `AUTO_ONTOLOGY_ADMIN_PASSWORD` + redeploying Frontend changes the login.

## Open questions

- **Not deployed yet; no Docker build or container run** this round (instruction: no Docker). Verified statically: registry manifests/configs/layers, upstream sources at the release commit, `sh -n`/`bash -n`, JSON, script tests with fakes, SQL against local PostgreSQL 15.
- **nvcr.io from Railway:** anonymous pulls work from here; Railway pulling `nvcr.io/...:tag@sha256` (image services) and `FROM nvcr.io/...` (Ingestion build) is unverified. Fallback: build the images from `release/v1.1.0` (`d14214e9`) in repo services.
- **Default chat model (tested on Railway 2026-11-03 with a real free key):** upstream 1.1.0's `nvidia/nemotron-3-nano-30b-a3b` answers `410 Gone` (end of life 2026-09-01). Of the live chat models, that account could call only `nemotron-3-ultra-550b-a55b`, `nemotron-3.5-lightning-30b-a3b` and `openai/gpt-oss-20b` (the rest: `404 Function ... Not found for account`, incl. `nemotron-nano-3-30b-a3b` and `nemotron-3-super-120b-a12b`). Lightning rejects the `guided_json` field langchain-nvidia sends for structured output; gpt-oss-20b timed out at 120 s. `nemotron-3-ultra-550b-a55b` (structured output listed in langchain-nvidia 1.4.3) compiled Chinook and answered two questions correctly (first answer ~3 min). Embedding and rerank ids work.
- **Trial rate limits:** ingest + compile of Chinook on a free key may hit 429s (the clients retry); the time to the first answer is unmeasured (estimate 5–20 min).
- **IPv6-only (legacy) Railway environments:** Backend and Ingestion bind `0.0.0.0` (hardcoded upstream); private calls to them need the IPv4 records that new environments provide.
- **Pre-deploy semantics:** Railway runs pre-deploy in a separate container from the service image; `prisma db push` there is unverified (upstream runs it as a Kubernetes Job the same way).
- **User management in 1.1.0:** adding email/password users needs SSO or Better Auth's `POST /api/auth/admin/create-user`; the latter is inferred from the Better Auth admin plugin and the admin role's statements, not exercised.
- **Memory:** chat worker processes and ingest bursts are estimates; watch Backend/Ingestion RAM on the first deploy.
- **Dynamic client registration** for MCP is open (`allowUnauthenticatedClientRegistration: true` upstream); anyone can register an OAuth client row, but nobody gets a token without signing in.
- **Upstream pace:** `main` is 114 commits past 1.1.0 (invitations, new model defaults). Re-check when NVIDIA publishes the next images.
