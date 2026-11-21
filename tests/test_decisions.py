"""Reason codes stay inside the decision they belong to."""

import pytest

from same_person import Decision, ReasonCode, Table, check_reasons, load_table, parse_reason_codes
from same_person.decisions import REASONS_FOR


def test_each_reason_belongs_to_one_decision() -> None:
    assigned = [code for codes in REASONS_FOR.values() for code in codes]
    assert set(assigned) == set(ReasonCode)
    assert len(assigned) == len(set(assigned))


def test_parse_reason_codes_splits_on_semicolons() -> None:
    codes = parse_reason_codes("NAME_DOB_LOCATION_MATCH; NAME_DOB_MATCH")
    assert codes == (ReasonCode.NAME_DOB_LOCATION_MATCH, ReasonCode.NAME_DOB_MATCH)


def test_blank_and_mismatched_codes_are_rejected() -> None:
    with pytest.raises(ValueError, match="at least one"):
        parse_reason_codes("  ")
    with pytest.raises(ValueError, match="does not use"):
        check_reasons(Decision.REVIEW, (ReasonCode.DOB_MISMATCH,))


def test_practice_labels_use_codes_allowed_for_their_decision() -> None:
    labels = load_table(Table.PRACTICE_LABELS)
    for row in labels.itertuples(index=False):
        decision = Decision(row.decision)
        check_reasons(decision, parse_reason_codes(row.reason_codes))
