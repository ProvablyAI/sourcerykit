"""Tests for sourcerykit.handoff._query_records.create_query_record_for_intercept."""

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from sourcerykit.errors import SourceryKitBootstrapError
from sourcerykit.handoff._query_records import create_query_record_for_intercept

_MW_ID = uuid.uuid4()
_COLL_ID = uuid.uuid4()
_QID = uuid.uuid4()


def _mock_bootstrap(middleware_id: uuid.UUID | None = _MW_ID, collection_id: uuid.UUID | None = _COLL_ID) -> MagicMock:
    b = MagicMock()
    b.middleware_id = middleware_id
    b.collection_id = collection_id
    return b


def _mock_service(query_id: uuid.UUID = _QID) -> MagicMock:
    svc = MagicMock()
    svc.run_query = AsyncMock(return_value=query_id)
    svc.wait_for_proof_computation = AsyncMock(return_value=None)
    svc.query_record_url = MagicMock(return_value=f"https://app.provably.ai/query/{query_id}")
    return svc


class TestCreateQueryRecordForIntercept:
    async def test_returns_query_id_and_url(self) -> None:
        svc = _mock_service()
        with (
            patch("sourcerykit.handoff._query_records.get_bootstrap", return_value=_mock_bootstrap()),
            patch("sourcerykit.handoff._query_records.service", svc),
        ):
            qid, url = await create_query_record_for_intercept("action_a", agent_id="agent-1")
        assert qid == _QID
        assert str(_QID) in url

    async def test_calls_run_query_with_middleware_and_collection(self) -> None:
        svc = _mock_service()
        with (
            patch("sourcerykit.handoff._query_records.get_bootstrap", return_value=_mock_bootstrap()),
            patch("sourcerykit.handoff._query_records.service", svc),
        ):
            await create_query_record_for_intercept("action_a", agent_id="agent-1")
        svc.run_query.assert_called_once_with(_MW_ID, _COLL_ID, svc.run_query.call_args[0][2])

    async def test_calls_wait_for_proof_computation(self) -> None:
        svc = _mock_service()
        with (
            patch("sourcerykit.handoff._query_records.get_bootstrap", return_value=_mock_bootstrap()),
            patch("sourcerykit.handoff._query_records.service", svc),
        ):
            await create_query_record_for_intercept("action_a", agent_id="agent-1")
        svc.wait_for_proof_computation.assert_called_once_with(_QID)

    async def test_uses_call_ref_filter_when_provided(self) -> None:
        svc = _mock_service()
        call_ref = uuid.uuid4()
        with (
            patch("sourcerykit.handoff._query_records.get_bootstrap", return_value=_mock_bootstrap()),
            patch("sourcerykit.handoff._query_records.service", svc),
            patch("sourcerykit.handoff._query_records.select_intercept_by_call_ref") as mock_by_ref,
            patch("sourcerykit.handoff._query_records.select_intercepts_by_action") as mock_by_action,
        ):
            mock_by_ref.return_value = "SELECT * WHERE call_ref = 'x'"
            await create_query_record_for_intercept("action_a", agent_id="agent-1", call_ref=call_ref)
        mock_by_ref.assert_called_once_with(call_ref)
        mock_by_action.assert_not_called()

    async def test_uses_action_name_filter_without_call_ref(self) -> None:
        svc = _mock_service()
        with (
            patch("sourcerykit.handoff._query_records.get_bootstrap", return_value=_mock_bootstrap()),
            patch("sourcerykit.handoff._query_records.service", svc),
            patch("sourcerykit.handoff._query_records.select_intercept_by_call_ref") as mock_by_ref,
            patch("sourcerykit.handoff._query_records.select_intercepts_by_action") as mock_by_action,
        ):
            mock_by_action.return_value = "SELECT * WHERE action_name = 'action_a'"
            await create_query_record_for_intercept("action_a", agent_id="agent-1")
        mock_by_action.assert_called_once_with("action_a")
        mock_by_ref.assert_not_called()

    async def test_raises_bootstrap_error_when_middleware_id_missing(self) -> None:
        svc = _mock_service()
        with (
            patch(
                "sourcerykit.handoff._query_records.get_bootstrap",
                return_value=_mock_bootstrap(middleware_id=None),
            ),
            patch("sourcerykit.handoff._query_records.service", svc),
        ):
            with pytest.raises(SourceryKitBootstrapError):
                await create_query_record_for_intercept("action_a", agent_id="agent-1")

    async def test_raises_bootstrap_error_when_collection_id_missing(self) -> None:
        svc = _mock_service()
        with (
            patch(
                "sourcerykit.handoff._query_records.get_bootstrap",
                return_value=_mock_bootstrap(collection_id=None),
            ),
            patch("sourcerykit.handoff._query_records.service", svc),
        ):
            with pytest.raises(SourceryKitBootstrapError):
                await create_query_record_for_intercept("action_a", agent_id="agent-1")

    async def test_raises_value_error_for_empty_action_name(self) -> None:
        with pytest.raises(ValueError, match="action_name"):
            await create_query_record_for_intercept("", agent_id="agent-1")

    async def test_raises_value_error_for_empty_agent_id(self) -> None:
        with pytest.raises(ValueError, match="agent_id"):
            await create_query_record_for_intercept("action_a", agent_id="")
