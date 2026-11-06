import base64
import sys
import threading
from pathlib import Path
from types import SimpleNamespace

import pytest

# The repo-wide CI job doesn't install the server's dependencies; the
# "Asana MCP server" workflow does.
pytest.importorskip("fastmcp")

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import server  # noqa: E402  (puts the asana lib on sys.path)
import asana_sdk  # noqa: E402
from asana_auth import AsanaTokenVerifier  # noqa: E402
from asana_client import AsanaClient  # noqa: E402
from fastmcp import Client  # noqa: E402
from fastmcp.exceptions import ToolError  # noqa: E402

pytestmark = pytest.mark.anyio


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.fixture(autouse=True)
def workspace(monkeypatch):
    monkeypatch.setenv("ASANA_WORKSPACE", "19421316985")


@pytest.fixture
def signed_in(monkeypatch):
    monkeypatch.setattr(server, "get_access_token", lambda: SimpleNamespace(token="tok-dustin"))


@pytest.fixture
def asana_calls(monkeypatch):
    """Record AsanaClient HTTP calls and answer with canned data."""
    calls = []
    responses = {}

    def fake_request(self, method, endpoint, params=None, json_data=None, retries=3):
        calls.append(
            {"method": method, "endpoint": endpoint, "params": params or {}, "json": json_data, "token": self._token}
        )
        for prefix, payload in responses.items():
            if endpoint.startswith(prefix):
                return payload
        return {"data": {}}

    monkeypatch.setattr(AsanaClient, "_request", fake_request)
    return SimpleNamespace(calls=calls, responses=responses)


async def call(tool, args=None):
    async with Client(server.mcp) as client:
        result = await client.call_tool(tool, args or {})
        return result.data


async def test_create_task_converts_markdown_and_runs_as_caller(signed_in, asana_calls):
    asana_calls.responses["tasks"] = {"data": {"gid": "111", "name": "Buy milk"}}

    task = await call("create_task", {"name": "Buy milk", "project_gid": "222", "notes": "## Why\n- **now**"})

    post = asana_calls.calls[0]
    assert post["token"] == "tok-dustin"
    assert post["method"] == "POST" and post["endpoint"] == "tasks"
    body = post["json"]["data"]
    assert "notes" not in body
    assert body["html_notes"].startswith("<body>") and "<strong>now</strong>" in body["html_notes"]
    assert task["url"] == "https://app.asana.com/0/0/111/f"


async def test_create_subtask_uses_parent_and_rich_text(signed_in, asana_calls):
    asana_calls.responses["tasks/999/subtasks"] = {"data": {"gid": "112", "name": "Step"}}

    await call("create_task", {"name": "Step", "parent_gid": "999", "notes": "*soon*"})

    post = asana_calls.calls[0]
    assert post["endpoint"] == "tasks/999/subtasks"
    assert "<em>soon</em>" in post["json"]["data"]["html_notes"]


async def test_plain_notes_are_sent_verbatim(signed_in, asana_calls):
    await call("update_task", {"task_gid": "111", "notes": "a*b*c", "notes_format": "plain"})

    body = asana_calls.calls[0]["json"]["data"]
    assert body == {"notes": "a*b*c"}


async def test_get_task_returns_markdown_description(signed_in, asana_calls):
    asana_calls.responses["tasks/111"] = {
        "data": {"gid": "111", "name": "T", "notes": "plain dup", "html_notes": "<body><strong>hi</strong></body>"}
    }

    task = await call("get_task", {"task_gid": "111"})

    assert task["notes_markdown"].strip() == "**hi**"
    assert "notes" not in task and "html_notes" not in task
    assert task["url"].endswith("/111/f")


async def test_list_tasks_project_and_assignee_uses_search(signed_in, asana_calls):
    asana_calls.responses["workspaces/19421316985/tasks/search"] = {"data": [{"gid": "1", "name": "x"}]}

    tasks = await call("list_tasks", {"project_gid": "222", "assignee": "me"})

    req = asana_calls.calls[0]
    assert req["endpoint"] == "workspaces/19421316985/tasks/search"
    assert req["params"]["projects.any"] == "222"
    assert req["params"]["assignee.any"] == "me"
    assert req["params"]["completed"] == "false"
    assert tasks[0]["url"].endswith("/1/f")


async def test_list_tasks_rejects_section_with_assignee(signed_in, asana_calls):
    with pytest.raises(ToolError, match="section_gid can't be combined"):
        await call("list_tasks", {"section_gid": "5", "assignee": "me"})
    assert asana_calls.calls == []


async def test_find_uses_typeahead(signed_in, asana_calls):
    asana_calls.responses["workspaces/19421316985/typeahead"] = {"data": [{"gid": "81", "name": "Cari Tuna"}]}

    people = await call("find", {"query": "Cari"})

    req = asana_calls.calls[0]
    assert req["params"]["resource_type"] == "user" and req["params"]["query"] == "Cari"
    assert people[0]["gid"] == "81"


async def test_tools_refuse_without_session(monkeypatch, asana_calls):
    monkeypatch.setattr(server, "get_access_token", lambda: None)

    with pytest.raises(ToolError, match="Reconnect the Asana connector"):
        await call("whoami")
    assert asana_calls.calls == []


async def test_sdk_tools_run_with_caller_token(signed_in, monkeypatch):
    seen = {}

    def fake_overdue(project_gid):
        seen["token"] = asana_sdk.get_client().configuration.access_token
        seen["project"] = project_gid
        return [{"gid": "7", "name": "late"}]

    monkeypatch.setattr(asana_sdk, "get_overdue_tasks", fake_overdue)

    tasks = await call("overdue_tasks", {"project_gid": "222"})

    assert seen == {"token": "tok-dustin", "project": "222"}
    assert tasks[0]["url"].endswith("/7/f")


async def test_attach_file_decodes_base64(signed_in, monkeypatch):
    captured = {}

    def fake_upload(task_gid, file_content=None, file_name=None, content_type=None):
        captured.update(task=task_gid, content=file_content, name=file_name)
        return {"gid": "att1"}

    monkeypatch.setattr(asana_sdk, "upload_attachment_to_task", fake_upload)
    payload = base64.b64encode(b"\x89PNG bytes").decode()

    await call("attach_file", {"task_gid": "111", "file_name": "a.png", "content": payload, "encoding": "base64"})

    assert captured == {"task": "111", "content": b"\x89PNG bytes", "name": "a.png"}


def test_sdk_refuses_local_token_fallback():
    assert server.os.environ["ASANA_SDK_REQUIRE_TOKEN_OVERRIDE"] == "1"
    with pytest.raises(asana_sdk.AsanaAuthenticationError, match="refusing to fall back"):
        asana_sdk.get_client()


def test_sdk_token_override_is_isolated_per_thread():
    results = {}
    barrier = threading.Barrier(2)

    def worker(name):
        with asana_sdk.use_access_token(f"tok-{name}"):
            barrier.wait()
            results[name] = asana_sdk.get_client().configuration.access_token

    threads = [threading.Thread(target=worker, args=(n,)) for n in ("dustin", "cari")]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert results == {"dustin": "tok-dustin", "cari": "tok-cari"}


class _FakeResponse:
    def __init__(self, status_code, payload=None):
        self.status_code = status_code
        self._payload = payload
        self.text = str(payload)

    def json(self):
        return self._payload


def _fake_httpx(monkeypatch, response):
    import asana_auth

    class FakeAsyncClient:
        def __init__(self, *a, **kw):
            self.requests = 0

        async def __aenter__(self):
            return self

        async def __aexit__(self, *exc):
            return False

        async def get(self, url, params=None, headers=None):
            FakeAsyncClient.last_headers = headers
            return response

    monkeypatch.setattr(asana_auth.httpx2, "AsyncClient", FakeAsyncClient)
    return FakeAsyncClient


async def test_verifier_accepts_allowlisted_user(monkeypatch):
    fake = _fake_httpx(monkeypatch, _FakeResponse(200, {"data": {"gid": "81", "name": "Cari Tuna", "email": "cari@sutrogroup.org"}}))
    verifier = AsanaTokenVerifier(allowed_user_gids={"1204450987777858", "81"})

    access = await verifier.verify_token("tok-cari")

    assert access.subject == "81" and access.token == "tok-cari"
    assert fake.last_headers["Authorization"] == "Bearer tok-cari"


async def test_verifier_rejects_other_workspace_members(monkeypatch):
    _fake_httpx(monkeypatch, _FakeResponse(200, {"data": {"gid": "1204059442044877", "email": "vendor@example.com"}}))
    verifier = AsanaTokenVerifier(allowed_user_gids={"1204450987777858", "81"})

    assert await verifier.verify_token("tok-vendor") is None


async def test_verifier_returns_none_on_expired_token(monkeypatch):
    _fake_httpx(monkeypatch, _FakeResponse(401, {"errors": [{"message": "expired"}]}))
    verifier = AsanaTokenVerifier(allowed_user_gids={"81"})

    assert await verifier.verify_token("tok-old") is None


def test_verifier_requires_allowlist():
    with pytest.raises(ValueError):
        AsanaTokenVerifier(allowed_user_gids=set())


async def test_subtask_can_be_listed_on_a_project(signed_in, asana_calls):
    await call("create_task", {"name": "Step", "parent_gid": "999", "project_gid": "222"})

    post = asana_calls.calls[0]
    assert post["endpoint"] == "tasks/999/subtasks"
    assert post["json"]["data"]["projects"] == ["222"]


async def test_update_task_can_clear_start_date(signed_in, asana_calls):
    await call("update_task", {"task_gid": "111", "start_on": ""})

    assert asana_calls.calls[0]["json"]["data"] == {"start_on": None}


async def test_remove_task_from_project(signed_in, asana_calls):
    await call("remove_task_from_project", {"task_gid": "111", "project_gid": "222"})

    req = asana_calls.calls[0]
    assert req["endpoint"] == "tasks/111/removeProject"
    assert req["json"]["data"] == {"project": "222"}


async def test_limits_above_asana_page_cap_are_rejected(signed_in, asana_calls):
    with pytest.raises(ToolError):
        await call("my_tasks", {"limit": 500})
    assert asana_calls.calls == []


def test_sdk_401_with_caller_token_does_not_refresh_server_identity(monkeypatch):
    from asana_sdk import infrastructure

    def refuse():
        raise AssertionError("must not touch the configured token source")

    monkeypatch.setattr(infrastructure.get_config().token_manager, "get_valid_token", refuse)
    error = SimpleNamespace(status=401, body='{"errors": [{"message": "token expired"}]}')

    with asana_sdk.use_access_token("tok-cari"):
        with pytest.raises(asana_sdk.AsanaAuthenticationError, match="caller's token"):
            infrastructure.handle_api_exception(error, "get goals")


def test_storage_defaults_to_file_store_without_table():
    from asana_auth import build_storage

    assert build_storage(dynamodb_table=None, region=None, jwt_signing_key="k" * 48) is None


def test_storage_uses_encrypted_dynamodb_table():
    from asana_auth import build_storage
    from key_value.aio.stores.dynamodb import DynamoDBStore
    from key_value.aio.wrappers.encryption import FernetEncryptionWrapper

    store = build_storage(dynamodb_table="oauth-table", region="us-west-2", jwt_signing_key="k" * 48)

    assert isinstance(store, FernetEncryptionWrapper)
    assert isinstance(store.key_value, DynamoDBStore)
    assert store.key_value._table_name == "oauth-table"


def test_storage_requires_region_for_dynamodb():
    from asana_auth import build_storage

    with pytest.raises(ValueError, match="AWS_REGION"):
        build_storage(dynamodb_table="oauth-table", region=None, jwt_signing_key="k" * 48)
