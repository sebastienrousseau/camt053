# Contributing to Camt053

Thank you for your interest in contributing to Camt053. This guide covers
the development workflow and standards.

## Development Setup

### Prerequisites

- Python 3.9.2+
- [Poetry](https://python-poetry.org/docs/#installation)
- Git with SSH commit signing configured

### Setup

```bash
# Clone and install
git clone git@github.com:sebastienrousseau/camt053.git
cd camt053
poetry install

# Verify
poetry run pytest tests/ -q
```

### On macOS

```bash
brew install python@3.12 poetry
```

### On Linux (Debian/Ubuntu)

```bash
sudo apt install python3 python3-pip
pip install poetry
```

### On WSL

```bash
sudo apt install python3 python3-pip
pip install poetry
# Ensure ~/.local/bin is in PATH
```

## Workflow

1. **Fork** the repository
2. **Create a branch** from `main`:
   ```bash
   git checkout -b feat/my-feature
   ```
   Use a `feat/`, `fix/`, `docs/`, or `chore/` prefix that matches the kind of
   change.
3. **Make changes** — follow the coding standards below
4. **Run tests** — coverage must remain at **100%**:
   ```bash
   poetry run pytest tests/ -v
   ```
5. **Run linters and type checks**:
   ```bash
   poetry run ruff check camt053/
   poetry run black --check camt053/ tests/
   poetry run mypy camt053/
   ```
6. **Sign and commit** (see [Commit Signing](#commit-signing-required)):
   ```bash
   git commit -S -m "feat: add my feature"
   ```
7. **Push** and open a pull request against `main`, filling in the PR template

## Branch Protection

`main` is a protected branch. Changes land **only** through a pull request that
satisfies all of the following:

- **Pull request required** — direct pushes to `main` are rejected.
- **Green CI** — every required check (test matrix, smoke tests, lint, type
  check, security scan, and CodeQL) must pass.
- **Signed commits** — all commits in the PR must be verified (SSH or GPG).
- **Conversation resolution** — all review comments must be resolved before
  merge.
- **Up to date with `main`** — rebase onto the latest `main` if it has moved.

`CODEOWNERS` automatically requests review from the maintainer on every PR.

## Commit Signing (Required)

All commits **must** be signed with SSH or GPG.

### SSH Signing

```bash
git config --global gpg.format ssh
git config --global user.signingkey ~/.ssh/id_ed25519
git config --global commit.gpgsign true
```

### Commit Message Format

Use [Conventional Commits](https://www.conventionalcommits.org/):

```
feat: add LEI validation for account owners
fix: handle empty IBAN in account identification
docs: update README with API examples
test: add gold master for acmt.019
refactor: simplify XML data preparer dispatch
```

## Coding Standards

The following tools are run in CI and must pass locally before you push:

- **Ruff** (`ruff check camt053/`) — linting.
- **Black** `26.5.1` (`black --check camt053/ tests/`) — formatting; pin the
  same version locally to avoid spurious diffs.
- **mypy** `--strict` (`mypy camt053/`) — static type checking.

In addition:

- **Line length:** 79 characters (enforced by Black + Ruff)
- **Type hints:** Required on all public functions (mypy strict)
- **Docstrings:** Required on all public classes and functions
- **Tests:** Every new feature must include tests; coverage must stay at
  **100%** — the suite fails below that threshold

## Testing

```bash
# Full suite
poetry run pytest tests/ -v

# By marker
poetry run pytest -m integration      # End-to-end tests
poetry run pytest -m version_compat   # Version compatibility
poetry run pytest -m security         # Security tests

# Single file
poetry run pytest tests/test_version_matrix.py -v
```

## Pull Request Checklist

The PR template captures this checklist; the essentials are:

- [ ] All tests pass (`poetry run pytest`)
- [ ] Coverage remains at **100%**
- [ ] Linters and type checks pass (`ruff check`, `black --check`, `mypy`)
- [ ] Commits are signed (SSH or GPG)
- [ ] PR title follows conventional commit format
- [ ] PR is linked to a tracking issue
- [ ] All review conversations are resolved
- [ ] New features include tests and documentation, and `CHANGELOG.md` is
      updated

## License

By contributing, you agree that your contributions will be licensed under
the [Apache License 2.0](LICENSE).
