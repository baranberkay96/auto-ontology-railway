# Deploy and Host Auto Ontology with Railway

[![Deploy on Railway](https://railway.com/button.svg)](https://railway.com/deploy/auto-ontology-v1-semantic-layer?referralCode=20H68q)

Auto Ontology is NVIDIA's open-source (Apache-2.0) semantic layer for AI agents: it builds an ontology over your relational databases and answers natural-language questions as SQL. This community template runs release 1.1.0 from NVIDIA's published images with the web UI, the authenticated API, the MCP server and a sample database, so the first question works after deploy.

## About Hosting Auto Ontology

Upstream ships a Docker Compose file and a Helm chart; running it yourself means a pgvector Postgres, a FastAPI backend that must never be public, an ingestion worker, two migration jobs, a Next.js front end with Better Auth, and an MCP server whose OAuth settings must match the web app's public URL. This template wires all of that on Railway's private network. Migrations run before each deploy, the admin account is created from generated variables, sign-up stays closed, and only the web app and the MCP server get public domains. You provide one value: an NVIDIA API key. A read-only Chinook database is registered as a sample connection, ingested and compiled on first boot.

## Common Use Cases

- Give Cursor, Claude or your own agents governed access to company data through MCP, with every call running as the signed-in user
- Natural-language analytics over Postgres, Snowflake, Databricks, MySQL, ClickHouse or Trino, with the generated SQL shown
- A shared business glossary that maps terms such as "active customer" onto real columns and reviewed SQL
- Scripts and scheduled jobs that ask questions over the `/api/chat/completions` endpoint with API tokens
- Evaluating NVIDIA Nemotron models for text-to-SQL on your own schema

## Dependencies for Auto Ontology Hosting

- Auto Ontology 1.1.0: backend + ingestion (`nvcr.io/nvidia/auto-ontology`), web app (`nvcr.io/nvidia/auto-ontology-frontend`), MCP server (`nvcr.io/nvidia/auto-ontology-mcp`)
- PostgreSQL 18 with pgvector (catalog, users, embeddings)
- PostgreSQL 18 with the Chinook sample database (optional demo source)
- An NVIDIA API key from build.nvidia.com, or your own OpenAI-compatible / NIM endpoints

### Deployment Dependencies

- Source and docs: https://github.com/NVIDIA/auto-ontology
- MCP server guide: https://github.com/NVIDIA/auto-ontology/blob/main/docs/mcp.md
- NVIDIA API keys and models: https://build.nvidia.com
- NVIDIA API Trial Terms of Service: https://assets.ngc.nvidia.com/products/api-catalog/legal/NVIDIA%20API%20Trial%20Terms%20of%20Service.pdf
- Chinook sample database (MIT): https://github.com/lerocha/chinook-database

### Implementation Details

| Service | Role | Public |
|---|---|---|
| Frontend | Web UI, Better Auth login, API tokens, the authenticated `/api` gateway; runs the Prisma migration before each deploy | **yes** |
| MCP Server | MCP endpoint `/mcp` for agent clients; sign-in through Auto Ontology's OAuth | **yes** |
| Backend | FastAPI: chat / NL-to-SQL, catalog, connections; runs the Alembic migration before each deploy | no |
| Ingestion | Ingests connected databases, writes embeddings, compiles the semantic layer (every 24 h and on demand) | no |
| Postgres | pgvector database, tuned to the container's limits | no |
| Sample Data | Chinook sample (11 tables, music store sales 2021–2025) with a read-only login | no |

Backend and Ingestion must stay private: the Backend trusts a user-id header set by the Frontend, and the Ingestion API has no authentication. Never add a domain or TCP proxy to them.

**First login**

1. Paste your NVIDIA API key (`nvapi-...`) into `DEFAULT_MODELS_API_KEY` when deploying. Create one for free at build.nvidia.com.
2. Wait until all services are healthy (first deploy: a few minutes for image pulls and builds).
3. Open the Frontend URL. The login is `AUTO_ONTOLOGY_ADMIN_EMAIL` (default `admin@example.com`) and `AUTO_ONTOLOGY_ADMIN_PASSWORD` (generated), both on Frontend → Variables. To use your own email, change it there and redeploy Frontend.
4. On first boot, Ingestion registers the `chinook` connection, ingests it and compiles the semantic layer (about 15 minutes in our test). Check Settings → Semantic Compilation for the first successful run. If the key was wrong or a model unavailable during that run, fix it, then use **Reset Semantic Layer** there: a failed run still counts as compiled.
5. Ask in Chat: "Which artists have the most tracks?" A first answer took about 3 minutes in our test.

Self-service sign-up is disabled, as it is upstream. Add people through Settings → SSO (redirect URI `https://{your-domain}/api/auth/sso/callback`), or as an admin through Better Auth's admin API. The admin password is re-applied on every start: rotate it by changing the variable and redeploying Frontend.

**Connect your own database**

As an admin, open Settings → Connections → Add (Postgres, Snowflake, Databricks, MySQL, ClickHouse, Trino and others). Use a read-only database user. Adding a connection starts an ingest; its semantic layer is compiled on the next daily pass. To compile sooner, switch Semantic Compilation off and on again (enabling starts a run) or restart Ingestion. You can delete the `chinook` sample there, or remove the Sample Data service once the connection is gone. Without Vault, which this template does not include, connection credentials are stored in plaintext JSON in the Postgres catalog: keep that database private and treat its backups as secrets. You can also list connections in `CONNECTION_STRINGS` on Backend (comma-separated URLs); while it is set, the Connections page is hidden.

**Semantic compilation cost**

The template switches semantic compilation on at first boot so the sample works out of the box. It runs every 24 h over every connected database, and new tables cost model calls. Large warehouses can mean many calls. Turn it off in Settings, or set `TEMPLATE_ENABLE_SEMANTIC_COMPILATION=false` on Ingestion before the first deploy to keep upstream's opt-in default.

**API and MCP**

- API: user menu → API Tokens → New token. Then call `POST https://{your-domain}/api/chat/completions` with header `x-api-key: {token}` and body `{"question": "..."}`. The response is a stream of `step` / `result` events ending in `[DONE]`. A token acts with its owner's role.
- MCP: add `https://{mcp-domain}/mcp` to Cursor, Claude or any MCP client. The client registers itself and opens Auto Ontology's login page; no secrets go into the client config. Tools: `ask_question`, `check_readiness`, `search_terms`, `describe_table` and more, all read-only. The MCP URL is configured once, in `AUTO_ONTOLOGY_MCP_PUBLIC_URL` on Frontend.

**Models**

All model settings live on Backend (Ingestion references them). Defaults: `nvidia/nemotron-3-ultra-550b-a55b` for chat (upstream 1.1.0's `nvidia/nemotron-3-nano-30b-a3b` was retired on 2026-09-01; the chat model must support structured output), `nvidia/nemotron-3-embed-1b` for embeddings and `nvidia/llama-nemotron-rerank-vl-1b-v2` for reranking, all on NVIDIA's API catalog. `REASONING_*` and `NON_REASONING_*` accept any OpenAI-compatible endpoint (set `*_ENDPOINT`, `*_MODEL` and `*_API_KEY`). Embeddings and reranking expect NVIDIA NIM-compatible APIs, either hosted or self-hosted NIM. Keep the embedding model fixed after the first ingest; changing it needs a re-ingest. NVIDIA enables models per account: `404 Function ... Not found for account` in the logs means pick another model from build.nvidia.com. On HTTP 429/503, lower `LLM_MAX_INFLIGHT` (Backend) and `SEMANTIC_LLM_MAX_INFLIGHT` (Ingestion).

**Scaling**

Frontend can run replicas. Scale Backend vertically: each concurrent chat turn runs in its own worker process. Keep Ingestion and MCP Server at one replica, because their schedulers and sessions live in the process. Give Ingestion more RAM for large catalogs.

**Upgrades**

All Auto Ontology images are pinned to 1.1.0 by digest. To upgrade, set the same new tag and digest on Backend, Frontend and MCP Server, and in `AUTO_ONTOLOGY_IMAGE` on Ingestion. Read the upstream changes, then deploy them together. Backend migrates the schema before it starts, and Ingestion waits for it. Never run mixed versions.

**Costs**

Estimated at Railway usage prices: about $19/month idle and $50/month with a few active users and daily ingests. Hobby plan recommended. Model calls are billed by your model provider, not Railway.

**NVIDIA API terms**

Hosted endpoints on build.nvidia.com are governed by NVIDIA's API Trial Terms of Service and each model's licence. The free access is meant for prototyping and evaluation. The trial terms limit use without a paid subscription to internal testing and evaluation, not production. For production, check NVIDIA's terms (for example a subscription or self-hosted NIM), or point the model settings at another provider. This summary is not legal advice.

### Why Deploy Auto Ontology on Railway?

Railway runs the web app, MCP server, API, ingestion worker and both databases in one project on a private network, with HTTPS, volumes, pre-deploy migrations and logs handled for you. One API key gets you from deploy to a working NL-to-SQL demo; then you connect your own databases and agents. This is a community template. It is not affiliated with or endorsed by NVIDIA. Auto Ontology is NVIDIA's open-source project under the Apache-2.0 licence.
