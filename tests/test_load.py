"""Readers keep the development-set contract."""

from __future__ import annotations

import csv
from pathlib import Path

import pandas as pd
import pytest

from same_person import Table, load_table, load_text
from same_person.__main__ import main
from same_person.catalog import CATALOG, TableSpec
from same_person.errors import SchemaError
from same_person.load import count_records, read_table, table_path


def test_checked_in_headers_match_the_catalog() -> None:
    for spec in CATALOG:
        path = table_path(spec.table)
        assert path.is_file(), path
        with path.open(newline="", encoding="utf-8") as handle:
            header = next(csv.reader(handle))
        if spec.prose:
            assert header
        else:
            assert tuple(header) == spec.columns


def test_keys_are_unique() -> None:
    for spec in CATALOG:
        if not spec.key:
            continue
        frame = pd.read_csv(
            table_path(spec.table),
            usecols=list(spec.key),
            dtype=str,
            keep_default_na=False,
        )
        duplicates = int(frame.duplicated().sum())
        assert duplicates == 0, f"{spec.table.value} has {duplicates} duplicate keys"


def test_practice_label_sample_survives_the_string_loader() -> None:
    labels = load_table(Table.PRACTICE_LABELS)
    assert len(labels) == 50
    row = labels.loc[labels["hit_id"] == "H-582410"].iloc[0]
    assert row["alert_id"] == "A-145983"
    assert row["decision"] == "SAME_ENTITY"


def test_start_here_keeps_the_title_and_blank_lines() -> None:
    lines = load_text(Table.START_HERE)
    assert lines[0] == "Same Person or Not? The development set, for browsing"
    assert "" in lines
    assert len(lines) == 27


def test_placeholder_token_is_not_read_as_missing(tmp_path: Path) -> None:
    spec = _customers()
    row = {column: "" for column in spec.columns or ()}
    row["record_id"] = "CUS-1"
    row["full_name"] = "NA"
    path = tmp_path / spec.filename
    pd.DataFrame([row]).to_csv(path, index=False)
    frame = read_table(path, spec)
    assert frame.loc[0, "full_name"] == "NA"
    assert frame.loc[0, "preferred_name"] == ""


def test_schema_mismatch_names_both_sides(tmp_path: Path) -> None:
    spec = _customers()
    path = tmp_path / spec.filename
    pd.DataFrame([{"record_id": "CUS-1"}]).to_csv(path, index=False)
    with pytest.raises(SchemaError, match="record_id"):
        read_table(path, spec)


def test_missing_file_names_the_table(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError, match="alerts"):
        load_table(Table.ALERTS, root=tmp_path)


def test_inventory_reports_the_checked_in_counts(capsys: pytest.CaptureFixture[str]) -> None:
    main()
    output = capsys.readouterr().out
    assert "same-person 0.1.0" in output
    assert "alerts" in output
    assert "440" in output
    assert "practice_labels" in output
    alerts = table_path(Table.ALERTS)
    assert count_records(alerts, header=True) == 440


def _customers() -> TableSpec:
    spec = next(item for item in CATALOG if item.table is Table.CUSTOMERS)
    assert spec.columns is not None
    return spec
