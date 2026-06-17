"""Shared constants and configuration for the camt053 library."""

import os
from pathlib import Path

BASE_DIR = Path(os.path.dirname(os.path.abspath(__file__))).resolve()

VERSION = "0.0.1"
SCHEMAS_DIR = BASE_DIR / "schemas"
TEMPLATES_DIR = BASE_DIR / "templates"

# Cash-management messages this library can read (parse) and, for the
# statement message, write (the reversing entry is emitted as a camt.053).
# Versions track the ISO 20022 2025/2026 maintenance release (variant .001.14).
valid_xml_types = [
    "camt.052.001.14",
    "camt.053.001.14",
    "camt.054.001.14",
]

# The single message type the library *generates* (the reversing entry).
REVERSAL_MESSAGE_TYPE = "camt.053.001.14"

# Human-readable name for every supported ISO 20022 cash-management message.
message_names = {
    "camt.052.001.14": "Bank To Customer Account Report",
    "camt.053.001.14": "Bank To Customer Statement",
    "camt.054.001.14": "Bank To Customer Debit Credit Notification",
}

# Local (namespace-stripped) name of the document-level container element for
# each supported message, used by the namespace-agnostic statement parser.
STATEMENT_CONTAINERS = {
    "camt.052.001.14": "BkToCstmrAcctRpt",
    "camt.053.001.14": "BkToCstmrStmt",
    "camt.054.001.14": "BkToCstmrDbtCdtNtfctn",
}

# The repeated report/statement/notification element inside each container.
STATEMENT_ELEMENTS = ("Stmt", "Rpt", "Ntfctn")

# ISO 20022 external return reason codes most relevant to reversing entries.
# AC04 (ClosedAccount) is the headline case: a credit transfer booked against
# an account that has since been closed must be returned to the debtor.
return_reason_names = {
    "AC01": "Incorrect Account Number",
    "AC04": "Closed Account Number",
    "AC06": "Blocked Account",
    "AG01": "Transaction Forbidden",
    "AM04": "Insufficient Funds",
    "MD07": "End Customer Deceased",
    "RR01": "Missing Debtor Account Or Identification",
    "RR04": "Regulatory Reason",
}

# Credit/debit indicator values and their reversal.
CREDIT = "CRDT"
DEBIT = "DBIT"
_REVERSED = {CREDIT: DEBIT, DEBIT: CREDIT}


def reverse_credit_debit(indicator: str) -> str:
    """Return the opposite credit/debit indicator (``CRDT`` <-> ``DBIT``)."""
    return _REVERSED.get((indicator or "").upper(), DEBIT)


APP_NAME = "Camt053"
APP_DESCRIPTION = """
A powerful Python library that reads ISO 20022 camt
Bank-to-Customer Statements (camt.053) and Reports
(camt.052 / camt.054), extracts booked entries by
return reason code (e.g. AC04 Closed Account), and
generates validated reversing entries.\n
https://camt053.com
"""

__all__ = [
    "APP_DESCRIPTION",
    "APP_NAME",
    "BASE_DIR",
    "CREDIT",
    "DEBIT",
    "REVERSAL_MESSAGE_TYPE",
    "SCHEMAS_DIR",
    "STATEMENT_CONTAINERS",
    "STATEMENT_ELEMENTS",
    "TEMPLATES_DIR",
    "VERSION",
    "message_names",
    "return_reason_names",
    "reverse_credit_debit",
    "valid_xml_types",
]
