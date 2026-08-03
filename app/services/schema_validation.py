"""Validate Investment.attributes against an InvestmentType.field_schema.

Single-source-of-truth validator. Reused by both create and update paths.
"""

from __future__ import annotations

import logging
from datetime import date, datetime
from decimal import Decimal

logger = logging.getLogger(__name__)


def _is_valid_date(value) -> bool:
    if isinstance(value, (date, datetime)):
        return True
    if not isinstance(value, str):
        return False
    try:
        date.fromisoformat(value)
        return True
    except ValueError:
        return False


def validate_attributes(field_schema: list[dict], attributes: dict) -> None:
    """Raise ValueError on missing required, wrong data_type, or unknown enum value.

    Extra keys not in the schema are allowed for forward-compat (warned).
    """
    schema_keys = {f["key"] for f in field_schema}

    for extra_key in set(attributes.keys()) - schema_keys:
        logger.warning("attributes contain key %r not present in field_schema", extra_key)

    for field in field_schema:
        key = field["key"]
        required = field.get("required", False)
        data_type = field["data_type"]
        value = attributes.get(key)

        if value is None or value == "":
            if required:
                raise ValueError(f"Missing required field: {key}")
            continue

        if data_type == "text":
            if not isinstance(value, str):
                raise ValueError(f"Field {key} must be text (str), got {type(value).__name__}")
        elif data_type in ("number", "percent"):
            if isinstance(value, bool) or not isinstance(value, (int, float, Decimal)):
                # allow numeric strings
                if not (isinstance(value, str) and _is_numeric_str(value)):
                    raise ValueError(f"Field {key} must be numeric, got {value!r}")
        elif data_type == "date":
            if not _is_valid_date(value):
                raise ValueError(f"Field {key} must be an ISO date string, got {value!r}")
        elif data_type == "enum":
            options = field.get("options") or []
            if value not in options:
                raise ValueError(f"Field {key} must be one of {options}, got {value!r}")
        else:
            raise ValueError(f"Unknown data_type {data_type!r} in field_schema for {key}")


def _is_numeric_str(s: str) -> bool:
    try:
        Decimal(s)
        return True
    except Exception:
        return False


def validate_additive_schema_change(old: list[dict], new: list[dict]) -> None:
    """Raise ValueError if `new` removes or renames any key that existed in `old`."""
    old_keys = {f["key"] for f in old}
    new_keys = {f["key"] for f in new}
    missing = old_keys - new_keys
    if missing:
        raise ValueError(f"Cannot remove existing field(s): {sorted(missing)}")
    # data_type / required of existing fields may change but keys must stay
