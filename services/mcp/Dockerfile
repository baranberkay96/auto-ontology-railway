# MCP Server: NVIDIA's published Auto Ontology image, unchanged.
#
# A plain image source on nvcr.io deploys, but Railway's template composer rejects it
# ("Invalid Docker image"), so the image is pulled through this one-line build.
# AUTO_ONTOLOGY_MCP_IMAGE is a service variable; Railway passes service variables to Docker builds as
# build arguments. The base image's user, entrypoint and command are kept as they are.
ARG AUTO_ONTOLOGY_MCP_IMAGE=nvcr.io/nvidia/auto-ontology-mcp:1.1.0@sha256:3b8f9e5703c99d6521a572f1c777c0723e0f377dfcd7d08df6ff03475cfcaa26
FROM ${AUTO_ONTOLOGY_MCP_IMAGE}
