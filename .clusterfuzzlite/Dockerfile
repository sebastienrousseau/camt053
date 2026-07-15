# ClusterFuzzLite build image for camt053 (Python / Atheris).
# Used by the .github/workflows/cflite-*.yml workflows to build the fuzz
# targets in fuzz/ against the OSS-Fuzz Python base image.
# Pinned by digest for supply-chain reproducibility; kept current by Dependabot
# (docker ecosystem in .github/dependabot.yml). Tag: latest as of 2026-06-25.
FROM gcr.io/oss-fuzz-base/base-builder-python@sha256:8d46cb51bc42b45eeaa80b132a235f60a79154c788fe17012847a35304d8b804

COPY . $SRC/camt053
WORKDIR $SRC/camt053
COPY .clusterfuzzlite/build.sh $SRC/build.sh
