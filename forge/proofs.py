"""Proof envelope validation and signature verification.

A valid, signed proof is evidence. It never grants authority.
"""
from __future__ import annotations

import hashlib
import hmac
import json
from pathlib import Path
from typing import Mapping, Protocol

from jsonschema import Draft202012Validator, FormatChecker

SCHEMA_DIR = Path(__file__).resolve().parent.parent / "schemas"
PROOF_ENVELOPE_SCHEMA = json.loads((SCHEMA_DIR / "proof-envelope.v1.json").read_text())

_VALIDATOR = Draft202012Validator(PROOF_ENVELOPE_SCHEMA, format_checker=FormatChecker())


class ProofValidationError(ValueError):
    pass


class SignatureError(ValueError):
    pass


class Verifier(Protocol):
    def verify(self, canonical_bytes: bytes, signature: str, verifier_ref: str) -> bool: ...


def canonical_json(obj) -> bytes:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def validate_proof_envelope(obj) -> dict:
    errors = sorted(_VALIDATOR.iter_errors(obj), key=lambda e: list(e.path))
    if errors:
        raise ProofValidationError("; ".join(f"{'/'.join(map(str, e.path)) or '<root>'}: {e.message}" for e in errors))
    if obj.get("grants_authority", False) is not False:
        raise ProofValidationError("grants_authority must be false")
    return obj


def is_security_bound(envelope: Mapping) -> bool:
    return bool(envelope.get("security_attestation_ref"))


def verify_signed_proof(envelope: Mapping, signature: str | None, verifier: Verifier) -> dict:
    validate_proof_envelope(envelope)
    if not signature or not isinstance(signature, str):
        raise SignatureError("proof envelope is unsigned")
    if not verifier.verify(canonical_json(envelope), signature, envelope["verifier_ref"]):
        raise SignatureError(f"signature does not verify for verifier_ref {envelope['verifier_ref']!r}")
    return {"envelope": dict(envelope), "signature": signature, "security_bound": is_security_bound(envelope)}


class HmacSha256Verifier:
    """Test/reference verifier. Keys live only inside this object and are never exported."""

    def __init__(self, keys: Mapping[str, bytes]):
        self._keys = dict(keys)

    def sign(self, canonical_bytes: bytes, verifier_ref: str) -> str:
        return hmac.new(self._keys[verifier_ref], canonical_bytes, hashlib.sha256).hexdigest()

    def verify(self, canonical_bytes: bytes, signature: str, verifier_ref: str) -> bool:
        key = self._keys.get(verifier_ref)
        if key is None:
            return False
        return hmac.compare_digest(self.sign(canonical_bytes, verifier_ref), signature)
