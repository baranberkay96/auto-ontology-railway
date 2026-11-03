# Frontend: NVIDIA's published Auto Ontology image, unchanged.
#
# A plain image source on nvcr.io deploys, but Railway's template composer rejects it
# ("Invalid Docker image"), so the image is pulled through this one-line build.
# AUTO_ONTOLOGY_FRONTEND_IMAGE is a service variable; Railway passes service variables to Docker builds as
# build arguments. The base image's user, entrypoint and command are kept as they are.
ARG AUTO_ONTOLOGY_FRONTEND_IMAGE=nvcr.io/nvidia/auto-ontology-frontend:1.1.0@sha256:c45cbd9a15169d159a5752ab054595773324393af9aac23acef9221fbe716b97
FROM ${AUTO_ONTOLOGY_FRONTEND_IMAGE}
