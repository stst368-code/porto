#!/usr/bin/env python3
"""Small filesystem helpers for build scripts.

Windows and OneDrive can hold transient handles on generated directories while a
build is replacing them.  These helpers retry destructive operations and clear
read-only attributes without changing the build's source/output contract.
"""
from __future__ import annotations

import os
import shutil
import stat
import time
from pathlib import Path


def _make_writable_and_retry(func, target: str, excinfo) -> None:
    """shutil.rmtree onexc handler: clear read-only and retry once."""
    try:
        mode = os.stat(target, follow_symlinks=False).st_mode
        os.chmod(target, mode | stat.S_IWUSR, follow_symlinks=False)
    except (FileNotFoundError, OSError):
        pass

    try:
        func(target)
    except FileNotFoundError:
        pass


def remove_path(path: str | Path, *, retries: int = 8, delay: float = 0.25) -> None:
    """Remove a file, symlink, or directory, retrying transient Windows locks.

    The delay increases on each retry.  A persistent failure is re-raised with
    the path and retry count so the build still fails loudly instead of silently
    leaving stale generated files behind.
    """
    target = Path(path)
    last_error: OSError | None = None

    for attempt in range(1, retries + 1):
        try:
            if target.is_symlink() or target.is_file():
                try:
                    mode = target.stat(follow_symlinks=False).st_mode
                    os.chmod(target, mode | stat.S_IWUSR, follow_symlinks=False)
                except (FileNotFoundError, OSError):
                    pass
                target.unlink(missing_ok=True)
            elif target.is_dir():
                shutil.rmtree(target, onexc=_make_writable_and_retry)
            else:
                return

            if not target.exists() and not target.is_symlink():
                return
        except (PermissionError, OSError) as exc:
            last_error = exc

        if attempt < retries:
            time.sleep(delay * attempt)

    raise RuntimeError(
        f"Unable to remove generated path after {retries} attempts: {target}"
    ) from last_error
