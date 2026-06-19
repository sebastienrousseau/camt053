"""XML generator for ISO 20022 reversing-entry / payment-return documents.

The headline output is a camt.053 reversing-entry statement, which can be
emitted in any bundled camt.053 schema version (see
:data:`camt053.constants.REVERSAL_CAMT_VERSIONS`). As an alternative, the same
reversing-entry records can be rendered as a pacs.004 PaymentReturn document
(the canonical ISO "payment return" message), selected via ``output_format``.
"""

import os
from typing import Any

from jinja2 import Environment, FileSystemLoader

from camt053.constants import (
    OUTPUT_FORMAT_CAMT053,
    OUTPUT_FORMAT_PACS004,
    OUTPUT_FORMATS,
    PACS_RETURN_MESSAGE_TYPE,
    REVERSAL_CAMT_VERSIONS,
    REVERSAL_MESSAGE_TYPE,
    TEMPLATES_DIR,
)
from camt053.exceptions import ReversalGenerationError
from camt053.models import Statement
from camt053.reversal.reversal import build_reversal_records
from camt053.security import validate_path
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


def _resolve_message_type(output_format: str, version: str | None) -> str:
    """Resolve the output format + version to a bundled message type.

    Args:
        output_format: One of :data:`camt053.constants.OUTPUT_FORMATS`.
        version: For the camt.053 format, the schema version to emit (one of
            :data:`camt053.constants.REVERSAL_CAMT_VERSIONS`); ``None`` selects
            the default :data:`camt053.constants.REVERSAL_MESSAGE_TYPE`. Ignored
            for the pacs.004 format.

    Returns:
        The bundled message type whose template directory should be rendered.

    Raises:
        ReversalGenerationError: If the format or version is unknown.
    """
    fmt = (output_format or "").lower()
    if fmt == OUTPUT_FORMAT_PACS004:
        return PACS_RETURN_MESSAGE_TYPE
    if fmt != OUTPUT_FORMAT_CAMT053:
        supported = ", ".join(OUTPUT_FORMATS)
        raise ReversalGenerationError(
            f"Unknown output format {output_format!r}; "
            f"expected one of: {supported}."
        )
    if version is None:
        return REVERSAL_MESSAGE_TYPE
    if version not in REVERSAL_CAMT_VERSIONS:
        supported = ", ".join(REVERSAL_CAMT_VERSIONS)
        raise ReversalGenerationError(
            f"Unknown camt.053 output version {version!r}; "
            f"expected one of: {supported}."
        )
    return version


def _render_and_validate(
    records: list[dict[str, Any]], message_type: str
) -> str:
    """Render a reversal template and validate it against its bundled XSD."""
    tdir = TEMPLATES_DIR / message_type
    template_path = str(tdir / "template.xml")
    xsd_path = str(tdir / f"{message_type}.xsd")

    env = Environment(
        loader=FileSystemLoader(os.path.dirname(template_path)),
        autoescape=True,
    )
    template = env.get_template(os.path.basename(template_path))
    xml_content = template.render(**_build_context(records))

    if not validate_xml_string_via_xsd(xml_content, xsd_path):
        raise ReversalGenerationError(
            f"Generated reversal XML failed validation against {xsd_path}"
        )
    return xml_content


def generate_reversal_xml(
    records: list[dict[str, Any]],
    output_format: str = OUTPUT_FORMAT_CAMT053,
    version: str | None = None,
) -> str:
    """Render reversing-entry records into a validated reversal document.

    Args:
        records: One or more flat reversing-entry records (as produced by
            :func:`camt053.reversal.reversal.build_reversal_records`).
        output_format: ``"camt053"`` (default) emits a camt.053 reversing-entry
            statement; ``"pacs004"`` emits a pacs.004 PaymentReturn document.
        version: For the camt.053 format, the schema version to emit (one of
            :data:`camt053.constants.REVERSAL_CAMT_VERSIONS`); ``None`` keeps
            the default :data:`camt053.constants.REVERSAL_MESSAGE_TYPE`. Ignored
            for the pacs.004 format.

    Returns:
        The validated reversal document as a string.

    Raises:
        ReversalGenerationError: If records are empty, the format / version is
            unknown, or the rendered XML does not validate against its XSD.
    """
    if not records:
        raise ReversalGenerationError(
            "No reversing-entry records to render - records list is empty"
        )
    message_type = _resolve_message_type(output_format, version)
    return _render_and_validate(records, message_type)


def generate_reversal_for_statement(
    statement: Statement,
    reason_code: str | None = None,
    msg_id: str | None = None,
    creation_date_time: str | None = None,
    output_format: str = OUTPUT_FORMAT_CAMT053,
    version: str | None = None,
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
        output_format: ``"camt053"`` (default) or ``"pacs004"``.
        version: Optional camt.053 schema version to emit (default keeps
            :data:`camt053.constants.REVERSAL_MESSAGE_TYPE`).

    Returns:
        The validated reversal document as a string.

    Raises:
        ReversalGenerationError: If no entry matches or validation fails.
    """
    records = build_reversal_records(
        statement,
        reason_code=reason_code,
        msg_id=msg_id,
        creation_date_time=creation_date_time,
    )
    return generate_reversal_xml(
        records, output_format=output_format, version=version
    )


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
