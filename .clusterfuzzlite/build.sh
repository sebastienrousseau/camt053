#!/bin/bash -eu
# ClusterFuzzLite build script: compile every fuzz/fuzz_*.py harness into a
# libFuzzer binary placed in $OUT.
#
# Runtime deps are installed hash-pinned; the local camt053 package is added to
# PyInstaller's import search path (--paths) rather than via an un-pinnable
# `pip install .`. --collect-data camt053 bundles camt053's JSON schemas/XSDs so
# schema-backed entry points don't raise FileNotFoundError.

pip3 install --require-hashes -r "$SRC/camt053/requirements/fuzz.txt"

for harness in "$SRC"/camt053/fuzz/fuzz_*.py; do
  compile_python_fuzzer "$harness" \
    --collect-data camt053 \
    --paths "$SRC/camt053"
done
