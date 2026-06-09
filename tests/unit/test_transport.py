from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from agentkit.handoff.transport import post_handoff
from agentkit.handoff.types import HandoffPayload


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
