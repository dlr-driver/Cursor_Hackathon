"""Catalog integrity."""

import pytest

from same_person.catalog import CATALOG, Table, spec_for
from same_person.errors import UnknownTableError


def test_catalog_covers_every_table() -> None:
    assert {spec.table for spec in CATALOG} == set(Table)


def test_filenames_are_unique() -> None:
    names = [spec.filename for spec in CATALOG]
    assert len(names) == len(set(names))


def test_spec_for_accepts_the_table_value() -> None:
    assert spec_for("alerts").filename == "Alerts.csv"
    assert spec_for(Table.HITS).key == ("hit_id",)


def test_spec_for_rejects_unknown_names() -> None:
    with pytest.raises(UnknownTableError, match="Unknown table"):
        spec_for("watchlist")
