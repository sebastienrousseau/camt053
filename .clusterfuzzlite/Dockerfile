# ClusterFuzzLite build image for camt053 (Python / Atheris).
# Used by the .github/workflows/cflite-*.yml workflows to build the fuzz
# targets in fuzz/ against the OSS-Fuzz Python base image.
# Pinned by digest for supply-chain reproducibility; kept current by Dependabot
# (docker ecosystem in .github/dependabot.yml). Tag: latest as of 2026-06-25.
FROM gcr.io/oss-fuzz-base/base-builder-python@sha256:030add5351585b43fb46a1939aad7c82dc11c7e690eaaaf118e8b71e3b674519

COPY . $SRC/camt053
WORKDIR $SRC/camt053
COPY .clusterfuzzlite/build.sh $SRC/build.sh
