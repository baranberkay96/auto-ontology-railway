# Notice

## Upstream software

This repository contains Railway configuration and small wrapper scripts only. Auto Ontology is **NVIDIA's open-source project**; its software is pulled from NVIDIA's published container images and is not stored or modified here. This is a community template, not affiliated with or endorsed by NVIDIA.

| Software | License | Used as |
|---|---|---|
| Auto Ontology 1.1.0 (backend, ingestion service, Next.js web app, MCP server) | Apache License 2.0 — Copyright (c) 2024-2026, NVIDIA CORPORATION & AFFILIATES. All rights reserved. | Images `nvcr.io/nvidia/auto-ontology:1.1.0`, `nvcr.io/nvidia/auto-ontology-frontend:1.1.0`, `nvcr.io/nvidia/auto-ontology-mcp:1.1.0` (published by NVIDIA on NGC), pinned by digest. The Ingestion service adds one script on top of the backend image; no upstream file is changed. |
| Third-party components inside those images (Python and npm dependencies, Ubuntu 22.04 base, Node.js, Prisma, Better Auth, FastMCP, ...) | Their own licenses | Listed by NVIDIA in `/licenses/THIRD_PARTY_NOTICES.md` and `/licenses/CONTAINER_THIRD_PARTY_NOTICES.md` inside each image; NVIDIA's `OPEN_SOURCE_NOTICE` points to https://opensource.nvidia.com/oss/teams/nvidia for the archived sources. |
| PostgreSQL 18, pgvector 0.8 | PostgreSQL License | `ghcr.io/railwayapp-templates/postgres-ssl:18` (Railway; MIT-licensed image repo) for Postgres and Sample Data |
| Chinook Database 1.4.5 (sample data) | MIT — Copyright (c) 2008-2024 Luis Rocha | `Chinook_PostgreSql.sql` downloaded at build time from https://github.com/lerocha/chinook-database at commit `7f67772503d71ba90f19283c38e93923addb43fa`, verified by SHA-256 `e3fde5c1a5b51a2a91429a702c9ca6e69ba56e6c7f5e112724d70c3d03db695e`, loaded unmodified except for its three `DROP/CREATE DATABASE` / `\c` header lines. Not stored in this repository. |
| Lucide icons (`network`, `server`, `database-zap`, `plug`, `database`) | ISC | Referenced by URL from `cdn.jsdelivr.net/npm/lucide-static@1.59.0`; not copied |

The MIT licence text of Chinook (it travels with the downloaded file's header link): Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated documentation files (the "Software"), to deal in the Software without restriction, including without limitation the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software, and to permit persons to whom the Software is furnished to do so, subject to the following conditions: The above copyright notice and this permission notice shall be included in all copies or substantial portions of the Software. THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

## External services and terms (not legal advice)

- **NVIDIA API catalog** (`integrate.api.nvidia.com`, `ai.api.nvidia.com`, keys from build.nvidia.com) is the default model provider. It is governed by the NVIDIA API Trial Terms of Service (https://assets.ngc.nvidia.com/products/api-catalog/legal/NVIDIA%20API%20Trial%20Terms%20of%20Service.pdf). Those terms state that, unless you purchase a subscription from NVIDIA or a service provider, the API service may only be used for internal testing and evaluation, not in production. Free access is therefore meant for prototyping and evaluation; for production, check NVIDIA's current terms (subscription, self-hosted NIM) or configure another provider in the model settings.
- **Models** (default: Nemotron 3 Nano 30B A3B, Nemotron 3 Embed 1B, Llama Nemotron Rerank VL 1B v2) carry their own licences, shown on each model's build.nvidia.com page (for example the NVIDIA Open Model License).
- Upstream's own notice applies: Auto Ontology retrieves and interacts with external materials (model APIs, your databases, optional KumoRFM) that are governed by their own terms; you are responsible for complying with them.
- This summary is practical guidance, not legal advice. Ask NVIDIA or a lawyer before relying on the hosted endpoints for a commercial or customer-facing workload.

## Verified against

| What | Upstream file | Ref | Checked |
|---|---|---|---|
| Release version, image tags, release process | `pyproject.toml`, `mcp/pyproject.toml`, `frontend/package.json`, `helm/auto-ontology/Chart.yaml` + `values.yaml`, `.github/workflows/release-docker.yml`, `.github/actions/determine-release-version/action.yml`, `DEPLOYMENT.md` | `release/v1.1.0` = `d14214e930fcb5988178ad51bde7672e600827a7`; `main` = `6c4fb71e20c1f9fc4b6059aa1c99f55b697d60b0` | 2026-11-03 |
| Services, ports, migrations, start modes | `docker-compose.yml`, `Dockerfile` (entrypoint `server` / `ingestion_service` / `migrate`), `frontend/Dockerfile`, `frontend/prisma/migrate.sh`, `frontend/prisma.config.ts`, `helm/auto-ontology/templates/*.yaml` | `d14214e9` | 2026-11-03 |
| Runtime (not build-time) configuration of the web app | `frontend/next.config.ts` (no rewrites), `frontend/auth/proxy-backend.ts`, `frontend/app/api/chat/*/route.ts`, compiled bundle in image layer `sha256:0c8264cc…` | `d14214e9` / image 1.1.0 | 2026-11-03 |
| Sign-up disabled, admin seeding, MCP resource, API keys | `frontend/auth/auth.ts`, `frontend/auth/seed-admin.ts`, `frontend/instrumentation.ts`, `frontend/auth/auth-access.ts`, `frontend/app/api/auth/[...all]/route.ts` | `d14214e9` | 2026-11-03 |
| Schema gate, health endpoints, bind addresses | `auto_ontology/dal/schema_version.py`, `auto_ontology/server/__main__.py`, `auto_ontology/server/health/router.py`, `auto_ontology/ingestion_service/__main__.py`, `auto_ontology/ingestion_service/router.py`, `alembic/env.py` | `d14214e9` | 2026-11-03 |
| Connections, `CONNECTION_STRINGS`, Vault, plaintext storage | `README.md` (Connections Management), `auto_ontology/dal/connections.py`, `auto_ontology/server/connections/service.py` + `router.py`, `auto_ontology/connectors/registry.py`, `auto_ontology/ingestion_service/connections.py`, `frontend/app/settings/connections/page.tsx` | `d14214e9` | 2026-11-03 |
| Semantic compilation opt-in and chat gate | `auto_ontology/ingestion_service/config.py`, `semantic_scheduler.py`, `data_scheduler.py`, `auto_ontology/infra/feature_flags.py`, `auto_ontology/server/chat/router.py`, `frontend/app/api/configurations/semantic-compilation/route.ts`, `frontend/prisma/schema.prisma` | `d14214e9` | 2026-11-03 |
| Model triplets and defaults | `.env.example`, `auto_ontology/utils/model_config.py`, `llm_invoke.py`, `embedding.py`, `auto_ontology/vdb/postgres.py` | `d14214e9` | 2026-11-03 |
| MCP server auth, routes, configuration | `mcp/auto_ontology_mcp/config.py`, `server.py`, `auto_ontology_auth.py`, `readiness.py`, `docs/mcp.md`, `mcp/Dockerfile`; FastMCP 3.4.7 `fastmcp/server/auth/auth.py`, `server/http.py`; MCP SDK 1.29.0 `mcp/server/auth/routes.py` | `d14214e9`; PrefectHQ/fastmcp `v3.4.7`; modelcontextprotocol/python-sdk `v1.29.0` | 2026-11-03 |
| Image digests, configs, layers (code identical to the branch) | NGC registry API (`nvcr.io/v2/nvidia/<repo>/manifests/1.1.0`, configs, code layers) | 1.1.0 | 2026-11-03 |
| Postgres base and init hooks | railwayapp-templates/postgres-ssl `Dockerfile.18`, `wrapper.sh`; docker-library/postgres `18/trixie/docker-entrypoint.sh` | default branches | 2026-11-03 |
| Chinook script | lerocha/chinook-database `ChinookDatabase/DataSources/Chinook_PostgreSql.sql`, `LICENSE.md`, `docker-compose.yml` | `7f677725` (release 1.4.5) | 2026-11-03 |
| NVIDIA API trial terms | NVIDIA API Trial Terms of Service (PDF, link above); model page build.nvidia.com/nvidia/nemotron-3-nano-30b-a3b | — | 2026-11-03 |
| Railway behaviour | docs.railway.com: start command (overrides the image ENTRYPOINT, exec form), pre-deploy command (separate container, env vars, private network) | — | 2026-11-03 |

## Our files

| File | Origin |
|---|---|
| `services/postgres/pgvector-tune.sh`, `services/postgres/to-start-command.py` | Our own `56-pgvector` template (baranberkay96/pgvector-railway), unchanged apart from a header comment |
| `services/ingestion/*`, `services/sample-data/*`, `template.json`, `TEMPLATE.md`, `README.md` | Written for this template. The ingestion wrapper calls Auto Ontology's internal Python API inside NVIDIA's image (Apache-2.0); it contains no copied upstream code. |

## Reference only (not copied)

- No Railway marketplace template exists for Auto Ontology; "Ontology Browser", WrenAI and Vanna were only noted as neighbours.
- Upstream README, DEPLOYMENT.md and docs were read for behaviour; no prose was copied.

## Trademarks

NVIDIA, NIM, Nemotron and NGC are trademarks of NVIDIA Corporation. "Railway", "PostgreSQL", "Cursor" and "Claude" belong to their respective owners. The template uses a neutral icon and does not use NVIDIA's logo. This is a community template and is not affiliated with or endorsed by NVIDIA or Railway.
