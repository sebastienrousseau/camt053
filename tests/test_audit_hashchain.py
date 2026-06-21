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

"""Tests for B6: HMAC hash-chain audit log."""

from __future__ import annotations

import dataclasses
from typing import Any

import pytest

from camt053 import services
from camt053.audit import (
    GENESIS_HASH,
    AuditEvent,
    HashChain,
    compute_event_hmac,
    verify_chain,
)

_SECRET = b"test-secret-key"


def _new_chain() -> HashChain:
    """Helper: build a fresh chain with the default test secret."""
    return HashChain(secret=_SECRET)


# ─── HashChain.append ───────────────────────────────────────────────────────


def test_empty_chain_has_no_events() -> None:
    """A freshly-constructed chain carries no events."""
    chain = _new_chain()
    assert chain.events == []


def test_first_append_sets_genesis_prev_hash() -> None:
    """The first event records GENESIS_HASH as its prev_hash."""
    chain = _new_chain()
    event = chain.append("statement.parsed", {"msg_id": "M-1"})
    assert event.prev_hash == GENESIS_HASH
    assert event.sequence == 0


def test_second_append_links_to_first() -> None:
    """The second event's prev_hash equals the first event's hmac."""
    chain = _new_chain()
    first = chain.append("statement.parsed", {"msg_id": "M-1"})
    second = chain.append("reversal.generated", {"reason": "AC04"})
    assert second.prev_hash == first.hmac
    assert second.sequence == 1


def test_append_default_payload_is_empty_dict() -> None:
    """Omitting payload stores an empty dict, not None."""
    chain = _new_chain()
    event = chain.append("noop")
    assert event.payload == {}


def test_append_preserves_payload_immutability() -> None:
    """Mutating the original payload dict after append doesn't affect the event."""
    chain = _new_chain()
    payload: dict[str, Any] = {"a": 1}
    event = chain.append("e", payload)
    payload["b"] = 2  # external mutation
    assert event.payload == {"a": 1}


def test_append_returns_event_added_to_events() -> None:
    """The returned event is the same object stored in chain.events."""
    chain = _new_chain()
    event = chain.append("e")
    assert chain.events[-1] is event


def test_explicit_timestamp_round_trips() -> None:
    """A caller-supplied timestamp is preserved on the event."""
    chain = _new_chain()
    ts = "2026-06-21T12:00:00.000000Z"
    event = chain.append("e", timestamp_utc=ts)
    assert event.timestamp_utc == ts


def test_default_timestamp_is_iso_utc_with_z_suffix() -> None:
    """The auto-generated timestamp is ISO 8601 UTC with a trailing Z."""
    chain = _new_chain()
    event = chain.append("e")
    assert event.timestamp_utc.endswith("Z")
    # YYYY-MM-DDTHH:MM:SS.uuuuuuZ → 27 chars
    assert len(event.timestamp_utc) == 27


def test_audit_event_is_frozen() -> None:
    """AuditEvent is immutable; attribute assignment raises."""
    chain = _new_chain()
    event = chain.append("e")
    with pytest.raises(dataclasses.FrozenInstanceError):
        event.event_type = "tampered"  # type: ignore[misc]


def test_audit_event_to_dict_carries_canonical_keys() -> None:
    """to_dict round-trips every public field."""
    chain = _new_chain()
    event = chain.append("statement.parsed", {"msg_id": "M-1"})
    payload = event.to_dict()
    assert set(payload.keys()) == {
        "sequence",
        "timestamp_utc",
        "event_type",
        "payload",
        "prev_hash",
        "hmac",
    }


# ─── compute_event_hmac ─────────────────────────────────────────────────────


def test_compute_event_hmac_is_deterministic() -> None:
    """Same inputs → same HMAC, always."""
    args: dict[str, Any] = {
        "prev_hash": GENESIS_HASH,
        "sequence": 0,
        "timestamp_utc": "2026-06-21T12:00:00.000000Z",
        "event_type": "e",
        "payload": {"a": 1},
    }
    first = compute_event_hmac(_SECRET, **args)
    second = compute_event_hmac(_SECRET, **args)
    assert first == second


def test_compute_event_hmac_changes_on_payload_change() -> None:
    """Different payload → different HMAC."""
    args: dict[str, Any] = {
        "prev_hash": GENESIS_HASH,
        "sequence": 0,
        "timestamp_utc": "2026-06-21T12:00:00.000000Z",
        "event_type": "e",
    }
    h1 = compute_event_hmac(_SECRET, **args, payload={"a": 1})
    h2 = compute_event_hmac(_SECRET, **args, payload={"a": 2})
    assert h1 != h2


def test_compute_event_hmac_changes_on_secret_change() -> None:
    """Different secret → different HMAC."""
    args: dict[str, Any] = {
        "prev_hash": GENESIS_HASH,
        "sequence": 0,
        "timestamp_utc": "2026-06-21T12:00:00.000000Z",
        "event_type": "e",
        "payload": {},
    }
    h_a = compute_event_hmac(b"secret-A", **args)
    h_b = compute_event_hmac(b"secret-B", **args)
    assert h_a != h_b


def test_compute_event_hmac_is_64_lowercase_hex() -> None:
    """SHA-256 hex digest is exactly 64 lowercase hex chars."""
    h = compute_event_hmac(
        _SECRET,
        prev_hash=GENESIS_HASH,
        sequence=0,
        timestamp_utc="2026-06-21T12:00:00.000000Z",
        event_type="e",
        payload={},
    )
    assert len(h) == 64
    assert all(c in "0123456789abcdef" for c in h)


# ─── verify_chain ───────────────────────────────────────────────────────────


def test_verify_empty_chain_is_valid() -> None:
    """An empty event list verifies as valid (no links to break)."""
    result = verify_chain([], _SECRET)
    assert result.valid is True
    assert result.broken_at is None
    assert result.reason is None


def test_verify_single_event_chain_is_valid() -> None:
    """A one-event chain verifies."""
    chain = _new_chain()
    chain.append("statement.parsed", {"msg_id": "M-1"})
    result = verify_chain(chain.events, _SECRET)
    assert result.valid is True


def test_verify_multi_event_chain_is_valid() -> None:
    """A multi-event chain verifies end-to-end."""
    chain = _new_chain()
    for i in range(5):
        chain.append(f"event-{i}", {"i": i})
    result = verify_chain(chain.events, _SECRET)
    assert result.valid is True


def test_tampered_payload_breaks_chain_with_hmac_mismatch() -> None:
    """Replacing an event's payload via reconstruction breaks the HMAC link."""
    chain = _new_chain()
    chain.append("e0", {"a": 0})
    second = chain.append("e1", {"a": 1})
    chain.append("e2", {"a": 2})
    # Reconstruct event #1 with a different payload but the same hmac
    tampered = AuditEvent(
        sequence=second.sequence,
        timestamp_utc=second.timestamp_utc,
        event_type=second.event_type,
        payload={"a": 999},  # tampered
        prev_hash=second.prev_hash,
        hmac=second.hmac,  # stale
    )
    events = [chain.events[0], tampered, chain.events[2]]
    result = verify_chain(events, _SECRET)
    assert result.valid is False
    assert result.broken_at == 1
    assert result.reason == "HMAC_MISMATCH"


def test_tampered_hmac_breaks_chain() -> None:
    """Editing only the hmac (keeping fields) trips HMAC_MISMATCH."""
    chain = _new_chain()
    chain.append("e0")
    second = chain.append("e1")
    chain.append("e2")
    tampered = AuditEvent(
        sequence=second.sequence,
        timestamp_utc=second.timestamp_utc,
        event_type=second.event_type,
        payload=second.payload,
        prev_hash=second.prev_hash,
        hmac="0" * 64,  # tampered hmac
    )
    events = [chain.events[0], tampered, chain.events[2]]
    result = verify_chain(events, _SECRET)
    assert result.valid is False
    assert result.broken_at == 1
    assert result.reason == "HMAC_MISMATCH"


def test_deleted_event_breaks_chain_with_prev_hash_mismatch() -> None:
    """Dropping a middle event breaks the prev_hash link of the next event."""
    chain = _new_chain()
    chain.append("e0")
    chain.append("e1")
    chain.append("e2")
    # Skip event 1; event 2's prev_hash references event 1's hmac
    events = [chain.events[0], chain.events[2]]
    result = verify_chain(events, _SECRET)
    assert result.valid is False
    # The next event after the deleted one is the first to fail
    assert result.broken_at == 2
    assert result.reason == "SEQUENCE_GAP"


def test_wrong_secret_breaks_every_event() -> None:
    """Verifying with the wrong secret fails at the first event."""
    chain = _new_chain()
    chain.append("e0")
    chain.append("e1")
    result = verify_chain(chain.events, b"wrong-secret")
    assert result.valid is False
    assert result.broken_at == 0
    assert result.reason == "HMAC_MISMATCH"


def test_genesis_prev_hash_must_be_genesis_default() -> None:
    """The first event must carry GENESIS_HASH as prev_hash."""
    chain = _new_chain()
    real = chain.append("e0")
    # Reconstruct as if event-0 had a non-genesis prev_hash
    tampered = AuditEvent(
        sequence=0,
        timestamp_utc=real.timestamp_utc,
        event_type=real.event_type,
        payload=real.payload,
        prev_hash="deadbeef" * 8,
        hmac=real.hmac,
    )
    result = verify_chain([tampered], _SECRET)
    assert result.valid is False
    assert result.broken_at == 0
    assert result.reason == "GENESIS_PREV_HASH"


def test_verify_with_starting_prev_hash_supports_continuation() -> None:
    """Pass starting_prev_hash to verify a continuation segment."""
    chain = _new_chain()
    chain.append("e0")
    chain.append("e1")
    chain.append("e2")
    # Verify just events [1, 2] as a continuation of event 0
    tail = chain.events[1:]
    result = verify_chain(
        tail, _SECRET, starting_prev_hash=chain.events[0].hmac
    )
    assert result.valid is True


def test_verify_with_wrong_starting_prev_hash_fails() -> None:
    """A continuation with the wrong anchor fails PREV_HASH_MISMATCH."""
    chain = _new_chain()
    chain.append("e0")
    chain.append("e1")
    tail = chain.events[1:]
    result = verify_chain(tail, _SECRET, starting_prev_hash="abc" * 21 + "a")
    assert result.valid is False
    assert result.broken_at == 1
    assert result.reason == "PREV_HASH_MISMATCH"


# ─── services facade re-exports ─────────────────────────────────────────────


def test_services_hashchain_is_the_same_class() -> None:
    """services.HashChain is the same class as the underlying one."""
    assert services.HashChain is HashChain


def test_services_verify_chain_works_end_to_end() -> None:
    """services.verify_chain is the same function and works."""
    chain = services.HashChain(secret=_SECRET)
    chain.append("e0")
    chain.append("e1")
    result = services.verify_chain(chain.events, _SECRET)
    assert result.valid is True


def test_services_genesis_hash_constant_matches() -> None:
    """The re-exported constant matches the source."""
    assert services.GENESIS_HASH == GENESIS_HASH
