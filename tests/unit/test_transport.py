from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from provably.handoff.transport import default_cluster_b_url, post_handoff
from provably.handoff.types import HandoffPayload


def test_default_cluster_b_url_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CLUSTER_B_URL", "http://custom:9999/")
    assert default_cluster_b_url() == "http://custom:9999"


def test_default_cluster_b_url_fallback(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("CLUSTER_B_URL", raising=False)
    assert default_cluster_b_url() == "http://localhost:8082"


def test_post_handoff_empty_url_raises() -> None:
    with pytest.raises(ValueError, match="empty"):
        post_handoff("", HandoffPayload())


@patch("provably.handoff.transport.httpx.post")
def test_post_handoff_posts_json(mock_post: MagicMock) -> None:
    mock_post.return_value.raise_for_status = MagicMock()
    hp = HandoffPayload(task="t")
    post_handoff("http://b.test", hp)
    mock_post.assert_called_once()
    args, kwargs = mock_post.call_args
    assert args[0] == "http://b.test/handoffs/receive"
    assert kwargs["json"]["task"] == "t"
