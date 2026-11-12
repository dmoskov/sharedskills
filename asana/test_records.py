#!/usr/bin/env python3
"""Unit tests for table and record support in asana_client.py (mocked HTTP)."""

import json
import os
import sys
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import pytest

sys.path.insert(0, str(Path(__file__).parent))

from asana_client import (  # noqa: E402
    AsanaAPIError,
    AsanaClient,
    AsanaError,
    _parse_field_args,
    cmd_import_records,
    cmd_records,
    cmd_upsert_record,
)

COLUMNS = [
    {"gid": "f_domain", "name": "Domain", "resource_subtype": "text"},
    {
        "gid": "f_stage",
        "name": "Stage",
        "resource_subtype": "enum",
        "enum_options": [{"gid": "o_lead", "name": "Lead"}, {"gid": "o_won", "name": "Won"}],
    },
    {
        "gid": "f_tags",
        "name": "Tags",
        "resource_subtype": "multi_enum",
        "enum_options": [{"gid": "o_red", "name": "Red"}, {"gid": "o_blue", "name": "Blue"}],
    },
    {"gid": "f_size", "name": "Size", "resource_subtype": "number"},
    {"gid": "f_since", "name": "Since", "resource_subtype": "date"},
    {"gid": "f_owner", "name": "Owner", "resource_subtype": "people"},
]


@pytest.fixture
def client():
    with patch.dict(os.environ, {"ASANA_ACCESS_TOKEN": "test_token"}):
        return AsanaClient(workspace="test_ws")


def _record(gid, name, domain=None):
    fields = [{"gid": "f_domain", "name": "Domain", "display_value": domain}] if domain else []
    return {"gid": gid, "name": name, "custom_fields": fields}


class TestTables:
    def test_get_tables_pages_through_workspace(self, client):
        pages = [
            {"data": [{"gid": "t1"}], "next_page": {"offset": "abc"}},
            {"data": [{"gid": "t2"}], "next_page": None},
        ]
        with patch.object(client, "_request", side_effect=pages) as req:
            assert [t["gid"] for t in client.get_tables()] == ["t1", "t2"]
        assert req.call_args_list[0][0][1] == "workspaces/test_ws/tables"
        assert req.call_args_list[1][0][2]["offset"] == "abc"
        assert req.call_args_list[0][0][2]["limit"] == "100"

    def test_get_table_reads_columns_from_settings_endpoint(self, client):
        responses = [
            {"data": {"gid": "t1", "name": "Accounts", "custom_field_settings": []}},
            {"data": [{"custom_field": COLUMNS[0]}, {"custom_field": COLUMNS[1]}]},
        ]
        with patch.object(client, "_request", side_effect=responses) as req:
            table = client.get_table("t1")
        assert req.call_args_list[1][0][1] == "tables/t1/custom_field_settings"
        assert [c["name"] for c in table["columns"]] == ["Domain", "Stage"]

    def test_create_table(self, client):
        with patch.object(client, "_request", return_value={"data": {"gid": "t1"}}) as req:
            client.create_table("Accounts")
        assert req.call_args[0][:2] == ("POST", "tables")
        assert req.call_args[1]["json_data"] == {"data": {"name": "Accounts", "workspace": "test_ws"}}

    def test_add_enum_column_creates_field_inline(self, client):
        response = {"data": {"custom_field": {"gid": "f1", "name": "Stage"}}}
        with patch.object(client, "_request", return_value=response) as req:
            field = client.add_table_column("t1", "Stage", "enum", options=["Lead", "Won"])
        assert req.call_args[0][1] == "tables/t1/addCustomFieldSetting"
        assert req.call_args[1]["json_data"] == {
            "data": {
                "custom_field": {
                    "name": "Stage",
                    "resource_subtype": "enum",
                    "enum_options": [{"name": "Lead"}, {"name": "Won"}],
                }
            }
        }
        assert field["gid"] == "f1"

    def test_add_column_reuses_existing_field(self, client):
        with patch.object(client, "_request", return_value={"data": {"custom_field": {"gid": "f9"}}}) as req:
            client.add_table_column("t1", custom_field="f9")
        assert req.call_args[1]["json_data"] == {"data": {"custom_field": "f9"}}

    @pytest.mark.parametrize(
        "kwargs, message",
        [
            ({"name": "Stage", "field_type": "enum"}, "at least one option"),
            ({"name": "Notes", "field_type": "text", "options": ["x"]}, "only apply to enum"),
            ({"name": "Due", "field_type": "date", "precision": 2}, "precision only applies"),
            ({"name": "Ref", "field_type": "reference"}, "field_type must be one of"),
            ({}, "name is required"),
        ],
    )
    def test_add_column_validates(self, client, kwargs, message):
        with pytest.raises(ValueError, match=message):
            client.add_table_column("t1", **kwargs)


class TestFieldResolution:
    def test_resolves_names_and_values_for_every_type(self):
        fields = AsanaClient.resolve_record_fields(
            COLUMNS,
            {
                "Domain": "acme.example",
                "stage": "won",
                "Tags": "Red, Blue",
                "Size": "12",
                "Since": "2026-01-15",
                "Owner": "me, someone@example.com",
            },
        )
        assert fields == {
            "f_domain": "acme.example",
            "f_stage": "o_won",
            "f_tags": ["o_red", "o_blue"],
            "f_size": 12,
            "f_since": {"date": "2026-01-15"},
            "f_owner": ["me", "someone@example.com"],
        }

    def test_accepts_gids_and_api_shaped_values(self):
        fields = AsanaClient.resolve_record_fields(
            COLUMNS, {"f_stage": "o_lead", "Size": 2.5, "Tags": ["blue"], "Since": {"date": "2026-02-01"}}
        )
        assert fields == {"f_stage": "o_lead", "f_size": 2.5, "f_tags": ["o_blue"], "f_since": {"date": "2026-02-01"}}

    def test_empty_value_clears(self):
        assert AsanaClient.resolve_record_fields(COLUMNS, {"Stage": "", "Size": None}) == {
            "f_stage": None,
            "f_size": None,
        }

    def test_unknown_column_lists_columns(self):
        with pytest.raises(ValueError, match="No column 'Nope'.*'Domain'"):
            AsanaClient.resolve_record_fields(COLUMNS, {"Nope": "x"})

    def test_unknown_option_lists_options(self):
        with pytest.raises(ValueError, match="no option 'Lost'.*'Lead', 'Won'"):
            AsanaClient.resolve_record_fields(COLUMNS, {"Stage": "Lost"})

    def test_bad_number(self):
        with pytest.raises(ValueError, match="not a number"):
            AsanaClient.resolve_record_fields(COLUMNS, {"Size": "lots"})

    def test_ambiguous_case_insensitive_name(self):
        columns = [{"gid": "a", "name": "Stage"}, {"gid": "b", "name": "STAGE"}]
        assert AsanaClient.find_column(columns, "Stage")["gid"] == "a"
        with pytest.raises(ValueError, match="ambiguous"):
            AsanaClient.find_column(columns, "stage")

    def test_record_values_shows_all_day_dates_as_dates(self):
        record = {
            "custom_fields": [
                {"name": "Since", "display_value": "2026-01-15T00:00:00.000Z",
                 "date_value": {"date": "2026-01-15", "date_time": None}},
                {"name": "Stage", "display_value": "Won"},
            ]
        }
        assert AsanaClient.record_values(record) == {"Since": "2026-01-15", "Stage": "Won"}

    def test_parse_field_args_merges_json_then_pairs(self):
        args = SimpleNamespace(fields_json='{"Stage": "Lead", "Size": 3}', field=["Stage=Won", "Domain = a=b"])
        assert _parse_field_args(args) == {"Stage": "Won", "Size": 3, "Domain": "a=b"}

    def test_parse_field_args_rejects_bad_pair(self):
        with pytest.raises(AsanaError, match="Column=value"):
            _parse_field_args(SimpleNamespace(fields_json=None, field=["Stage"]))


class TestRecords:
    def test_get_records_pages_fully(self, client):
        pages = [
            {"data": [{"gid": str(i)} for i in range(100)], "next_page": {"offset": "o1"}},
            {"data": [{"gid": "100"}], "next_page": None},
        ]
        with patch.object(client, "_request", side_effect=pages) as req:
            records = client.get_records("t1", modified_since="2026-01-01T00:00:00Z")
        assert len(records) == 101
        assert req.call_args_list[0][0][1] == "tables/t1/records"
        assert req.call_args_list[0][0][2]["modified_since"] == "2026-01-01T00:00:00Z"

    def test_create_record_sends_fingerprint_and_fills_permalink(self, client):
        response = {"data": {"gid": "r1", "workspace": {"gid": "ws1"}}}
        with patch.object(client, "_request", return_value=response) as req:
            record = client.create_record("t1", "Acme", {"f_domain": "acme.example"}, unique_fingerprint="acme")
        assert req.call_args[0][:2] == ("POST", "records")
        assert req.call_args[1]["json_data"] == {
            "data": {
                "name": "Acme",
                "table": "t1",
                "custom_fields": {"f_domain": "acme.example"},
                "unique_fingerprint": "acme",
            }
        }
        assert record["permalink_url"] == "https://app.asana.com/1/ws1/record/r1"

    def test_update_record(self, client):
        with patch.object(client, "_request", return_value={"data": {"gid": "r1"}}) as req:
            client.update_record("r1", name="Acme Inc", custom_fields={"f_stage": "o_won"})
        assert req.call_args[0][:2] == ("PUT", "records/r1")
        assert req.call_args[1]["json_data"] == {"data": {"name": "Acme Inc", "custom_fields": {"f_stage": "o_won"}}}

    def test_update_record_needs_changes(self, client):
        with pytest.raises(ValueError, match="No updates"):
            client.update_record("r1")

    def test_delete_record(self, client):
        with patch.object(client, "_request", return_value={"data": {}}) as req:
            assert client.delete_record("r1") is True
        assert req.call_args[0][:2] == ("DELETE", "records/r1")

    def test_search_records(self, client):
        with patch.object(client, "_request", return_value={"data": [{"gid": "r1"}]}) as req:
            client.search_records(text="acme", tables=["t1", "t2"], limit=10)
        assert req.call_args[0][1] == "workspaces/test_ws/records/search"
        params = req.call_args[0][2]
        assert params["text"] == "acme" and params["tables.any"] == "t1,t2" and params["limit"] == "10"

    def test_search_records_requires_a_filter(self, client):
        with pytest.raises(ValueError, match="at least one search filter"):
            client.search_records()

    def test_record_comment(self, client):
        with patch.object(client, "_request", return_value={"data": {"gid": "s1"}}) as req:
            client.add_record_comment("r1", "hi")
        assert req.call_args[0][:2] == ("POST", "records/r1/stories")
        assert req.call_args[1]["json_data"] == {"data": {"text": "hi"}}


class TestUpsert:
    def test_creates_with_key_value_as_fingerprint(self, client):
        with patch.object(client, "create_record", return_value={"gid": "r1"}) as create:
            action, record = client.upsert_record(
                "t1", "Acme", {"Domain": "acme.example", "Stage": "Lead"}, key="Domain", columns=COLUMNS
            )
        assert action == "created"
        assert create.call_args[1]["unique_fingerprint"] == "acme.example"
        assert create.call_args[0][2] == {"f_domain": "acme.example", "f_stage": "o_lead"}

    def test_conflict_finds_existing_by_key_and_updates(self, client):
        conflict = AsanaAPIError("API error 409: already exists", 409)
        existing = [_record("r0", "Other", "other.example"), _record("r7", "Acme", "ACME.example")]
        with patch.object(client, "create_record", side_effect=conflict), \
                patch.object(client, "get_records", return_value=existing), \
                patch.object(client, "update_record", return_value={"gid": "r7"}) as update:
            action, record = client.upsert_record(
                "t1", "Acme Inc", {"Domain": "acme.example", "Stage": "Won"}, key="Domain", columns=COLUMNS
            )
        assert action == "updated" and record["gid"] == "r7"
        assert update.call_args[0][0] == "r7"
        assert update.call_args[1] == {"name": "Acme Inc", "custom_fields": {"f_domain": "acme.example", "f_stage": "o_won"}}

    def test_conflict_with_no_matching_key_explains(self, client):
        conflict = AsanaAPIError("API error 409", 409)
        with patch.object(client, "create_record", side_effect=conflict), \
                patch.object(client, "get_records", return_value=[]):
            with pytest.raises(AsanaError, match="probably edited"):
                client.upsert_record("t1", "Acme", {"Domain": "acme.example"}, key="Domain", columns=COLUMNS)

    def test_upsert_by_name(self, client):
        conflict = AsanaAPIError("API error 409", 409)
        with patch.object(client, "create_record", side_effect=conflict) as create, \
                patch.object(client, "get_records", return_value=[_record("r3", "Acme")]), \
                patch.object(client, "update_record", return_value={"gid": "r3"}):
            action, _ = client.upsert_record("t1", "Acme", {}, key="name", columns=COLUMNS)
        assert action == "updated"
        assert create.call_args[1]["unique_fingerprint"] == "Acme"

    def test_other_errors_propagate(self, client):
        with patch.object(client, "create_record", side_effect=AsanaAPIError("API error 403", 403)):
            with pytest.raises(AsanaAPIError):
                client.upsert_record("t1", "Acme", {"Domain": "a"}, key="Domain", columns=COLUMNS)

    def test_requires_key_value(self, client):
        with pytest.raises(ValueError, match="needs a value for the key column 'Domain'"):
            client.upsert_record("t1", "Acme", {"Stage": "Lead"}, key="domain", columns=COLUMNS)


class TestRecordCommands:
    def _args(self, **kw):
        base = {"json": False, "verbose": False}
        base.update(kw)
        return SimpleNamespace(**base)

    def test_cmd_records(self, client, capsys):
        records = [{"gid": "r1", "name": "Acme", "custom_fields": [{"name": "Stage", "display_value": "Won"}]}]
        with patch.object(client, "get_records", return_value=records):
            cmd_records(client, self._args(table_gid="t1", modified_since=None))
        out = capsys.readouterr().out
        assert "Acme  —  Stage: Won" in out and "(1 records)" in out

    def test_cmd_upsert_json(self, client, capsys):
        with patch.object(client, "upsert_record", return_value=("updated", {"gid": "r1"})) as upsert:
            cmd_upsert_record(
                client,
                self._args(json=True, table="t1", name="Acme", key="Domain", fingerprint=None,
                           field=["Domain=acme.example"], fields_json=None),
            )
        assert upsert.call_args[0] == ("t1", "Acme", {"Domain": "acme.example"})
        assert json.loads(capsys.readouterr().out) == {"action": "updated", "record": {"gid": "r1"}}

    def test_cmd_import_records(self, client, tmp_path, capsys):
        path = tmp_path / "rows.csv"
        path.write_text(
            "Name,Domain,Stage\n"
            "Acme,acme.example,Won\n"
            "Globex,globex.example,\n"
            ",nameless.example,Lead\n"
        )
        index = {"acme.example": {"gid": "r1"}}
        args = self._args(table_gid="t1", file=str(path), key="domain", name_column="Name",
                          skip_empty=True, dry_run=False)
        with patch.object(client, "get_table_columns", return_value=COLUMNS), \
                patch.object(client, "index_records", return_value=index), \
                patch.object(client, "update_record", return_value={"gid": "r1"}) as update, \
                patch.object(client, "upsert_record", return_value=("created", {"gid": "r2"})) as upsert:
            cmd_import_records(client, args)
        assert update.call_args[0][0] == "r1"
        assert update.call_args[1]["custom_fields"] == {"f_domain": "acme.example", "f_stage": "o_won"}
        # --skip-empty drops Globex's blank Stage instead of clearing it
        assert upsert.call_args[0][2] == {"Domain": "globex.example"}
        assert "1 created, 1 updated, 1 skipped, 0 failed" in capsys.readouterr().out

    def test_cmd_import_records_jsonl_dry_run(self, client, tmp_path, capsys):
        path = tmp_path / "rows.jsonl"
        path.write_text('{"Name": "Acme", "Domain": "acme.example", "Stage": "Nope"}\n')
        args = self._args(json=True, table_gid="t1", file=str(path), key="Domain", name_column="Name",
                          skip_empty=False, dry_run=True)
        with patch.object(client, "get_table_columns", return_value=COLUMNS), \
                patch.object(client, "index_records", return_value={}), \
                patch.object(client, "_request") as req:
            with pytest.raises(SystemExit):
                cmd_import_records(client, args)
        req.assert_not_called()
        result = json.loads(capsys.readouterr().out)
        assert result["counts"]["failed"] == 1 and "no option 'Nope'" in result["results"][0]["error"]
