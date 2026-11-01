# AGENT-ENTITY evolution projection (prototype)
Pure Python standard-library read-only proof projection. Run `python -m unittest discover -s tests -p 'test_evolution.py'` from repo root.

No production authority, score calibration, credential promotion or runtime integration is implemented. Only verified independent evidence is counted, duplicates rejected and revocations reported. External signature/issuer verification, cryptographic receipt validation, policy registry, appeals adjudication and storage are **not** implemented; caller-supplied verification_status is untrusted until a trusted verifier is integrated. Do not deploy as an authorization control.

Next: connect verified Proof Graph receipts, define versioned schemas and build domain-specific evidence metrics and human-reviewed certification.
