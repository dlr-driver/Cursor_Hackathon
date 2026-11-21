"""Workbook export follows the same catalog as the loader."""

from pathlib import Path

import pandas as pd
import pytest

from same_person.catalog import CATALOG
from same_person.errors import SchemaError
from same_person.export import export_workbook
from same_person.load import read_table, read_text


def test_export_rejects_a_workbook_with_the_wrong_sheets(tmp_path: Path) -> None:
    workbook = tmp_path / "bad.xlsx"
    pd.DataFrame({"a": [1]}).to_excel(workbook, index=False)
    with pytest.raises(SchemaError, match="do not match"):
        export_workbook(workbook, tmp_path / "out")


def test_export_round_trip_preserves_headers_and_prose(tmp_path: Path) -> None:
    workbook = tmp_path / "book.xlsx"
    with pd.ExcelWriter(workbook, engine="openpyxl") as writer:
        for spec in CATALOG:
            if spec.columns is None:
                pd.DataFrame(["Title", None, "Body"]).to_excel(
                    writer, sheet_name=spec.sheet, index=False, header=False
                )
            else:
                row = {column: f"{column}-value" for column in spec.columns}
                pd.DataFrame([row]).to_excel(writer, sheet_name=spec.sheet, index=False)

    out_dir = tmp_path / "data"
    written = export_workbook(workbook, out_dir)
    assert [path.name for path in written] == [spec.filename for spec in CATALOG]

    alerts = next(spec for spec in CATALOG if spec.filename == "Alerts.csv")
    frame = read_table(out_dir / alerts.filename, alerts)
    assert frame.loc[0, "alert_id"] == "alert_id-value"

    start_here = next(spec for spec in CATALOG if spec.filename == "Start_here.csv")
    assert read_text(out_dir / start_here.filename, start_here) == ["Title", "", "Body"]
