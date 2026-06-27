# Copyright (C) 2023-2026 Sebastien Rousseau.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or
# implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Append-only HMAC hash-chain audit log for camt.05x workflows.

Financial-services consumers of camt053 (banks, clearing-house
adapters, regulated fintechs) commonly need a tamper-evident
processing log: who parsed which statement, when, with which result,
in a sequence that cannot be rewritten without breaking a verifiable
chain. This module provides that primitive at the library level so
every consumer in the suite (CLI, REST API, MCP server, LSP server)
can emit and verify the same shape.

Design choices
--------------
* **HMAC-SHA-256** over the canonical JSON serialisation of
  ``(prev_hash, sequence, timestamp_utc, event_type, payload)``.
  HMAC (rather than a plain digest) so an attacker who tampers with
  the log cannot recompute valid hashes without the secret.
* **Append-only**. The :class:`HashChain` exposes :meth:`append` and
  read-only :attr:`events`. No update / delete is supported on
  individual events; tampering requires editing the stored list
  out-of-band and is what :func:`verify_chain` detects.
* **Stateless verification**. :func:`verify_chain` takes the events
  + secret + an optional starting hash and re-derives every link.
  Verification has no side effects and yields a structured report.
* **Library-level secret is the caller's responsibility.** The chain
  carries no key material; the secret stays with the application.

Out of scope
------------
* Storage: where the events live (file, database, append-only log
  service) is the caller's concern.
* Distribution / signing of release-boundary bundles via sigstore
  is a CI-pipeline concern, tracked separately.
* Timestamping with an external Trusted Timestamping Authority is
  out of scope; the chain uses local UTC time. Add a TSA wrapper
  externally if you need legal-grade timestamps.
"""

from __future__ import annotations

import hashlib
import hmac
import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

__all__ = [
    "GENESIS_HASH",
    "AuditEvent",
    "ChainVerification",
    "HashChain",
    "compute_event_hmac",
    "verify_chain",
]


#: The conventional "previous hash" recorded on the very first event
#: in a chain. Chosen as the empty string rather than e.g. 64 zeroes
#: so the genesis marker is visually distinct from any computed hash.
GENESIS_HASH: str = ""


@dataclass(frozen=True)
class AuditEvent:
    """One immutable event in an :class:`HashChain`.

    Frozen so callers cannot accidentally mutate a stored event and
    silently break the chain; tampering still detected by
    :func:`verify_chain` even when fields are read-only because the
    stored ``hmac`` is checked against a freshly-computed one.

    Attributes:
        sequence: Zero-based index of this event in the chain.
        timestamp_utc: ISO 8601 UTC timestamp with a trailing ``Z``.
        event_type: Application-defined event label (e.g.
            ``"statement.parsed"``, ``"reversal.generated"``).
        payload: JSON-serialisable application payload. Avoid storing
            PII directly; redact in the application layer first.
        prev_hash: The ``hmac`` of the previous event in the chain;
            :data:`GENESIS_HASH` for the first event.
        hmac: The HMAC-SHA-256 of the canonical serialisation of this
            event's
            ``(prev_hash, sequence, timestamp_utc, event_type, payload)``
            tuple under the chain's secret.
    """

    sequence: int
    timestamp_utc: str
    event_type: str
    payload: dict[str, Any]
    prev_hash: str
    hmac: str

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-serialisable representation."""
        return {
            "sequence": self.sequence,
            "timestamp_utc": self.timestamp_utc,
            "event_type": self.event_type,
            "payload": self.payload,
            "prev_hash": self.prev_hash,
            "hmac": self.hmac,
        }


@dataclass(frozen=True)
class ChainVerification:
    """The result of :func:`verify_chain`.

    Attributes:
        valid: ``True`` iff every event's stored ``hmac`` matches the
            HMAC re-derived from its fields under the supplied secret
            **and** every event's ``prev_hash`` matches the prior
            event's stored ``hmac``.
        broken_at: The ``sequence`` index of the first event that
            failed verification, or ``None`` if the chain is intact.
        reason: A short stable code describing the failure, or
            ``None`` if intact. One of ``"HMAC_MISMATCH"``,
            ``"PREV_HASH_MISMATCH"``, ``"SEQUENCE_GAP"``, or
            ``"GENESIS_PREV_HASH"``.
    """

    valid: bool
    broken_at: int | None = None
    reason: str | None = None


def _canonical(
    prev_hash: str,
    sequence: int,
    timestamp_utc: str,
    event_type: str,
    payload: dict[str, Any],
) -> bytes:
    """Return the canonical bytes signed by the HMAC.

    Uses :func:`json.dumps` with sorted keys and no insignificant
    whitespace so the serialisation is byte-stable across Python
    versions and platforms. UTF-8 encoded.
    """
    return json.dumps(
        {
            "prev_hash": prev_hash,
            "sequence": sequence,
            "timestamp_utc": timestamp_utc,
            "event_type": event_type,
            "payload": payload,
        },
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")


def compute_event_hmac(
    secret: bytes,
    *,
    prev_hash: str,
    sequence: int,
    timestamp_utc: str,
    event_type: str,
    payload: dict[str, Any],
) -> str:
    """Compute the HMAC-SHA-256 for an audit event under ``secret``.

    Exposed publicly so consumers can re-derive an event's expected
    HMAC offline (e.g. during external verification) without having
    to instantiate a :class:`HashChain`.

    Args:
        secret: The chain's HMAC secret. Must match what the producer
            used; mismatches yield ``HMAC_MISMATCH`` on verification.
        prev_hash: The previous event's ``hmac``, or
            :data:`GENESIS_HASH` for the first event.
        sequence: Zero-based index of this event in the chain.
        timestamp_utc: ISO 8601 UTC with trailing ``Z``.
        event_type: Application-defined event label.
        payload: JSON-serialisable application payload.

    Returns:
        The HMAC-SHA-256 as a 64-character lowercase hex string.
    """
    msg = _canonical(prev_hash, sequence, timestamp_utc, event_type, payload)
    return hmac.new(secret, msg, hashlib.sha256).hexdigest()


def _utc_now_iso() -> str:
    """Return the current UTC instant as ``YYYY-MM-DDTHH:MM:SS.uuuuuuZ``.

    Microsecond precision so two events appended in quick succession
    are unlikely to share a timestamp; the chain does not rely on
    timestamps for ordering (``sequence`` does) but rapid collisions
    look suspicious to human readers.
    """
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%fZ")


@dataclass
class HashChain:
    """An append-only HMAC hash-chain audit log.

    Construct with a secret, then call :meth:`append` for each event.
    The chain stores every appended event in :attr:`events`; iterate
    or serialise it however suits your storage.

    The chain is **in-memory only**; persistence is the caller's
    responsibility (write each appended event to your file / DB / log
    service). To reconstruct a chain from storage, build the
    :class:`AuditEvent` instances directly and pass them to
    :func:`verify_chain` rather than re-instantiating ``HashChain``.
    """

    secret: bytes
    events: list[AuditEvent] = field(default_factory=list)

    def append(
        self,
        event_type: str,
        payload: dict[str, Any] | None = None,
        *,
        timestamp_utc: str | None = None,
    ) -> AuditEvent:
        """Append a new event to the chain and return it.

        Args:
            event_type: Application-defined event label.
            payload: JSON-serialisable application payload, or ``None``
                for events that carry no extra data (an empty dict is
                stored).
            timestamp_utc: Optional explicit timestamp (mainly for
                reproducible tests); defaults to the current UTC
                instant in microsecond ISO 8601 form.

        Returns:
            The freshly appended :class:`AuditEvent`.
        """
        prev_hash = self.events[-1].hmac if self.events else GENESIS_HASH
        sequence = len(self.events)
        ts = timestamp_utc or _utc_now_iso()
        payload_dict = dict(payload) if payload else {}
        event_hmac = compute_event_hmac(
            self.secret,
            prev_hash=prev_hash,
            sequence=sequence,
            timestamp_utc=ts,
            event_type=event_type,
            payload=payload_dict,
        )
        event = AuditEvent(
            sequence=sequence,
            timestamp_utc=ts,
            event_type=event_type,
            payload=payload_dict,
            prev_hash=prev_hash,
            hmac=event_hmac,
        )
        self.events.append(event)
        return event


def verify_chain(
    events: list[AuditEvent],
    secret: bytes,
    *,
    starting_prev_hash: str = GENESIS_HASH,
) -> ChainVerification:
    """Verify that an :class:`AuditEvent` list is an intact hash-chain.

    Walks the events in order and checks two invariants per event:

    1. **HMAC integrity**: the event's stored ``hmac`` matches the
       HMAC re-derived from its other fields under ``secret``.
    2. **Chain linkage**: the event's ``prev_hash`` equals the
       previous event's ``hmac`` (or ``starting_prev_hash`` for the
       first event in the list).

    The sequence indices are also checked: events must be
    consecutively numbered starting from zero (or from
    ``len(events) - len(events)`` if the caller is verifying a
    sub-segment, which is supported via ``starting_prev_hash``).

    Args:
        events: The chain to verify, in order.
        secret: The HMAC secret used by the producer.
        starting_prev_hash: The ``prev_hash`` the first event must
            carry. Defaults to :data:`GENESIS_HASH`; pass the last
            ``hmac`` of an earlier segment to verify a continuation.

    Returns:
        A :class:`ChainVerification` carrying the verdict.
    """
    expected_prev = starting_prev_hash
    expected_sequence = events[0].sequence if events else 0
    for event in events:
        if event.sequence != expected_sequence:
            return ChainVerification(
                valid=False,
                broken_at=event.sequence,
                reason="SEQUENCE_GAP",
            )
        if event.prev_hash != expected_prev:
            return ChainVerification(
                valid=False,
                broken_at=event.sequence,
                reason=(
                    "GENESIS_PREV_HASH"
                    if expected_prev == starting_prev_hash
                    and starting_prev_hash == GENESIS_HASH
                    and event.sequence == 0
                    else "PREV_HASH_MISMATCH"
                ),
            )
        recomputed = compute_event_hmac(
            secret,
            prev_hash=event.prev_hash,
            sequence=event.sequence,
            timestamp_utc=event.timestamp_utc,
            event_type=event.event_type,
            payload=event.payload,
        )
        if not hmac.compare_digest(recomputed, event.hmac):
            return ChainVerification(
                valid=False,
                broken_at=event.sequence,
                reason="HMAC_MISMATCH",
            )
        expected_prev = event.hmac
        expected_sequence += 1
    return ChainVerification(valid=True)
