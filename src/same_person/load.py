"""Read development-set CSVs without coercing identifiers or the token NA."""

from __future__ import annotations

import csv
from pathlib import Path

import pandas as pd

from same_person.catalog import Table, TableSpec, spec_for
from same_person.errors import SchemaError
from same_person.paths import data_dir


def table_path(table: Table | str, *, root: Path | None = None) -> Path:
    """Return the CSV path for ``table`` under ``root`` or the checkout."""
    return data_dir(root) / spec_for(table).filename


def require_columns(actual: tuple[str, ...], expected: tuple[str, ...], *, source: str) -> None:
    """Raise ``SchemaError`` when ``actual`` is not exactly ``expected``."""
    if actual != expected:
        raise SchemaError(
            f"{source} columns do not match the catalog. "
            f"Expected {list(expected)}. Found {list(actual)}."
        )


def read_table(path: Path, spec: TableSpec) -> pd.DataFrame:
    """Load a tabular CSV. Every cell is a string. Missing cells are empty strings."""
    columns = spec.columns
    if columns is None:
        raise ValueError(f"{spec.table.value} is prose. Use read_text.")
    if not path.is_file():
        raise FileNotFoundError(f"Missing data file for {spec.table.value}: {path}")
    frame = pd.read_csv(path, dtype=str, keep_default_na=False)
    actual = tuple(str(column) for column in frame.columns)
    require_columns(actual, columns, source=str(path))
    return frame


def read_text(path: Path, spec: TableSpec) -> list[str]:
    """Load a single-column prose CSV, including blank rows."""
    if not spec.prose:
        raise ValueError(f"{spec.table.value} has columns. Use read_table.")
    if not path.is_file():
        raise FileNotFoundError(f"Missing data file for {spec.table.value}: {path}")
    lines: list[str] = []
    with path.open(newline="", encoding="utf-8") as handle:
        for row in csv.reader(handle):
            if len(row) != 1:
                raise SchemaError(
                    f"{path} should have one column of text, found {len(row)} fields."
                )
            lines.append(row[0])
    return lines


def load_table(table: Table | str, *, root: Path | None = None) -> pd.DataFrame:
    """Load a tabular sheet from ``data/``."""
    spec = spec_for(table)
    return read_table(table_path(spec.table, root=root), spec)


def load_text(table: Table | str, *, root: Path | None = None) -> list[str]:
    """Load a prose sheet from ``data/``."""
    spec = spec_for(table)
    return read_text(table_path(spec.table, root=root), spec)


def count_records(path: Path, *, header: bool) -> int:
    """Count CSV records, respecting quotes that contain newlines."""
    if not path.is_file():
        raise FileNotFoundError(path)
    with path.open(newline="", encoding="utf-8") as handle:
        total = sum(1 for _ in csv.reader(handle))
    if header:
        return max(total - 1, 0)
    return total
