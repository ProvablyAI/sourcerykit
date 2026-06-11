"""Tests for sourcerykit.db helpers — ConnectionInfo, _intercepts, _trusted_endpoints."""

import uuid

from sourcerykit.db._engine import ConnectionInfo

# ---------------------------------------------------------------------------
# ConnectionInfo
# ---------------------------------------------------------------------------


class TestConnectionInfo:
    def test_to_dict_returns_all_fields(self) -> None:
        ci = ConnectionInfo(
            name="mydb",
            username="user",
            password="secret",
            provider="postgresql",
            uri="postgresql://user:secret@localhost:5432/mydb",
        )
        d = ci.to_dict()
        assert d["name"] == "mydb"
        assert d["username"] == "user"
        assert d["password"] == "secret"
        assert d["provider"] == "postgresql"
        assert d["uri"] == "postgresql://user:secret@localhost:5432/mydb"

    def test_to_dict_keys(self) -> None:
        ci = ConnectionInfo(name="n", username="u", password="p", provider="prov", uri="u://x")
        assert set(ci.to_dict().keys()) == {"name", "username", "password", "provider", "uri"}


# ---------------------------------------------------------------------------
# DB intercept SQL builders
# ---------------------------------------------------------------------------


class TestInsertIntercept:
    def test_returns_insert_statement(self) -> None:
        from sourcerykit.db._intercepts import insert_intercept

        stmt = insert_intercept(
            agent_id="agent-1",
            action_name="fetch",
            source_url="https://api.example.com",
            request_payload={"method": "GET"},
            raw_response={"status": 200},
            response_hash="abc123",
        )
        # Should be a SQLAlchemy Insert object
        from sqlalchemy.sql.dml import Insert

        assert isinstance(stmt, Insert)

    def test_returning_id_clause_present(self) -> None:
        from sourcerykit.db._intercepts import insert_intercept

        stmt = insert_intercept("a", "b", "https://c.com", {}, {}, "hash")
        compiled = str(stmt.compile())
        assert "RETURNING" in compiled.upper() or "returning" in compiled.lower()


class TestSelectInterceptById:
    def test_returns_string_with_id(self) -> None:
        from sourcerykit.db._intercepts import select_intercept_by_id

        row_id = uuid.uuid4()
        sql = select_intercept_by_id(row_id)
        assert isinstance(sql, str)
        assert str(row_id) in sql


class TestSelectInterceptsByAction:
    def test_returns_string_with_action_name(self) -> None:
        from sourcerykit.db._intercepts import select_intercepts_by_action

        sql = select_intercepts_by_action("my_action")
        assert isinstance(sql, str)
        assert "my_action" in sql


class TestSelectInterceptsByAgentIdAndAction:
    def test_returns_select_object(self) -> None:
        from sqlalchemy.sql.selectable import Select

        from sourcerykit.db._intercepts import select_intercepts_by_agent_id_and_action

        stmt = select_intercepts_by_agent_id_and_action("agent-1", "action-a")
        assert isinstance(stmt, Select)


# ---------------------------------------------------------------------------
# DB trusted_endpoint SQL builders
# ---------------------------------------------------------------------------


class TestSelectTrustedEndpointPrefix:
    def test_returns_select_object(self) -> None:
        from sqlalchemy.sql.selectable import Select

        from sourcerykit.db._trusted_endpoints import select_trusted_endpoint_prefix

        org_id = uuid.uuid4()
        stmt = select_trusted_endpoint_prefix(org_id, "https://example.com")
        assert isinstance(stmt, Select)


class TestSelectActiveTrustedEndpoints:
    def test_returns_select_object(self) -> None:
        from sqlalchemy.sql.selectable import Select

        from sourcerykit.db._trusted_endpoints import select_active_trusted_endpoints

        org_id = uuid.uuid4()
        stmt = select_active_trusted_endpoints(org_id)
        assert isinstance(stmt, Select)


class TestInsertTrustedEndpointDb:
    def test_returns_insert_object(self) -> None:
        from sqlalchemy.sql.dml import Insert

        from sourcerykit.db._trusted_endpoints import insert_trusted_endpoint

        org_id = uuid.uuid4()
        stmt = insert_trusted_endpoint(org_id, "https://example.com", "My label")
        assert isinstance(stmt, Insert)

    def test_insert_without_label(self) -> None:
        from sourcerykit.db._trusted_endpoints import insert_trusted_endpoint

        org_id = uuid.uuid4()
        stmt = insert_trusted_endpoint(org_id, "https://example.com")
        assert stmt is not None
