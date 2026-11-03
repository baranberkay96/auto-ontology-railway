# Ingestion: NVIDIA's published Auto Ontology image (backend + ingestion, one
# image) with a small start wrapper. The service itself is unmodified.
#
# AUTO_ONTOLOGY_IMAGE is a service variable on Ingestion; Railway passes service
# variables to Docker builds as build arguments. Keep it identical to the Backend
# service's image: both read and write the same schema, and the ingestion service
# refuses to start against a schema revision its image does not ship.
ARG AUTO_ONTOLOGY_IMAGE=nvcr.io/nvidia/auto-ontology:1.1.0@sha256:d6d50ee5fb3617dce218ea9706e737c181e3eb6afcaf15cd954364a341aef57b
FROM ${AUTO_ONTOLOGY_IMAGE}

# The application lives in /app and is not installed into /opt/venv, so a script
# outside /app needs it on the import path (the image's own processes run from /app).
ENV PYTHONPATH=/app

# /usr/local/bin exists in the base image; 0755 so the image's non-root user
# (auto_ontology, uid 1000) can run it.
COPY --chmod=0755 railway-ingestion.py /usr/local/bin/railway-ingestion

# Fail the build, not the deploy, if a future image no longer has the internals
# the wrapper uses (connection DAL, schema check, Alembic head).
RUN ["/usr/local/bin/railway-ingestion", "--self-test"]

# tini as in the base image; the wrapper exec()s the ingestion service, so tini
# forwards SIGTERM straight to uvicorn for a graceful scheduler shutdown.
ENTRYPOINT ["/usr/bin/tini", "--", "/usr/local/bin/railway-ingestion"]
CMD []
