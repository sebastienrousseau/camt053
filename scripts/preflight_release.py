#!/usr/bin/env python3
"""Check that a camt053 release is safe to tag.

The publish job runs on a pushed tag, which is the worst possible place
to discover a problem: by the time it complains the tag is public, and
fixing it means deleting and re-cutting a tag other people may already
have fetched.

Everything here is something the release workflow also checks, moved to
before the tag exists.

Usage:
    python3 scripts/preflight_release.py            # check
    python3 scripts/preflight_release.py --full     # + tests, build, audit
    python3 scripts/preflight_release.py --tag      # also create the tag
"""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

GREEN = "\033[32m"
RED = "\033[31m"
DIM = "\033[33m"
RESET = "\033[0m"

_problems: list[str] = []


def run(*args: str) -> subprocess.CompletedProcess[str]:
    """Run a command in the repository root and capture its output.

    Args:
        *args: The command and its arguments.

    Returns:
        The completed process.
    """
    return subprocess.run(  # noqa: S603 - fixed argv, no shell
        args, cwd=ROOT, capture_output=True, text=True, check=False
    )


def check(label: str, ok: bool, detail: str = "") -> bool:
    """Record and print one check.

    Args:
        label: What was checked.
        ok: Whether it passed.
        detail: Optional extra context.

    Returns:
        ``ok``, so callers can chain.
    """
    mark = f"{GREEN}✓{RESET}" if ok else f"{RED}✗{RESET}"
    suffix = f" — {detail}" if detail else ""
    print(f"  {mark} {label}{suffix}")
    if not ok:
        _problems.append(label)
    return ok


def declared_version() -> str | None:
    """Return the version declared in pyproject.toml.

    Returns:
        The version string, or ``None`` when it cannot be found.
    """
    text = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    match = re.search(r'^version = "([^"]+)"', text, re.M)
    return match.group(1) if match else None


def dunder_version() -> str | None:
    """Return ``camt053.__version__`` as written in the source.

    Parsed rather than imported so this works without an install.

    Returns:
        The version string, or ``None`` when it cannot be found.
    """
    text = (ROOT / "camt053" / "__init__.py").read_text(encoding="utf-8")
    match = re.search(r'^__version__ = "([^"]+)"', text, re.M)
    return match.group(1) if match else None


def main(argv: list[str] | None = None) -> int:
    """Run the pre-flight checks.

    Args:
        argv: Command-line arguments, for testing.

    Returns:
        ``0`` when everything passes, ``1`` otherwise.
    """
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("version", nargs="?", help="the version to release")
    parser.add_argument(
        "--full", action="store_true", help="also run tests, build and audit"
    )
    parser.add_argument(
        "--tag", action="store_true", help="create the signed tag"
    )
    args = parser.parse_args(argv)

    print("\nPre-flight checks:\n")

    toml_version = declared_version()
    init_version = dunder_version()
    check(
        "version is identical in pyproject.toml and __init__.py",
        toml_version is not None and toml_version == init_version,
        f"{toml_version} / {init_version}",
    )

    version = args.version or toml_version
    if not version:
        print("\nCannot determine the version to release.", file=sys.stderr)
        return 1
    print(f"\n  release candidate: v{version}\n")

    # The lock is the one that has bitten this family repeatedly: the
    # publish job installs with poetry, so a stale lock fails a release
    # that has already been tagged.
    lock_ok = run("poetry", "check", "--lock").returncode == 0
    check(
        "poetry.lock matches pyproject.toml",
        lock_ok,
        "" if lock_ok else "run `poetry lock` and commit the result",
    )

    dirty = run("git", "status", "--porcelain").stdout.strip()
    check(
        "working tree is clean",
        not dirty,
        f"{len(dirty.splitlines())} modified path(s)" if dirty else "",
    )

    branch = run("git", "rev-parse", "--abbrev-ref", "HEAD").stdout.strip()
    check("on main", branch == "main", branch)

    local = run("git", "rev-parse", "HEAD").stdout.strip()
    remote = run("git", "rev-parse", "origin/main").stdout.strip()
    ahead = run(
        "git", "rev-list", "--count", "origin/main..HEAD"
    ).stdout.strip()
    check(
        "HEAD matches origin/main",
        local == remote,
        f"{ahead} unpushed commit(s) — push them before tagging"
        if local != remote
        else "",
    )

    tag = f"v{version}"
    check(
        f"tag {tag} does not exist locally",
        not run("git", "tag", "-l", tag).stdout.strip(),
    )
    check(
        f"tag {tag} does not exist on origin",
        not run(
            "git", "ls-remote", "--tags", "origin", f"refs/tags/{tag}"
        ).stdout.strip(),
    )

    signing = run("git", "config", "--get", "user.signingkey").stdout.strip()
    check("tag signing key configured", bool(signing), signing)

    if args.full:
        print("\n  running slow checks…")
        tests = run("poetry", "run", "pytest", "-q")
        check(
            "test suite passes",
            tests.returncode == 0,
            tests.stdout.strip().splitlines()[-1] if tests.stdout else "",
        )
        check("package builds", run("poetry", "build").returncode == 0)
        audit = run("poetry", "run", "pip-audit", "--progress-spinner", "off")
        check(
            "pip-audit clean",
            audit.returncode == 0,
            "" if audit.returncode == 0 else "vulnerabilities reported",
        )
    else:
        print(
            f"  {DIM}–{RESET} test suite / build / audit — pass --full to run"
        )

    if _problems:
        print(f"\n{len(_problems)} problem(s): {'; '.join(_problems)}")
        print("Fix these before tagging — the publish job fails on them too,")
        print("but only after you have already pushed a tag.")
        return 1

    print("\nAll pre-flight checks passed.")

    if args.tag:
        message = f"camt053 {tag}"
        created = run("git", "tag", "-s", tag, "-m", message)
        if created.returncode != 0:
            print(f"\nFailed to create the tag: {created.stderr.strip()}")
            return 1
        print(f"{GREEN}✓{RESET} created signed tag {tag}")
        print(f"    push it with:  git push origin {tag}")
    else:
        print(f"Next:  python3 scripts/preflight_release.py {version} --tag")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
