"""Decision and reason-code vocabulary from the screening SOP."""

from __future__ import annotations

from enum import StrEnum


class Decision(StrEnum):
    """Whether a hit is the customer."""

    DIFFERENT_ENTITY = "DIFFERENT_ENTITY"
    SAME_ENTITY = "SAME_ENTITY"
    REVIEW = "REVIEW"


class ReasonCode(StrEnum):
    """The main reason that supports a decision. Several may be cited."""

    TEMPORAL_IMPOSSIBILITY = "TEMPORAL_IMPOSSIBILITY"
    DOB_MISMATCH = "DOB_MISMATCH"
    LOCATION_MISMATCH = "LOCATION_MISMATCH"
    NAME_MISMATCH_VERIFIED = "NAME_MISMATCH_VERIFIED"
    ENTITY_TYPE_MISMATCH = "ENTITY_TYPE_MISMATCH"
    DECEASED = "DECEASED"
    NAME_DOB_LOCATION_MATCH = "NAME_DOB_LOCATION_MATCH"
    NAME_DOB_MATCH = "NAME_DOB_MATCH"
    NAME_LOCATION_MATCH = "NAME_LOCATION_MATCH"
    INSUFFICIENT_DATA = "INSUFFICIENT_DATA"
    AMBIGUOUS_CUSTOMER_RECORD = "AMBIGUOUS_CUSTOMER_RECORD"


REASONS_FOR: dict[Decision, frozenset[ReasonCode]] = {
    Decision.DIFFERENT_ENTITY: frozenset(
        {
            ReasonCode.TEMPORAL_IMPOSSIBILITY,
            ReasonCode.DOB_MISMATCH,
            ReasonCode.LOCATION_MISMATCH,
            ReasonCode.NAME_MISMATCH_VERIFIED,
            ReasonCode.ENTITY_TYPE_MISMATCH,
            ReasonCode.DECEASED,
        }
    ),
    Decision.SAME_ENTITY: frozenset(
        {
            ReasonCode.NAME_DOB_LOCATION_MATCH,
            ReasonCode.NAME_DOB_MATCH,
            ReasonCode.NAME_LOCATION_MATCH,
        }
    ),
    Decision.REVIEW: frozenset(
        {
            ReasonCode.INSUFFICIENT_DATA,
            ReasonCode.AMBIGUOUS_CUSTOMER_RECORD,
        }
    ),
}


def _check_reason_map() -> None:
    if set(REASONS_FOR) != set(Decision):
        raise RuntimeError("Every decision needs a reason-code set.")
    seen: set[ReasonCode] = set()
    for codes in REASONS_FOR.values():
        overlap = seen & codes
        if overlap:
            names = ", ".join(sorted(code.value for code in overlap))
            raise RuntimeError(f"Reason codes assigned to more than one decision: {names}.")
        seen |= codes
    missing = set(ReasonCode) - seen
    if missing:
        names = ", ".join(sorted(code.value for code in missing))
        raise RuntimeError(f"Reason codes missing from the policy map: {names}.")


_check_reason_map()


def parse_reason_codes(raw: str) -> tuple[ReasonCode, ...]:
    """Split a practice-label ``reason_codes`` cell on semicolons."""
    if raw.strip() == "":
        raise ValueError("A decision needs at least one reason code.")
    codes: list[ReasonCode] = []
    for part in raw.split(";"):
        token = part.strip()
        if token == "":
            raise ValueError(f"Blank reason code in {raw!r}.")
        codes.append(ReasonCode(token))
    return tuple(codes)


def check_reasons(decision: Decision, codes: tuple[ReasonCode, ...]) -> None:
    """Raise ``ValueError`` when a code is not allowed for ``decision``."""
    if not codes:
        raise ValueError(f"{decision.value} needs at least one reason code.")
    allowed = REASONS_FOR[decision]
    invalid = [code.value for code in codes if code not in allowed]
    if invalid:
        raise ValueError(f"{decision.value} does not use {', '.join(invalid)}.")
