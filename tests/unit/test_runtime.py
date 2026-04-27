from __future__ import annotations

from unittest.mock import patch

from provably.runtime import configure_indexing


def test_configure_indexing_on() -> None:
    with (
        patch("provably.runtime.initialize_runtime") as ir,
        patch("provably.runtime.init_interceptor") as ii,
        patch("provably.runtime.enable") as en,
        patch("provably.runtime.disable") as di,
    ):
        configure_indexing(True)
        ir.assert_called_once_with()
        ii.assert_called_once()
        en.assert_called_once()
        di.assert_not_called()


def test_configure_indexing_off() -> None:
    with (
        patch("provably.runtime.initialize_runtime") as ir,
        patch("provably.runtime.init_interceptor") as ii,
        patch("provably.runtime.enable") as en,
        patch("provably.runtime.disable") as di,
    ):
        configure_indexing(False)
        ir.assert_not_called()
        ii.assert_called_once()
        en.assert_not_called()
        di.assert_called_once()
