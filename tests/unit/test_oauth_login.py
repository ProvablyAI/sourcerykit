"""Tests for sourcerykit.provably.oauth_login."""

import base64
import hashlib

from sourcerykit.provably.oauth_login import pkce_pair


def test_pkce_pair_s256_verifiable() -> None:
    verifier, challenge = pkce_pair()
    assert verifier and challenge
    expected = base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).rstrip(b"=").decode()
    assert challenge == expected
