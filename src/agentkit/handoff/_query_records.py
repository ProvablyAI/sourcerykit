from uuid import UUID

from agentkit.bootstrap.bootstrap import get_bootstrap
from agentkit.db._intercepts import select_intercept_by_id, select_intercepts_by_action
from agentkit.errors import AgentKitBootstrapError
from agentkit.logger import get_logger
from agentkit.provably.service import service
from agentkit.utils.validation import validate_length

_log = get_logger(__name__)


async def create_query_record_for_intercept(
    action_name: str,
    agent_id: str,
    row_id: UUID | None = None,
) -> tuple[UUID, str]:
    _log.info("query_record_started", action_name=action_name, agent_id=agent_id)
    if not action_name or not agent_id:
        raise ValueError("create_query_record_for_intercept requires non-empty agent_id and action_name")

    # Enforce DB length limits to avoid insert/query failures
    validate_length("agent_id", agent_id, max_len=255)
    validate_length("action_name", action_name, max_len=255)

    if row_id is not None:
        query = select_intercept_by_id(row_id)
    else:
        query = select_intercepts_by_action(action_name)

    provably = get_bootstrap()

    middleware_id = provably.middleware_id
    collection_id = provably.collection_id

    if middleware_id is not None and collection_id is not None:
        query_id = await service.run_query(middleware_id, collection_id, query)
        await service.wait_for_proof_computation(query_id)
        query_url = service.query_record_url(query_id)
        return query_id, query_url
    else:
        _log.error("query_record_failed_incomplete_bootstrap", action_name=action_name)
        raise AgentKitBootstrapError("Provably bootstrap incomplete: middleware_id and collection_id are required")
