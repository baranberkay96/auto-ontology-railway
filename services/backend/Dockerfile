# Backend: NVIDIA's published Auto Ontology image, unchanged.
#
# A plain image source on nvcr.io deploys, but Railway's template composer rejects it
# ("Invalid Docker image"), so the image is pulled through this one-line build.
# AUTO_ONTOLOGY_IMAGE is a service variable; Railway passes service variables to Docker builds as
# build arguments. The base image's user, entrypoint and command are kept as they are.
ARG AUTO_ONTOLOGY_IMAGE=nvcr.io/nvidia/auto-ontology:1.1.0@sha256:d6d50ee5fb3617dce218ea9706e737c181e3eb6afcaf15cd954364a341aef57b
FROM ${AUTO_ONTOLOGY_IMAGE}
