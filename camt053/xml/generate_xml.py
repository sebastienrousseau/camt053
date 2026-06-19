"""XML generator for ISO 20022 camt.053 reversing-entry statements."""

import os
from typing import Any

from camt053.constants import REVERSAL_MESSAGE_TYPE, TEMPLATES_DIR
from camt053.exceptions import ReversalGenerationError
from camt053.models import Statement
from camt053.reversal.reversal import build_reversal_records
from camt053.security import validate_path
from camt053.xml.template_env import get_template
from camt053.xml.validate_via_xsd import validate_xml_string_via_xsd

# ── Flat reversing-entry vocabulary ──────────────────────────────────
# A reversing-entry record carries the statement header (from the first
# record) and one reversed entry. ``build_reversal_records`` produces these
# from a parsed statement; ``generate_reversal_xml`` renders + validates them.

_HEADER_FIELDS = [
    "statement_msg_id",
    "creation_date_time",
    "statement_id",
    "electronic_seq_nb",
    "account_id",
    "account_id_other",
    "account_currency",
    "account_owner_name",
    "account_servicer_bic",
    "bal_type_code",
    "bal_amount",
    "bal_currency",
    "bal_credit_debit",
    "bal_date",
]

_ENTRY_FIELDS = [
    "entry_ref",
    "original_ref",
    "amount",
    "currency",
    "credit_debit",
    "reversal_indicator",
    "status",
    "booking_date",
    "value_date",
    "end_to_end_id",
    "tx_id",
    "reason_code",
    "reason_name",
    "additional_info",
    "counterparty_name",
    "counterparty_account",
]

_ALL_FIELDS = _HEADER_FIELDS + _ENTRY_FIELDS


def _build_record(row: dict[str, Any]) -> dict[str, Any]:
    """Project a raw record onto the known reversing-entry vocabulary."""
    return {field: row.get(field, "") for field in _ALL_FIELDS}


def _build_context(records: list[dict[str, Any]]) -> dict[str, Any]:
    """Build a render context from reversing-entry records.

    The first record populates the statement header; every record is exposed
    via ``records`` so the template can iterate over the reversed entries.
    """
    context = _build_record(records[0])
    context["records"] = [_build_record(row) for row in records]
    return context


def _render_and_validate(records: list[dict[str, Any]]) -> str:
    """Render the reversal template and validate it against the bundled XSD."""
    tdir = TEMPLATES_DIR / REVERSAL_MESSAGE_TYPE
    template_path = str(tdir / "template.xml")
    xsd_path = str(tdir / f"{REVERSAL_MESSAGE_TYPE}.xsd")

    template = get_template(
        os.path.dirname(template_path), os.path.basename(template_path)
    )
    xml_content = template.render(**_build_context(records))

    if not validate_xml_string_via_xsd(xml_content, xsd_path):
        raise ReversalGenerationError(
            f"Generated reversal XML failed validation against {xsd_path}"
        )
    return xml_content


def generate_reversal_xml(records: list[dict[str, Any]]) -> str:
    """Render reversing-entry records into validated camt.053 XML.

    Args:
        records: One or more flat reversing-entry records (as produced by
            :func:`camt053.reversal.reversal.build_reversal_records`).

    Returns:
        The validated camt.053.001.08 reversal document as a string.

    Raises:
        ReversalGenerationError: If records are empty or the rendered XML does
            not validate against the bundled XSD.
    """
    if not records:
        raise ReversalGenerationError(
            "No reversing-entry records to render - records list is empty"
        )
    return _render_and_validate(records)


def generate_reversal_for_statement(
    statement: Statement,
    reason_code: str | None = None,
    msg_id: str | None = None,
    creation_date_time: str | None = None,
) -> str:
    """Build and render a reversing-entry statement for a parsed statement.

    Convenience that chains
    :func:`camt053.reversal.reversal.build_reversal_records` and
    :func:`generate_reversal_xml`.

    Args:
        statement: The parsed statement whose entries are reversed.
        reason_code: If given, only entries with this return reason are
            reversed; otherwise every returnable entry is.
        msg_id: Optional reversal group-header message id.
        creation_date_time: Optional ISO 8601 timestamp for the reversal.

    Returns:
        The validated camt.053.001.08 reversal document as a string.

    Raises:
        ReversalGenerationError: If no entry matches or validation fails.
    """
    records = build_reversal_records(
        statement,
        reason_code=reason_code,
        msg_id=msg_id,
        creation_date_time=creation_date_time,
    )
    return generate_reversal_xml(records)


def write_reversal_xml(
    records: list[dict[str, Any]], xml_file_path: str
) -> str:
    """Generate a reversal document and write it to ``xml_file_path``.

    Args:
        records: One or more flat reversing-entry records.
        xml_file_path: Destination path (must be within the working directory).

    Returns:
        The validated path the reversal document was written to.

    Raises:
        ValueError: If the output path escapes the working directory.
        ReversalGenerationError: If generation or validation fails.
    """
    xml_content = generate_reversal_xml(records)
    try:
        safe_xml_path = validate_path(xml_file_path)
    except Exception as e:
        raise ValueError(f"Path validation failed: {e}") from e

    cwd_prefix = str(os.path.realpath(os.getcwd()))
    if not safe_xml_path.startswith(cwd_prefix + os.sep):
        raise ValueError(
            f"Output path outside working directory: {safe_xml_path}"
        )

    with open(safe_xml_path, "w", encoding="utf-8") as xml_file:
        xml_file.write(xml_content)
    return safe_xml_path
