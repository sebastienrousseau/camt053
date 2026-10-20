<!-- SPDX-License-Identifier: Apache-2.0 OR MIT -->

# Toolchain policy

Python 3.10 is the floor (`python = ">=3.10,<4.0"` in `pyproject.toml`), with
CI on 3.10, 3.11, 3.12, 3.13 and 3.14 on Linux, macOS and Windows. Raising the
floor is a maintainer decision, recorded in the changelog, and moves with the
rest of the camt053 suite in the same release. No distro-system Python is
supported.

Runtime dependencies carry upper bounds, and a dependency with a published
advisory is floored in `pyproject.toml` so no affected version can resolve
(for example `anyio>=4.14.2`). The CI and release tooling installs from
hash-pinned `requirements/*.txt`, regenerated with `make pip-compile`.
