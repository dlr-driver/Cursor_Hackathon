"""Locate the checkout that holds ``pyproject.toml`` and ``data/``."""

from __future__ import annotations

import os
from pathlib import Path


def repo_root() -> Path:
    """Return the repository root.

    ``SAME_PERSON_ROOT`` overrides discovery. That is useful in notebooks
    whose working directory is not the checkout.
    """
    override = os.environ.get("SAME_PERSON_ROOT")
    if override:
        root = Path(override).expanduser().resolve()
        if not (root / "pyproject.toml").is_file():
            raise FileNotFoundError(f"SAME_PERSON_ROOT does not contain pyproject.toml: {root}")
        return root

    start = Path(__file__).resolve()
    for candidate in start.parents:
        marker = candidate / "src" / "same_person" / "__init__.py"
        if (candidate / "pyproject.toml").is_file() and marker.is_file():
            return candidate
    raise FileNotFoundError(
        "Could not find the repository root. Set SAME_PERSON_ROOT to the checkout."
    )


def data_dir(root: Path | None = None) -> Path:
    """Return the directory that holds one CSV per workbook sheet."""
    return (root or repo_root()) / "data"
