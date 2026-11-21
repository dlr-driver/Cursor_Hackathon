"""Identity resolution for name-screening alerts."""

from same_person.catalog import Table
from same_person.decisions import Decision, ReasonCode, check_reasons, parse_reason_codes
from same_person.load import load_table, load_text

__version__ = "0.1.0"

__all__ = [
    "Decision",
    "ReasonCode",
    "Table",
    "__version__",
    "check_reasons",
    "load_table",
    "load_text",
    "parse_reason_codes",
]
