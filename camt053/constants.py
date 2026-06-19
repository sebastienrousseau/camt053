"""Shared constants and configuration for the camt053 library."""

import os
from pathlib import Path

BASE_DIR = Path(os.path.dirname(os.path.abspath(__file__))).resolve()

VERSION = "0.0.4"
SCHEMAS_DIR = BASE_DIR / "schemas"
TEMPLATES_DIR = BASE_DIR / "templates"
XSD_DIR = BASE_DIR / "xsd"

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

# ISO 20022 ExternalReturnReason1Code values, covering the common SEPA and
# CBPR+ return reasons. AC04 (ClosedAccount) is the headline case: a credit
# transfer booked against an account that has since been closed must be
# returned to the debtor. Names follow the official ISO external code set.
return_reason_names = {
    "AC01": "Incorrect Account Number",
    "AC02": "Invalid Debtor Account Number",
    "AC03": "Invalid Creditor Account Number",
    "AC04": "Closed Account Number",
    "AC06": "Blocked Account",
    "AC13": "Invalid Debtor Account Type",
    "AC14": "Invalid Creditor Account Type",
    "AG01": "Transaction Forbidden",
    "AG02": "Invalid Bank Operation Code",
    "AM01": "Zero Amount",
    "AM02": "Not Allowed Amount",
    "AM03": "Not Allowed Currency",
    "AM04": "Insufficient Funds",
    "AM05": "Duplication",
    "AM06": "Too Low Amount",
    "AM07": "Blocked Amount",
    "AM08": "Non Settled Amount",
    "AM09": "Wrong Amount",
    "BE01": "Inconsistent With End Customer",
    "BE05": "Unrecognised Initiating Party",
    "CNOR": "Creditor Bank Is Not Registered",
    "DNOR": "Debtor Bank Is Not Registered",
    "DT01": "Invalid Date",
    "ED01": "Correspondent Bank Not Possible",
    "ED05": "Settlement Failed",
    "FF01": "Invalid File Format",
    "MD01": "No Mandate",
    "MD06": "Refund Request By End Customer",
    "MD07": "End Customer Deceased",
    "MS02": "Not Specified Reason Customer Generated",
    "MS03": "Not Specified Reason Agent Generated",
    "NARR": "Narrative",
    "NOAS": "No Answer From Customer",
    "NOOR": "No Original Transaction Received",
    "RC01": "Bank Identifier Incorrect",
    "RR01": "Missing Debtor Account Or Identification",
    "RR02": "Missing Debtor Name Or Address",
    "RR03": "Missing Creditor Name Or Address",
    "RR04": "Regulatory Reason",
    "SL01": "Specific Service Offered By Debtor Agent",
    "TM01": "Cut Off Time",
}

# Handling actions a return reason can be classified into. ``return`` sends the
# funds back to the originator (the headline reversal flow), ``retry`` re-tries
# the transaction (transient conditions such as insufficient funds), and
# ``ignore`` records the reason without acting on it.
REASON_ACTIONS = ("return", "retry", "ignore")

# The action used for any reason code not named in ``_REASON_ACTION_POLICY``.
DEFAULT_REASON_ACTION = "return"

# Built-in mapping of ISO external return reason codes to a handling action.
# Account-level rejections (closed / blocked / invalid account) are returned;
# transient conditions (insufficient funds, duplicates, cut-off) are retried;
# purely informational reasons are ignored. Codes not listed fall back to
# ``DEFAULT_REASON_ACTION``.
_REASON_ACTION_POLICY = {
    "AC01": "return",
    "AC02": "return",
    "AC03": "return",
    "AC04": "return",
    "AC06": "return",
    "AC13": "return",
    "AC14": "return",
    "AG01": "return",
    "AM04": "retry",
    "AM05": "retry",
    "AM07": "retry",
    "ED05": "retry",
    "TM01": "retry",
    "NARR": "ignore",
    "MS02": "ignore",
    "MS03": "ignore",
}


def reason_action_policy() -> dict[str, str]:
    """Return a copy of the built-in reason-code action policy."""
    return dict(_REASON_ACTION_POLICY)


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
    "DEFAULT_REASON_ACTION",
    "REASON_ACTIONS",
    "REVERSAL_MESSAGE_TYPE",
    "SCHEMAS_DIR",
    "STATEMENT_CONTAINERS",
    "STATEMENT_ELEMENTS",
    "TEMPLATES_DIR",
    "VERSION",
    "XSD_DIR",
    "message_names",
    "reason_action_policy",
    "return_reason_names",
    "reverse_credit_debit",
    "valid_xml_types",
]
