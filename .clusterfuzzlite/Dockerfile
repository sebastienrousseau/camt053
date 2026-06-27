# ClusterFuzzLite build image for camt053 (Python / Atheris).
# Used by the .github/workflows/cflite-*.yml workflows to build the fuzz
# targets in fuzz/ against the OSS-Fuzz Python base image.
# Pinned by digest for supply-chain reproducibility; kept current by Dependabot
# (docker ecosystem in .github/dependabot.yml). Tag: latest as of 2026-06-25.
FROM gcr.io/oss-fuzz-base/base-builder-python@sha256:e0e18dea5d2e4107a4f5d04652e6c278fbea32dc6d6861ee8de29402d0916746

COPY . $SRC/camt053
WORKDIR $SRC/camt053
COPY .clusterfuzzlite/build.sh $SRC/build.sh
