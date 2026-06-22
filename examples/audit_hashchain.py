#!/usr/bin/env python3
"""Example: HMAC-SHA-256 hash-chain audit log (v0.0.6).

Usage:
    pip install camt053     # requires Python 3.10+
    python examples/audit_hashchain.py

Shows the tamper-evident append-only audit primitives: build a chain
of events, verify it offline, then demonstrate that a single-byte
modification breaks the chain.
"""

from camt053.audit import (
    AuditEvent,
    HashChain,
    verify_chain,
)


def main() -> None:
    secret = b"secret-shared-with-the-auditor"

    chain = HashChain(secret=secret)
    chain.append("statement.parsed", {"msg_id": "STMT-001"})
    chain.append("reversal.generated", {"reason": "AC04"})
    chain.append("reversal.emitted", {"size_bytes": 1637})

    events = chain.events
    print(f"chain has {len(events)} events")
    print(f"first event hmac : {events[0].hmac[:16]}...")
    print(f"last event hmac  : {events[-1].hmac[:16]}...")

    verification = verify_chain(events, secret=secret)
    print(f"\nverify (good)    : valid={verification.valid}")

    # Tamper: change one event's payload after the fact, keep its hmac.
    tampered = events.copy()
    tampered[1] = AuditEvent(
        sequence=events[1].sequence,
        timestamp_utc=events[1].timestamp_utc,
        event_type=events[1].event_type,
        payload={"reason": "AC06"},  # changed from AC04
        prev_hash=events[1].prev_hash,
        hmac=events[1].hmac,  # stale hmac
    )
    bad = verify_chain(tampered, secret=secret)
    print(f"verify (tampered): valid={bad.valid}")


if __name__ == "__main__":
    main()
