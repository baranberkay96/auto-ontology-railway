#!/usr/bin/env python
"""Railway start wrapper for the Auto Ontology ingestion service.

Runs inside NVIDIA's published image (nvcr.io/nvidia/auto-ontology), as the
image's own user, before handing the process to the unmodified service
(``python -m auto_ontology.ingestion_service``). It does three things:

1. **Waits for the database schema.** Alembic migrations run once, in the
   Backend service's pre-deploy command. The ingestion service refuses to start
   against a schema it does not expect, so instead of crash-looping until the
   Backend has migrated, this waits for ``public.alembic_version`` to reach the
   revision this image ships. Required: on timeout it exits 1 and Railway
   restarts it.
2. **Registers the sample connection once (optional).** With
   ``TEMPLATE_SAMPLE_CONNECTION=true`` and a fresh catalog, it adds the Chinook
   database on the Sample Data service as an ordinary UI-managed connection, the
   same record Settings -> Connections writes. The startup ingest pass then picks
   it up, and admins can edit or delete it in the UI like any other connection.
3. **Switches semantic compilation on once (optional).** With
   ``TEMPLATE_ENABLE_SEMANTIC_COMPILATION=true`` it inserts the
   ``semantic_compilation_enabled`` setting the Settings page writes, only if the
   row is absent, so the first ingest is followed by a compilation and the chat
   can answer without manual steps. A later choice in the UI is never overridden.

Steps 2 and 3 are recorded in ``railway_template.first_boot`` and never repeat,
and they are best-effort: any failure is logged and the service starts anyway.

Self-test (run at image build): ``railway-ingestion --self-test``.
"""

from __future__ import annotations

import contextlib
import json
import logging
import os
import sys
import time
from typing import Any, Callable, Iterator

APP_DIR = "/app"
MARKER_SCHEMA = "railway_template"
MARKER_TABLE = f"{MARKER_SCHEMA}.first_boot"
# Arbitrary constant: serialises the first-boot steps across replicas.
ADVISORY_LOCK_KEY = 7_281_904_113
SEMANTIC_FLAG_KEY = "semantic_compilation_enabled"
POLL_SECONDS = 5

LOG = logging.getLogger("railway-ingestion")


# ---------------------------------------------------------------------------
# Environment
# ---------------------------------------------------------------------------


def env_flag(name: str, default: bool) -> bool:
    """A true/false variable. A typo falls back to the default with a warning:
    these switch optional first-boot steps, which must never stop the service."""
    raw = (os.environ.get(name) or "").strip().lower()
    if not raw:
        return default
    if raw in {"1", "true", "yes", "on"}:
        return True
    if raw in {"0", "false", "no", "off"}:
        return False
    LOG.warning("%s must be true or false, got %r; using %s", name, raw, default)
    return default


def env_int(name: str, default: int, *, minimum: int = 1) -> int:
    """A whole-number variable; an invalid value falls back to the default."""
    raw = (os.environ.get(name) or "").strip()
    if not raw:
        return default
    if raw.isdigit() and int(raw) >= minimum:
        return int(raw)
    LOG.warning("%s must be a whole number >= %d, got %r; using %d", name, minimum, raw, default)
    return default


def pause(deadline: "Deadline") -> None:
    """Sleep one poll interval, but never past the deadline."""
    time.sleep(max(0.5, min(POLL_SECONDS, deadline.remaining())))


class Deadline:
    """One time budget shared by every wait, so the healthcheck window holds."""

    def __init__(self, seconds: int) -> None:
        self._end = time.monotonic() + seconds

    def remaining(self) -> float:
        return max(0.0, self._end - time.monotonic())

    def expired(self) -> bool:
        return self.remaining() <= 0


def sample_connection_from_env() -> dict[str, Any] | None:
    """The sample connection in the shape the Settings form stores, or None."""
    env_names = {
        "host": "TEMPLATE_SAMPLE_DB_HOST",
        "port": "TEMPLATE_SAMPLE_DB_PORT",
        "user": "TEMPLATE_SAMPLE_DB_USER",
        "password": "TEMPLATE_SAMPLE_DB_PASSWORD",
        "database": "TEMPLATE_SAMPLE_DB_NAME",
    }
    fields = {key: (os.environ.get(name) or "").strip() for key, name in env_names.items()}
    fields["password"] = os.environ.get("TEMPLATE_SAMPLE_DB_PASSWORD") or ""
    missing = [env_names[key] for key, value in fields.items() if not value]
    if missing:
        LOG.warning(
            "sample connection: %s not set (is the Sample Data service deployed?); "
            "not adding it",
            ", ".join(missing),
        )
        return None
    if not fields["port"].isdigit():
        LOG.warning("sample connection: TEMPLATE_SAMPLE_DB_PORT is not a number; not adding it")
        return None
    return {"type": "postgresql", **fields}


# ---------------------------------------------------------------------------
# Database helpers (the app database, via the image's own POSTGRES_* settings)
# ---------------------------------------------------------------------------


def app_connect() -> Any:
    import psycopg

    from auto_ontology.infra.postgres import get_postgres_connection_string

    return psycopg.connect(
        get_postgres_connection_string(), connect_timeout=5, autocommit=True
    )


@contextlib.contextmanager
def first_boot_lock() -> Iterator[Any]:
    """Session advisory lock + the marker table, for one first-boot step."""
    with app_connect() as conn:
        conn.execute("SELECT pg_advisory_lock(%s)", (ADVISORY_LOCK_KEY,))
        try:
            conn.execute(f"CREATE SCHEMA IF NOT EXISTS {MARKER_SCHEMA}")
            conn.execute(
                f"CREATE TABLE IF NOT EXISTS {MARKER_TABLE} ("
                " step text PRIMARY KEY,"
                " detail text NOT NULL DEFAULT '',"
                " done_at timestamptz NOT NULL DEFAULT now())"
            )
            yield conn
        finally:
            conn.execute("SELECT pg_advisory_unlock(%s)", (ADVISORY_LOCK_KEY,))


def step_done(conn: Any, step: str) -> bool:
    row = conn.execute(
        f"SELECT detail FROM {MARKER_TABLE} WHERE step = %s", (step,)
    ).fetchone()
    if row:
        LOG.info("%s: already handled on an earlier boot (%s)", step, row[0])
    return row is not None


def mark_done(conn: Any, step: str, detail: str) -> None:
    conn.execute(
        f"INSERT INTO {MARKER_TABLE} (step, detail) VALUES (%s, %s) "
        "ON CONFLICT (step) DO NOTHING",
        (step, detail),
    )
    LOG.info("%s: %s", step, detail)


# ---------------------------------------------------------------------------
# 1. Schema
# ---------------------------------------------------------------------------


def wait_for_schema(deadline: Deadline) -> None:
    from auto_ontology.dal.schema_version import schema_state

    last_log = 0.0
    while True:
        state = schema_state()
        if state.current:
            LOG.info("schema: at revision %s", state.applied)
            return
        if deadline.expired():
            LOG.error(
                "schema: not ready in time: %s. The Backend service runs the "
                "migrations in its pre-deploy command; Backend and Ingestion must "
                "run the same Auto Ontology image. Exiting so Railway restarts this "
                "service.",
                state.detail,
            )
            raise SystemExit(1)
        now = time.monotonic()
        if now - last_log >= 60:
            LOG.info("schema: waiting for the Backend migration (%s)", state.detail)
            last_log = now
        pause(deadline)


# ---------------------------------------------------------------------------
# 2. Sample connection
# ---------------------------------------------------------------------------


def wait_for_sample_db(connection: dict[str, Any], deadline: Deadline) -> bool:
    import psycopg

    from auto_ontology.connectors.connection_string_factory import (
        build_connection_string,
    )

    url = build_connection_string(connection)
    last_error = ""
    while True:
        try:
            with psycopg.connect(url, connect_timeout=5) as conn:
                conn.execute("SELECT count(*) FROM information_schema.tables")
            return True
        except Exception as exc:  # unreachable, still initialising, bad login
            text = str(exc).strip()
            last_error = text.splitlines()[0] if text else type(exc).__name__
        if deadline.expired():
            break
        pause(deadline)
    LOG.warning(
        "sample connection: %s:%s/%s not reachable in time (%s); not added on this "
        "boot, the next restart of Ingestion tries again",
        connection["host"],
        connection["port"],
        connection["database"],
        last_error or "timeout",
    )
    return False


def validate_with_connector(connection: dict[str, Any]) -> None:
    """The same check Settings -> Connections -> Test runs before saving."""
    from auto_ontology.catalog.table_filter import from_connection
    from auto_ontology.connectors.connection_string_factory import (
        build_connection_string,
    )
    from auto_ontology.connectors.registry import create_connector

    from_connection(connection)
    connector = create_connector(build_connection_string(connection))
    try:
        connector.ping()
    finally:
        connector.close()


def seed_sample_connection(deadline: Deadline) -> None:
    step = "sample_connection"
    if not env_flag("TEMPLATE_SAMPLE_CONNECTION", False):
        LOG.info("%s: TEMPLATE_SAMPLE_CONNECTION is off; skipped", step)
        return

    from auto_ontology.connectors.registry import parse_connection_strings
    from auto_ontology.dal.connections import insert_connection, list_connections

    if parse_connection_strings(os.environ.get("CONNECTION_STRINGS", "")):
        LOG.info("%s: CONNECTION_STRINGS is set, connections come from it; skipped", step)
        return
    connection = sample_connection_from_env()
    if connection is None:
        return
    name = connection["database"]

    with first_boot_lock() as conn:
        if step_done(conn, step):
            return
        if list_connections():
            mark_done(conn, step, "connections already configured; sample not added")
            return

    sample_budget = Deadline(
        min(int(deadline.remaining()), env_int("TEMPLATE_SAMPLE_WAIT_SECONDS", 300))
    )
    if not wait_for_sample_db(connection, sample_budget):
        return
    validate_with_connector(connection)

    from auto_ontology.connectors.vault import is_vault_configured, write_secret

    with first_boot_lock() as conn:
        if step_done(conn, step):
            return
        if any(str(c.get("database") or "") == name for c in list_connections()):
            mark_done(conn, step, f"connection {name!r} already exists")
            return
        # Mirrors auto_ontology.server.connections.service.create_connection:
        # credentials go to Vault when it is configured, else onto the row.
        if is_vault_configured():
            write_secret(name, connection)
            payload = ""
        else:
            payload = json.dumps(connection)
        insert_connection(connection=payload, database_name=name)
        mark_done(
            conn,
            step,
            f"added connection {name!r} ({connection['user']}@{connection['host']}:{connection['port']})",
        )


# ---------------------------------------------------------------------------
# 3. Semantic compilation flag
# ---------------------------------------------------------------------------


def wait_for_frontend_settings(deadline: Deadline) -> bool:
    while True:
        try:
            with app_connect() as conn:
                row = conn.execute(
                    "SELECT to_regclass('frontend.configurations') IS NOT NULL"
                ).fetchone()
            if row and row[0]:
                return True
        except Exception as exc:
            LOG.debug("settings table check failed: %s", exc)
        if deadline.expired():
            break
        pause(deadline)
    LOG.warning(
        "semantic_compilation: frontend.configurations does not exist yet (the "
        "Frontend pre-deploy command creates it); not switched on during this boot"
    )
    return False


def seed_semantic_compilation(deadline: Deadline) -> None:
    step = "semantic_compilation"
    if not env_flag("TEMPLATE_ENABLE_SEMANTIC_COMPILATION", False):
        LOG.info("%s: TEMPLATE_ENABLE_SEMANTIC_COMPILATION is off; skipped", step)
        return
    if not wait_for_frontend_settings(deadline):
        return
    with first_boot_lock() as conn:
        if step_done(conn, step):
            return
        result = conn.execute(
            "INSERT INTO frontend.configurations (key, value, updated_at) "
            "VALUES (%s, 'true', now()) ON CONFLICT (key) DO NOTHING",
            (SEMANTIC_FLAG_KEY,),
        )
        if result.rowcount:
            mark_done(conn, step, "switched on (Settings -> Semantic Compilation)")
        else:
            mark_done(conn, step, "already set in Settings; left unchanged")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def best_effort(name: str, func: Callable[[Deadline], None], deadline: Deadline) -> None:
    try:
        func(deadline)
    except SystemExit:
        raise
    except Exception:
        LOG.exception("%s: failed; skipped, the ingestion service starts anyway", name)


def exec_ingestion_service() -> None:
    from auto_ontology.dal.session import dispose_engine

    dispose_engine()
    os.chdir(APP_DIR)
    argv = [sys.executable, "-m", "auto_ontology.ingestion_service"]
    LOG.info("starting %s", " ".join(argv[1:]))
    sys.stdout.flush()
    sys.stderr.flush()
    os.execv(sys.executable, argv)


def self_test() -> int:
    """Build-time check that the image still has everything this script uses."""
    from auto_ontology.catalog.table_filter import from_connection
    from auto_ontology.connectors.connection_string_factory import (
        build_connection_string,
    )
    from auto_ontology.connectors.registry import create_connector, parse_connection_strings
    from auto_ontology.connectors.vault import is_vault_configured, write_secret
    from auto_ontology.dal.connections import insert_connection, list_connections
    from auto_ontology.dal.schema_version import head_revision, schema_state
    from auto_ontology.dal.session import dispose_engine
    from auto_ontology.infra.postgres import get_postgres_connection_string

    for func in (
        from_connection,
        create_connector,
        write_secret,
        insert_connection,
        list_connections,
        schema_state,
        dispose_engine,
        get_postgres_connection_string,
    ):
        assert callable(func), func
    sample = {
        "type": "postgresql",
        "host": "sample-data.railway.internal",
        "port": "5432",
        "user": "ao_reader",
        "password": "p@ss/word",
        "database": "chinook",
    }
    url = build_connection_string(sample)
    assert url == "postgresql://ao_reader:p%40ss%2Fword@sample-data.railway.internal:5432/chinook", url
    from_connection(sample)
    assert parse_connection_strings("") == []
    assert is_vault_configured() is False
    revision = head_revision()
    assert revision, "alembic head revision not readable from /app/alembic"
    LOG.info("self-test ok (alembic head %s)", revision)
    return 0


def main() -> int:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
        stream=sys.stderr,
    )
    if APP_DIR not in sys.path:
        sys.path.insert(0, APP_DIR)
    if "--self-test" in sys.argv[1:]:
        return self_test()

    deadline = Deadline(env_int("TEMPLATE_STARTUP_WAIT_SECONDS", 900))

    wait_for_schema(deadline)
    best_effort("sample_connection", seed_sample_connection, deadline)
    best_effort("semantic_compilation", seed_semantic_compilation, deadline)
    exec_ingestion_service()
    return 0  # not reached


if __name__ == "__main__":
    sys.exit(main())
