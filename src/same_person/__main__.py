"""Print a short inventory of the development-set files."""

from __future__ import annotations

from same_person import __version__
from same_person.catalog import CATALOG
from same_person.load import count_records
from same_person.paths import data_dir, repo_root


def main() -> None:
    """Print table names, record counts, and whether each file is prose or columnar."""
    folder = data_dir(repo_root())
    print(f"same-person {__version__}")
    print(f"data {folder}")
    rows: list[tuple[str, str, str]] = []
    for spec in CATALOG:
        count = str(count_records(folder / spec.filename, header=not spec.prose))
        detail = "prose" if spec.prose else f"{len(spec.columns)} columns"
        rows.append((spec.table.value, count, detail))
    name_width = max(len(name) for name, _, _ in rows)
    count_width = max(len(count) for _, count, _ in rows)
    for name, count, detail in rows:
        print(f"{name:<{name_width}}  {count:>{count_width}}  {detail}")


if __name__ == "__main__":
    main()
