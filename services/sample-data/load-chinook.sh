#!/bin/bash
# Sample Data, first boot only (official postgres entrypoint, initdb phase; runs
# as the postgres user against the temporary, socket-only server).
#
# 1. Loads the Chinook sample database into POSTGRES_DB (chinook). The upstream
#    script starts with DROP DATABASE / CREATE DATABASE chinook / \c chinook;
#    those three lines are removed, because the entrypoint already created the
#    database and is connected to the server, not to a database it may drop.
# 2. Creates the login Auto Ontology uses for it: SELECT on the Chinook tables
#    only, read-only by default (default_transaction_read_only), a statement
#    timeout, and no CONNECT on the server's other databases.
#
# Later boots skip this file (the data directory already exists). To change the
# reader password afterwards, run ALTER ROLE as the superuser and update
# SAMPLE_DB_READER_PASSWORD on this service (Ingestion references it).
set -euo pipefail

# Same as the entrypoint's own docker_process_sql: Railway sets PGHOST to this
# service's private domain, but during initdb the server only listens on the
# local socket.
unset PGHOST PGHOSTADDR

SQL=/opt/railway-sample/Chinook_PostgreSql.sql
DB="${POSTGRES_DB:?POSTGRES_DB is required}"
READER="${SAMPLE_DB_READER_USER:-ao_reader}"
PASSWORD="${SAMPLE_DB_READER_PASSWORD:-}"
TIMEOUT="${SAMPLE_DB_READER_STATEMENT_TIMEOUT:-120s}"

log() { echo "load-chinook: $*"; }
fail() { log "$*" >&2; exit 1; }
run_psql() { psql -v ON_ERROR_STOP=1 --no-psqlrc --quiet --username "$POSTGRES_USER" "$@"; }

[ -n "$PASSWORD" ] || fail "SAMPLE_DB_READER_PASSWORD is empty; refusing to create a login without a password"
case "$READER" in
  "" | *[!a-z0-9_]* | [0-9]*) fail "SAMPLE_DB_READER_USER must start with a letter or _ and use only a-z, 0-9 and _ (got: $READER)" ;;
esac
case "$TIMEOUT" in
  "" | *[!0-9a-z]*) fail "SAMPLE_DB_READER_STATEMENT_TIMEOUT must look like 120s, 2min or 0 (got: $TIMEOUT)" ;;
esac
[ "$READER" != "$POSTGRES_USER" ] || fail "SAMPLE_DB_READER_USER must differ from POSTGRES_USER"

BODY=$(mktemp)
trap 'rm -f "$BODY"' EXIT
sed -e '/^DROP DATABASE IF EXISTS chinook;$/d' \
    -e '/^CREATE DATABASE chinook;$/d' \
    -e '/^\\c chinook;$/d' "$SQL" > "$BODY"
# Exactly those three lines must be gone, and nothing else may switch databases.
removed=$(( $(wc -l < "$SQL") - $(wc -l < "$BODY") ))
[ "$removed" -eq 3 ] || fail "unexpected Chinook script layout ($removed header lines matched, expected 3)"
if grep -qiE '^[[:space:]]*(\\c(onnect)?[[:space:]]|(create|drop)[[:space:]]+database[^;]*;)' "$BODY"; then
  fail "Chinook script still switches or creates databases; refusing to load it"
fi

log "loading the Chinook sample database into $DB"
run_psql --dbname "$DB" -f "$BODY"

log "creating read-only login $READER"
run_psql --dbname "$DB" -v db="$DB" -v reader="$READER" -v password="$PASSWORD" -v timeout="$TIMEOUT" <<'SQL'
CREATE ROLE :"reader" LOGIN PASSWORD :'password' NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION;
ALTER ROLE :"reader" SET default_transaction_read_only = on;
ALTER ROLE :"reader" SET statement_timeout = :'timeout';
REVOKE ALL ON DATABASE :"db" FROM PUBLIC;
GRANT CONNECT ON DATABASE :"db" TO :"reader";
REVOKE CREATE ON SCHEMA public FROM PUBLIC;
GRANT USAGE ON SCHEMA public TO :"reader";
GRANT SELECT ON ALL TABLES IN SCHEMA public TO :"reader";
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT ON TABLES TO :"reader";
REVOKE CONNECT ON DATABASE postgres FROM PUBLIC;
SQL

tracks=$(run_psql --dbname "$DB" -tA -c 'SELECT count(*) FROM track')
invoices=$(run_psql --dbname "$DB" -tA -c 'SELECT count(*) FROM invoice')
log "done: $tracks tracks, $invoices invoices; login $READER can read database $DB"
