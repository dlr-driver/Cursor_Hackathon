"""Errors raised when the catalog and the files disagree."""


class SamePersonError(Exception):
    """Base error for this package."""


class UnknownTableError(SamePersonError):
    """The caller asked for a table that is not in the catalog."""


class SchemaError(SamePersonError):
    """A file or workbook does not match the catalog."""
