"""Standalone OAuth integration; all credentials and external operations are mocked."""

import io
import json
import os
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import MagicMock, patch
import urllib.error

import pytest

sys.path.insert(0, str(Path(__file__).parent))
from asana_client import AsanaAuthError, AsanaClient
from asana_sdk import token_manager


@pytest.fixture(autouse=True)
def isolated_auth(monkeypatch):
    for name in ("ASANA_OAUTH_SECRET", "ASANA_ACCESS_TOKEN", "SECRETS_REGION", "AWS_REGION"):
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setattr(token_manager, "BOTO3_AVAILABLE", True)
    monkeypatch.setattr(token_manager, "boto3", MagicMock())
    with patch.object(token_manager.urllib.request, "urlopen", side_effect=AssertionError("Unexpected provider call")), \
            patch("requests.Session.request", side_effect=AssertionError("Unexpected API call")):
        yield


def credentials(*, expired=False):
    return {
        "access_token": "fake-cached-token",
        "refresh_token": "fake-refresh-token",
        "client_id": "fake-client-id",
        "client_secret": "fake-client-secret",
        "expires_at": (datetime.now(timezone.utc) + timedelta(hours=-1 if expired else 2)).isoformat(),
        "unrelated_metadata": "preserved",
    }


def mock_secret(monkeypatch, *, expired=False):
    monkeypatch.setenv("ASANA_OAUTH_SECRET", "test/oauth")
    sm = token_manager.boto3.client.return_value
    sm.get_secret_value.return_value = {"SecretString": json.dumps(credentials(expired=expired))}
    return sm


def test_configured_secret_wins_over_environment_and_never_reads_file(monkeypatch):
    sm = mock_secret(monkeypatch)
    monkeypatch.setenv("ASANA_ACCESS_TOKEN", "fake-stale-environment-token")
    with patch.object(AsanaClient, "_load_oauth_token", side_effect=AssertionError("File fallback forbidden")), \
            patch("builtins.open", side_effect=AssertionError("Credential file read forbidden")):
        client = AsanaClient()
    assert client._token == "fake-cached-token"
    sm.get_secret_value.assert_called_once_with(SecretId="test/oauth")
    sm.put_secret_value.assert_not_called()
    token_manager.boto3.client.assert_called_once_with("secretsmanager", region_name="us-west-2")


@pytest.mark.parametrize("env,expected", [
    ({"AWS_REGION": "eu-west-1"}, "eu-west-1"),
    ({"AWS_REGION": "eu-west-1", "SECRETS_REGION": "us-east-2"}, "us-east-2"),
])
def test_region_overrides_are_preserved(monkeypatch, env, expected):
    mock_secret(monkeypatch)
    for key, value in env.items():
        monkeypatch.setenv(key, value)
    AsanaClient()
    token_manager.boto3.client.assert_called_once_with("secretsmanager", region_name=expected)


def test_explicit_constructor_token_keeps_precedence(monkeypatch):
    mock_secret(monkeypatch)
    monkeypatch.setenv("ASANA_ACCESS_TOKEN", "fake-env-token")
    client = AsanaClient(token="fake-explicit-token")
    assert client._token == "fake-explicit-token"
    token_manager.boto3.client.assert_not_called()


def test_environment_token_remains_supported_without_secret(monkeypatch):
    monkeypatch.setenv("ASANA_ACCESS_TOKEN", "fake-env-token")
    with patch.object(AsanaClient, "_load_oauth_token", side_effect=AssertionError("Unexpected file read")):
        client = AsanaClient()
    assert client._token == "fake-env-token"
    token_manager.boto3.client.assert_not_called()


def test_local_oauth_compatibility_remains_without_secret():
    with patch.object(AsanaClient, "_load_oauth_token", return_value="fake-local-token") as local:
        client = AsanaClient()
    assert client._token == "fake-local-token"
    local.assert_called_once_with()
    token_manager.boto3.client.assert_not_called()


@pytest.mark.parametrize("failure", ["read", "malformed", "missing-fields", "refresh"])
def test_configured_secret_errors_never_fall_back(monkeypatch, failure):
    sm = mock_secret(monkeypatch, expired=True)
    monkeypatch.setenv("ASANA_ACCESS_TOKEN", "fake-fallback-token")
    if failure == "read":
        sm.get_secret_value.side_effect = RuntimeError("AccessDenied")
    elif failure == "malformed":
        sm.get_secret_value.return_value = {"SecretString": "not-json"}
    elif failure == "missing-fields":
        sm.get_secret_value.return_value = {"SecretString": "{}"}
    with patch.object(AsanaClient, "_load_oauth_token", side_effect=AssertionError("File fallback forbidden")), \
            patch.object(token_manager.urllib.request, "urlopen", side_effect=urllib.error.URLError("rejected")):
        with pytest.raises(AsanaAuthError):
            AsanaClient()
    sm.put_secret_value.assert_not_called()


def test_missing_boto3_does_not_fall_back(monkeypatch):
    mock_secret(monkeypatch)
    monkeypatch.setenv("ASANA_ACCESS_TOKEN", "fake-fallback-token")
    monkeypatch.setattr(token_manager, "BOTO3_AVAILABLE", False)
    with pytest.raises(AsanaAuthError, match="boto3 is required"):
        AsanaClient()


def test_refresh_writes_back_rotated_token_without_local_file(monkeypatch):
    sm = mock_secret(monkeypatch, expired=True)
    response = io.StringIO(json.dumps({
        "access_token": "fake-fresh-token", "refresh_token": "fake-rotated-token", "expires_in": 3600,
    }))
    with patch.object(token_manager.urllib.request, "urlopen", return_value=response) as provider, \
            patch("builtins.open", side_effect=AssertionError("Credential file access forbidden")):
        client = AsanaClient()
    assert client._token == "fake-fresh-token"
    assert provider.call_count == 1
    payload = sm.put_secret_value.call_args.kwargs
    assert payload["SecretId"] == "test/oauth"
    saved = json.loads(payload["SecretString"])
    assert saved["access_token"] == "fake-fresh-token"
    assert saved["refresh_token"] == "fake-rotated-token"
    assert saved["unrelated_metadata"] == "preserved"
    assert datetime.fromisoformat(saved["expires_at"]) > datetime.now(timezone.utc)


def test_long_lived_client_re_resolves_same_secret_before_request(monkeypatch):
    sm = mock_secret(monkeypatch)
    client = AsanaClient()
    updated = credentials()
    updated["access_token"] = "fake-next-token"
    sm.get_secret_value.return_value = {"SecretString": json.dumps(updated)}
    monkeypatch.delenv("ASANA_OAUTH_SECRET")
    monkeypatch.setenv("ASANA_ACCESS_TOKEN", "fake-stale-token")
    response = MagicMock(status_code=200, ok=True)
    response.json.return_value = {"data": []}
    with patch.object(client._session, "request", return_value=response) as api:
        assert client._request("GET", "workspaces") == {"data": []}
    assert api.call_args.kwargs["headers"]["Authorization"] == "Bearer fake-next-token"
    assert [call.kwargs for call in sm.get_secret_value.call_args_list] == [
        {"SecretId": "test/oauth"}, {"SecretId": "test/oauth"},
    ]


def test_request_stops_if_secret_becomes_unavailable(monkeypatch):
    sm = mock_secret(monkeypatch)
    client = AsanaClient()
    sm.get_secret_value.side_effect = RuntimeError("AccessDenied")
    with patch.object(client._session, "request") as api:
        with pytest.raises(AsanaAuthError):
            client._request("GET", "workspaces")
    api.assert_not_called()
