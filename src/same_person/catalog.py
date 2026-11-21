"""Column contract for the development-set CSVs."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from same_person.errors import UnknownTableError


class Table(StrEnum):
    """A sheet from the browse workbook, in workbook order."""

    START_HERE = "start_here"
    ALERTS = "alerts"
    HITS = "hits"
    CUSTOMERS = "customers"
    ACCOUNTS = "accounts"
    ONBOARDING = "onboarding"
    KYC_CHECKS = "kyc_checks"
    NOTES = "notes"
    SEARCH_RESULTS = "search_results"
    PRACTICE_LABELS = "practice_labels"
    POLICY = "policy"


@dataclass(frozen=True, slots=True)
class TableSpec:
    """One exported sheet and the columns the loader expects."""

    table: Table
    sheet: str
    filename: str
    description: str
    columns: tuple[str, ...] | None = None
    key: tuple[str, ...] = ()

    @property
    def prose(self) -> bool:
        """True for the orientation and policy sheets, which have no header."""
        return self.columns is None

    def __post_init__(self) -> None:
        if self.prose:
            if self.key:
                raise ValueError(f"{self.table.value} is prose and cannot have a key.")
            return
        missing = [column for column in self.key if column not in self.columns]
        if missing:
            raise ValueError(f"{self.table.value} key {missing} is not in its columns.")


CATALOG: tuple[TableSpec, ...] = (
    TableSpec(
        table=Table.START_HERE,
        sheet="Start here",
        filename="Start_here.csv",
        description="How the development set is organised and how the sheets join.",
    ),
    TableSpec(
        table=Table.ALERTS,
        sheet="Alerts",
        filename="Alerts.csv",
        description="One row per screening alert: the customer as screened, plus hit ids.",
        columns=(
            "alert_id",
            "screened_at",
            "customer_name",
            "entity_type",
            "dob",
            "country",
            "city",
            "account_ref",
            "login_handle",
            "email",
            "hit_count",
            "hit_ids",
        ),
        key=("alert_id",),
    ),
    TableSpec(
        table=Table.HITS,
        sheet="Hits",
        filename="Hits.csv",
        description="One watchlist profile that matched an alert.",
        columns=(
            "hit_id",
            "alert_id",
            "match_score",
            "entity_type",
            "name",
            "aliases",
            "gender",
            "dobs",
            "place_of_birth",
            "life_status",
            "deceased_date",
            "nationality",
            "citizenship",
            "countries",
            "addresses",
            "identifiers",
            "categories",
            "primary_category",
            "position_or_allegation",
            "details",
            "relationships",
            "profile_notes",
            "sources",
            "source_urls",
        ),
        key=("hit_id",),
    ),
    TableSpec(
        table=Table.CUSTOMERS,
        sheet="Customers",
        filename="Customers.csv",
        description="The bank's system of record.",
        columns=(
            "record_id",
            "entity_type",
            "full_name",
            "preferred_name",
            "login_name",
            "dob",
            "nationality",
            "residence_country",
            "city",
            "address",
            "email",
            "phone",
            "occupation",
            "employer",
            "registration_number",
            "onboarded_at",
            "status",
            "last_kyc_refresh",
        ),
        key=("record_id",),
    ),
    TableSpec(
        table=Table.ACCOUNTS,
        sheet="Accounts",
        filename="Accounts.csv",
        description="Account numbers and logins. Joint accounts repeat the account id.",
        columns=(
            "account_id",
            "customer_id",
            "login_handle",
            "phone",
            "opened_at",
            "status",
        ),
        key=("account_id", "customer_id"),
    ),
    TableSpec(
        table=Table.ONBOARDING,
        sheet="Onboarding",
        filename="Onboarding.csv",
        description="Link from an account and customer to a KYC applicant.",
        columns=(
            "account_id",
            "customer_id",
            "kyc_applicant_id",
            "onboarded_at",
        ),
        key=("account_id", "customer_id"),
    ),
    TableSpec(
        table=Table.KYC_CHECKS,
        sheet="KYC checks",
        filename="KYC_checks.csv",
        description="Identity checks from the KYC provider, keyed by applicant id.",
        columns=(
            "check_id",
            "applicant_id",
            "provider",
            "verified_name",
            "verified_dob",
            "document_type",
            "document_number",
            "document_country",
            "result",
            "checked_at",
        ),
        key=("check_id",),
    ),
    TableSpec(
        table=Table.NOTES,
        sheet="Notes",
        filename="Notes.csv",
        description="Support and onboarding notes, filed by the customer's email.",
        columns=(
            "note_id",
            "requester_email",
            "created_at",
            "channel",
            "text",
        ),
        key=("note_id",),
    ),
    TableSpec(
        table=Table.SEARCH_RESULTS,
        sheet="Search results",
        filename="Search_results.csv",
        description="Web search results by name. Most are about namesakes.",
        columns=(
            "result_id",
            "query",
            "title",
            "snippet",
            "source",
        ),
        key=("result_id",),
    ),
    TableSpec(
        table=Table.PRACTICE_LABELS,
        sheet="Practice labels",
        filename="Practice_labels.csv",
        description="Answered hits from the development set, including the path to the answer.",
        columns=(
            "hit_id",
            "alert_id",
            "decision",
            "reason_codes",
            "customer_record_ids",
            "evidence",
            "reference_reason",
            "path",
        ),
        key=("hit_id",),
    ),
    TableSpec(
        table=Table.POLICY,
        sheet="Policy",
        filename="Policy.csv",
        description="The identity SOP, followed by the name-variant groups.",
    ),
)


def _index(specs: tuple[TableSpec, ...]) -> dict[Table, TableSpec]:
    by_table: dict[Table, TableSpec] = {}
    filenames: set[str] = set()
    sheets: set[str] = set()
    for spec in specs:
        if spec.table in by_table:
            raise ValueError(f"Duplicate table {spec.table.value}.")
        if spec.filename in filenames:
            raise ValueError(f"Duplicate filename {spec.filename}.")
        if spec.sheet in sheets:
            raise ValueError(f"Duplicate sheet {spec.sheet}.")
        by_table[spec.table] = spec
        filenames.add(spec.filename)
        sheets.add(spec.sheet)
    missing = set(Table) - set(by_table)
    if missing:
        names = ", ".join(sorted(item.value for item in missing))
        raise ValueError(f"Catalog is missing {names}.")
    return by_table


BY_TABLE: dict[Table, TableSpec] = _index(CATALOG)


def spec_for(table: Table | str) -> TableSpec:
    """Return the catalog entry for a table enum or its value, such as ``"alerts"``."""
    if isinstance(table, Table):
        return BY_TABLE[table]
    try:
        return BY_TABLE[Table(str(table))]
    except ValueError as exc:
        known = ", ".join(item.value for item in Table)
        raise UnknownTableError(f"Unknown table {table!r}. Known tables: {known}.") from exc
