# Sample Data: Railway's Postgres 18 image with the Chinook sample database
# (MIT, Luis Rocha) loaded into POSTGRES_DB (chinook) on first boot, plus a
# read-only login for Auto Ontology.
#
# Same image as the Postgres service (Railway's postgres-ssl, tini + wrapper.sh,
# SSL, volume checks). Nothing here changes ENTRYPOINT or CMD; the official
# postgres entrypoint runs /docker-entrypoint-initdb.d/* once, when the volume's
# data directory is empty.
FROM ghcr.io/railwayapp-templates/postgres-ssl:18

# Chinook 1.4.5, PostgreSQL script, fetched from a commit (immutable URL) and
# checked against the SHA-256 recorded when the template was written. A changed
# file fails the build instead of loading unknown SQL.
ADD https://raw.githubusercontent.com/lerocha/chinook-database/7f67772503d71ba90f19283c38e93923addb43fa/ChinookDatabase/DataSources/Chinook_PostgreSql.sql /opt/railway-sample/Chinook_PostgreSql.sql
RUN echo "e3fde5c1a5b51a2a91429a702c9ca6e69ba56e6c7f5e112724d70c3d03db695e  /opt/railway-sample/Chinook_PostgreSql.sql" | sha256sum -c - \
 && chmod 0755 /opt/railway-sample \
 && chmod 0644 /opt/railway-sample/Chinook_PostgreSql.sql \
 && grep -q "CREATE DATABASE chinook;" /opt/railway-sample/Chinook_PostgreSql.sql

# /docker-entrypoint-initdb.d already exists in the base image (0755); the script
# runs as the postgres user, so it must be world-readable and executable.
COPY --chmod=0755 load-chinook.sh /docker-entrypoint-initdb.d/50-load-chinook.sh
