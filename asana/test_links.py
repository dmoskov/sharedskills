#!/usr/bin/env python3
"""Unit tests for asana_links.py and link resolution in CLI commands (mocked HTTP)."""

import json
import os
import sys
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import pytest

sys.path.insert(0, str(Path(__file__).parent))

from asana_client import AsanaAPIError, AsanaClient, cmd_record, cmd_stories, cmd_task, cmd_tasks  # noqa: E402
from asana_links import (  # noqa: E402
    LinkResolver,
    annotate_fields,
    display_with_links,
    find_asana_urls,
    parse_asana_url,
)

WS = "111"
RECORD_URL = f"https://app.asana.com/1/{WS}/record/501"
TASK_URL = f"https://app.asana.com/1/{WS}/project/301/task/401"


def ok(name):
    return {"status_code": 200, "body": {"data": {"name": name}}}


def err(status, message="nope"):
    return {"status_code": status, "body": {"errors": [{"message": message}]}}


class FakeClient:
    """Answers batch_get from a {path: result} map and records every call."""

    def __init__(self, answers):
        self.answers = answers
        self.calls = []

    def batch_get(self, paths, fields=None):
        self.calls.append(list(paths))
        return [self.answers.get(p, err(404)) for p in paths]


class TestParse:
    @pytest.mark.parametrize(
        "url, expected",
        [
            (RECORD_URL, ("501", "record")),
            (TASK_URL, ("401", "task")),
            (f"https://app.asana.com/1/{WS}/task/402", ("402", "task")),
            (f"https://app.asana.com/1/{WS}/project/301", ("301", "project")),
            (f"https://app.asana.com/1/{WS}/project/301/list/9", ("301", "project")),
            (f"https://app.asana.com/1/{WS}/goal/601", ("601", "goal")),
            ("https://app.asana.com/0/goal/601", ("601", "goal")),
            ("https://app.asana.com/0/portfolio/701/list", ("701", "portfolio")),
            ("https://app.asana.com/0/0/401/f/", ("401", "task")),
            ("https://app.asana.com/0/301/401", ("401", "task")),
            ("https://app.asana.com/0/501/", ("501", None)),
            ("https://app.asana.com/0/301/list", ("301", None)),
            ("https://app.asana.com/0/profile/9", None),
            ("https://app.asana.com/1/111/home", None),
            ("https://example.com/0/1/2", None),
        ],
    )
    def test_parse(self, url, expected):
        assert parse_asana_url(url) == expected

    def test_find_urls_dedupes_and_strips_punctuation(self):
        text = f"See {RECORD_URL}, then {TASK_URL}. Again {RECORD_URL}"
        assert find_asana_urls(text) == [RECORD_URL, TASK_URL]

    def test_find_urls_ignores_non_strings_and_other_hosts(self):
        assert find_asana_urls(None) == []
        assert find_asana_urls(42) == []
        assert find_asana_urls("https://example.com/x") == []


class TestResolver:
    def test_resolves_typed_links_in_one_batch_and_caches(self):
        client = FakeClient({"/records/501": ok("Acme"), "/tasks/401": ok("Call Acme")})
        resolver = LinkResolver(client)
        links = resolver.links_in(f"{RECORD_URL} and {TASK_URL}")
        assert links == [
            {"gid": "501", "resource_type": "record", "name": "Acme", "url": RECORD_URL},
            {"gid": "401", "resource_type": "task", "name": "Call Acme", "url": TASK_URL},
        ]
        assert client.calls == [["/records/501", "/tasks/401"]]
        resolver.links_in(RECORD_URL)
        assert len(client.calls) == 1  # cached

    def test_same_gid_different_url_forms_dedupes(self):
        client = FakeClient({"/tasks/401": ok("Call Acme")})
        LinkResolver(client).links_in(f"{TASK_URL} https://app.asana.com/0/0/401/f")
        assert client.calls == [["/tasks/401"]]

    def test_untyped_url_tries_each_type(self):
        client = FakeClient({"/records/501": ok("Acme")})
        links = LinkResolver(client).links_in("https://app.asana.com/0/501/")
        assert links[0]["resource_type"] == "record" and links[0]["name"] == "Acme"
        assert client.calls == [["/projects/501", "/records/501", "/tasks/501"]]

    def test_unresolvable_links_keep_url_with_reason(self):
        client = FakeClient({"/tasks/1": err(403)})
        links = LinkResolver(client).links_in(
            f"https://app.asana.com/0/0/1 https://app.asana.com/1/{WS}/record/999 https://app.asana.com/0/77/"
        )
        assert [(link["name"], link["reason"]) for link in links] == [
            (None, "no access"),
            (None, "not found"),
            (None, "unknown object type, or not found"),
        ]

    def test_lookup_error_never_fails(self):
        class Broken:
            def batch_get(self, paths, fields=None):
                raise AsanaAPIError("Rate limited. Retry after 30s", 429)

        links = LinkResolver(Broken()).links_in(RECORD_URL)
        assert links[0]["name"] is None and "Rate limited" in links[0]["reason"]

    def test_annotate_and_display(self):
        client = FakeClient({"/records/501": ok("Acme"), "/tasks/1": err(403)})
        fields = [
            {"name": "Account", "display_value": f"{RECORD_URL} (main)", "text_value": f"{RECORD_URL} (main)"},
            {"name": "Blocked by", "display_value": "https://app.asana.com/0/0/1"},
            {"name": "Stage", "display_value": "Won"},
        ]
        annotate_fields(fields, LinkResolver(client))
        assert display_with_links(fields[0]) == "Acme (record 501) (main)"
        assert display_with_links(fields[1]) == "https://app.asana.com/0/0/1 (no access)"
        assert "links" not in fields[2] and display_with_links(fields[2]) == "Won"
        assert len(client.calls) == 1


class TestBatchGet:
    @pytest.fixture
    def client(self):
        with patch.dict(os.environ, {"ASANA_ACCESS_TOKEN": "test_token"}):
            return AsanaClient(workspace="test_ws")

    def test_chunks_at_ten_actions(self, client):
        paths = [f"/tasks/{i}" for i in range(23)]
        replies = [{"data": [ok(str(i))] * n} for i, n in enumerate((10, 10, 3))]
        with patch.object(client, "_request", side_effect=replies) as req:
            results = client.batch_get(paths, fields=["name"])
        assert len(results) == 23
        assert [len(c[1]["json_data"]["data"]["actions"]) for c in req.call_args_list] == [10, 10, 3]
        first = req.call_args_list[0]
        assert first[0][:2] == ("POST", "batch")
        assert first[1]["json_data"]["data"]["actions"][0] == {
            "method": "get", "relative_path": "/tasks/0", "options": {"fields": ["name"]}
        }


class TestCommands:
    @pytest.fixture
    def client(self):
        with patch.dict(os.environ, {"ASANA_ACCESS_TOKEN": "test_token"}):
            return AsanaClient(workspace="test_ws")

    def _args(self, **kw):
        base = {"json": False, "verbose": False}
        base.update(kw)
        return SimpleNamespace(**base)

    def test_task_resolves_by_default(self, client, capsys):
        task = {"name": "Call Acme", "custom_fields": [{"name": "Account", "display_value": RECORD_URL}]}
        with patch.object(client, "get_task", return_value=task), \
                patch.object(client, "batch_get", return_value=[ok("Acme")]) as batch:
            cmd_task(client, self._args(task_gid="401", markdown=True, plain=False, subtasks=False))
        batch.assert_called_once()
        assert "Account: Acme (record 501)" in capsys.readouterr().out

    def test_task_no_resolve_links(self, client, capsys):
        task = {"name": "Call Acme", "custom_fields": [{"name": "Account", "display_value": RECORD_URL}]}
        with patch.object(client, "get_task", return_value=task), \
                patch.object(client, "batch_get") as batch:
            cmd_task(client, self._args(task_gid="401", markdown=True, plain=False, subtasks=False,
                                        no_resolve_links=True, json=True))
        batch.assert_not_called()
        assert "links" not in json.loads(capsys.readouterr().out)["custom_fields"][0]

    def test_tasks_resolve_only_on_request(self, client, capsys):
        tasks = [{"gid": str(i), "name": f"T{i}", "custom_fields": [{"name": "Account", "display_value": RECORD_URL}]}
                 for i in range(3)]
        args = dict(assignee=None, project="p1", section=None, incomplete=False, limit=100)
        with patch.object(client, "get_tasks", return_value=tasks), patch.object(client, "batch_get") as batch:
            cmd_tasks(client, self._args(**args))
        batch.assert_not_called()
        capsys.readouterr()

        with patch.object(client, "get_tasks", return_value=tasks), \
                patch.object(client, "batch_get", return_value=[ok("Acme")]) as batch:
            cmd_tasks(client, self._args(json=True, resolve_links=True, **args))
        assert batch.call_args[0][0] == ["/records/501"]  # one lookup for three tasks
        out = json.loads(capsys.readouterr().out)
        assert out[2]["custom_fields"][0]["links"][0]["name"] == "Acme"

    def test_record_shows_names_in_values_and_comments(self, client, capsys):
        record = {"gid": "502", "name": "Deal", "custom_fields": [{"name": "Account", "display_value": RECORD_URL}]}
        stories = [{
            "resource_subtype": "comment_added", "created_at": "2026-01-01", "created_by": {"name": "Pat"},
            "text": f"ping https://app.asana.com/0/{WS}/",
            "html_text": f'<body>ping <a href="https://app.asana.com/0/{WS}/" data-asana-type="user">@Lee</a></body>',
        }]
        with patch.object(client, "get_record", return_value=record), \
                patch.object(client, "get_record_stories", return_value=stories), \
                patch.object(client, "batch_get", return_value=[ok("Acme")]):
            cmd_record(client, self._args(record_gid="502"))
        out = capsys.readouterr().out
        assert "Account: Acme (record 501)" in out
        assert "Pat: ping [@Lee]" in out

    def test_stories_use_rich_text_for_comments(self, client, capsys):
        stories = [{
            "resource_subtype": "comment_added", "created_at": "2026-01-01", "created_by": {"name": "Pat"},
            "text": f"see {RECORD_URL}",
            "html_text": f'<body>see <a href="{RECORD_URL}" data-asana-type="record_item">Acme</a></body>',
        }]
        with patch.object(client, "get_stories", return_value=stories):
            cmd_stories(client, self._args(task_gid="401", limit=50))
        assert "Pat: see [Acme](" in capsys.readouterr().out
