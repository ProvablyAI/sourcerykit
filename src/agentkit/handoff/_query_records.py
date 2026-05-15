from agentkit.db import select_intercept_by_id, select_intercepts_by_action
from agentkit.handoff._bootstrap import _BOOTSTRAP
from agentkit.logger import get_logger
from agentkit.provably import service

_log = get_logger(__name__)


async def create_query_record_for_intercept(
    action_name: str,
    agent_id: str,
    row_id: int | None = None,
) -> str:
    if not action_name or not agent_id:
        raise ValueError("create_query_record_for_intercept requires non-empty agent_id and action_name")

    if row_id is not None:
        query = select_intercept_by_id(row_id)
    else:
        query = select_intercepts_by_action(action_name)

    if _BOOTSTRAP.middleware_id is not None and _BOOTSTRAP.collection_id is not None:
        query_id = await service.run_query(_BOOTSTRAP.middleware_id, _BOOTSTRAP.collection_id, query)
        await service.wait_for_proof_computation(query_id)
        query_url = service.query_record_url(query_id)
        return query_url
    else:
        raise
