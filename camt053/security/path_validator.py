"""Path validation and sanitization to prevent security vulnerabilities."""

import os
import re
import sys
import tempfile
from pathlib import Path


class PathValidationError(ValueError):
    """Raised when path validation fails."""


class SecurityError(PermissionError):
    """Raised when a security boundary is violated."""


def _get_allowed_bases_pathlib() -> list[Path]:
    """Return the allowed base directories as resolved ``Path`` objects."""
    bases = [
        Path.cwd().resolve(),
        Path(tempfile.gettempdir()).resolve(),
    ]
    if sys.platform != "win32":
        bases.append(Path(os.path.join(os.path.sep, "var", "tmp")).resolve())
    return bases


def _get_allowed_bases_str() -> list[str]:
    """Return the allowed base directories as resolved path strings."""
    bases = [
        os.path.realpath(os.getcwd()),
        os.path.realpath(tempfile.gettempdir()),
    ]
    if sys.platform != "win32":
        bases.append(os.path.realpath(os.path.join(os.path.sep, "var", "tmp")))
    return bases


def _is_allowed_directory(resolved_path: Path) -> bool:
    """Return ``True`` if ``resolved_path`` is under an allowed base dir."""
    try:
        allowed_bases = _get_allowed_bases_pathlib()
        resolved_str = str(resolved_path)
        return any(
            resolved_str == str(base)
            or resolved_str.startswith(str(base) + os.sep)
            for base in allowed_bases
        )
    except Exception:
        return False


def _resolve_within_allowed_bases(
    untrusted_path: str | Path,
    base_dir: str | Path | None = None,
) -> str:
    """Resolve ``untrusted_path`` and confirm it stays within an allowed base.

    Args:
        untrusted_path: The caller-supplied path to resolve.
        base_dir: If given, the only directory the path may resolve within;
            otherwise the working directory and temp directories are allowed.

    Returns:
        The sanitised, resolved path string.

    Raises:
        PathValidationError: If the path is empty or contains ``..``.
        SecurityError: If the resolved path escapes the allowed base(s).
    """
    if not untrusted_path:
        raise PathValidationError("Path cannot be empty")
    path_str = str(untrusted_path)
    if ".." in path_str:
        raise PathValidationError("Path contains invalid traversal sequences")
    normalized_str = os.path.normpath(path_str)
    try:
        resolved_str = os.path.realpath(normalized_str)
    except (RuntimeError, OSError) as e:
        raise PathValidationError(f"Invalid path: {e}") from e
    if base_dir is not None:
        base_str = os.path.realpath(str(base_dir))
        allowed_bases = [base_str]
    else:
        allowed_bases = _get_allowed_bases_str()
    for base in allowed_bases:
        if resolved_str == base or resolved_str.startswith(base + os.sep):
            return base + resolved_str[len(base) :]
    if base_dir:
        raise SecurityError(
            f"Path '{resolved_str}' escapes base directory '{base_dir}'."
        )
    raise SecurityError(
        f"Path '{resolved_str}' is outside allowed directories."
    )


def validate_path(
    untrusted_path: str | Path,
    must_exist: bool = False,
    base_dir: str | Path | None = None,
) -> str:
    """Validate and sanitise an untrusted filesystem path.

    Args:
        untrusted_path: The caller-supplied path to validate.
        must_exist: If ``True``, require the resolved path to exist.
        base_dir: Restrict the path to this directory if given.

    Returns:
        The sanitised, resolved path string, guaranteed to sit within an
        allowed base directory.

    Raises:
        PathValidationError: If the path is empty or contains traversal.
        SecurityError: If the path escapes the allowed base(s).
        FileNotFoundError: If ``must_exist`` and the path does not exist.
    """
    safe_path = _resolve_within_allowed_bases(untrusted_path, base_dir)
    if must_exist and not os.path.exists(safe_path):
        raise FileNotFoundError(f"Path does not exist: {safe_path}")
    return safe_path


def sanitize_for_log(user_input: str, max_length: int = 100) -> str:
    """Strip control characters and truncate a string for safe logging.

    Args:
        user_input: The raw string to sanitise.
        max_length: The maximum length before truncation (default 100).

    Returns:
        A single-line string with control characters removed, truncated with
        an ellipsis if it exceeded ``max_length``.
    """
    if not user_input:
        return ""
    sanitized = re.sub(r"[\r\n\t\x00-\x1f\x7f-\x9f]", "", user_input)
    if len(sanitized) > max_length:
        sanitized = sanitized[:max_length] + "..."
    return sanitized
