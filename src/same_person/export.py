"""Rebuild ``data/*.csv`` from the browse workbook."""

from __future__ import annotations

import argparse
import csv
from pathlib import Path

import pandas as pd

from same_person.catalog import CATALOG, TableSpec
from same_person.errors import SamePersonError, SchemaError
from same_person.load import require_columns
from same_person.paths import data_dir


def export_workbook(workbook: Path, out_dir: Path) -> list[Path]:
    """Write one CSV per catalog sheet. Sheet names and column order must match."""
    workbook = Path(workbook)
    out_dir = Path(out_dir)
    if not workbook.is_file():
        raise FileNotFoundError(workbook)
    out_dir.mkdir(parents=True, exist_ok=True)
    try:
        book = pd.ExcelFile(workbook)
    except ImportError as exc:
        raise SamePersonError(
            "Reading .xlsx files requires openpyxl. Install the dev extra: pip install -e '.[dev]'"
        ) from exc

    expected = [spec.sheet for spec in CATALOG]
    actual = list(book.sheet_names)
    if actual != expected:
        raise SchemaError(
            f"Workbook sheets do not match the catalog. Expected {expected}. Found {actual}."
        )

    written: list[Path] = []
    for spec in CATALOG:
        path = out_dir / spec.filename
        if spec.prose:
            _write_prose(book, spec, path)
        else:
            _write_table(book, spec, path)
        written.append(path)
    return written


def _write_prose(book: pd.ExcelFile, spec: TableSpec, path: Path) -> None:
    frame = pd.read_excel(book, sheet_name=spec.sheet, header=None, dtype=str)
    if frame.shape[1] != 1:
        raise SchemaError(
            f"{spec.sheet} should be a single column of text, found {frame.shape[1]} columns."
        )
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        for value in frame.iloc[:, 0].fillna(""):
            writer.writerow([value])


def _write_table(book: pd.ExcelFile, spec: TableSpec, path: Path) -> None:
    columns = spec.columns
    if columns is None:
        raise ValueError(f"{spec.table.value} is prose. Use the prose writer.")
    frame = pd.read_excel(book, sheet_name=spec.sheet, dtype=str)
    actual = tuple(str(column) for column in frame.columns)
    require_columns(actual, columns, source=spec.sheet)
    frame.fillna("").to_csv(path, index=False)


def main(argv: list[str] | None = None) -> None:
    """Overwrite CSVs from a workbook. Defaults to the checkout ``data/`` directory."""
    parser = argparse.ArgumentParser(
        description="Write one CSV per sheet from the screening workbook."
    )
    parser.add_argument("workbook", type=Path, help="Path to the .xlsx browse workbook.")
    parser.add_argument(
        "--out",
        type=Path,
        default=None,
        help="Output directory. Defaults to the checkout data/ directory and overwrites it.",
    )
    args = parser.parse_args(argv)
    out_dir = args.out if args.out is not None else data_dir()
    for path in export_workbook(args.workbook, out_dir):
        print(path)


if __name__ == "__main__":
    main()
