"""Asana OAuth for the remote MCP server.

Claude (desktop, web, mobile) registers itself with this server via OAuth
Dynamic Client Registration; this server then sends the person through Asana's
own login (an OAuthProxy). Each person's Asana tokens are stored encrypted and
every tool call runs as that person. Only Asana users on the allowlist get in.
"""

from __future__ import annotations

import logging

import httpx2
from cryptography.fernet import Fernet
from key_value.aio.protocols import AsyncKeyValue
from key_value.aio.wrappers.encryption import FernetEncryptionWrapper

from fastmcp.server.auth import TokenVerifier
from fastmcp.server.auth.auth import AccessToken
from fastmcp.server.auth.jwt_issuer import derive_jwt_key
from fastmcp.server.auth.oauth_proxy import OAuthProxy
from fastmcp.utilities.token_cache import TokenCache

logger = logging.getLogger(__name__)

ASANA_AUTHORIZE_URL = "https://app.asana.com/-/oauth_authorize"
ASANA_TOKEN_URL = "https://app.asana.com/-/oauth_token"
ASANA_ME_URL = "https://app.asana.com/api/1.0/users/me"

# Claude's hosted OAuth callbacks plus loopback for local MCP clients
# (Claude Code, MCP inspector). Identity is enforced by the Asana allowlist.
DEFAULT_CLIENT_REDIRECT_URIS = [
    "https://claude.ai/api/mcp/auth_callback",
    "https://claude.com/api/mcp/auth_callback",
    "http://localhost:*",
    "http://127.0.0.1:*",
]


class AsanaTokenVerifier(TokenVerifier):
    """Validates an Asana access token by calling /users/me and enforcing the allowlist.

    Asana tokens are opaque, so validation is an API call. The OAuthProxy calls
    this on every MCP request, so successful results are cached briefly.
    """

    def __init__(
        self,
        *,
        allowed_user_gids: set[str],
        timeout_seconds: int = 10,
        cache_ttl_seconds: int = 300,
    ):
        if not allowed_user_gids:
            raise ValueError("allowed_user_gids must name at least one Asana user GID")
        super().__init__(required_scopes=None)
        self.allowed_user_gids = set(allowed_user_gids)
        self.timeout_seconds = timeout_seconds
        self._cache = TokenCache(ttl_seconds=cache_ttl_seconds, max_size=1000)

    async def verify_token(self, token: str) -> AccessToken | None:
        is_cached, cached = self._cache.get(token)
        if is_cached:
            return cached

        async with httpx2.AsyncClient(timeout=self.timeout_seconds) as client:
            response = await client.get(
                ASANA_ME_URL,
                params={"opt_fields": "name,email"},
                headers={"Authorization": f"Bearer {token}", "Accept": "application/json"},
            )

        if response.status_code == 401:
            # Expected when the hour-long Asana access token lapses; the proxy refreshes it.
            logger.info("Asana rejected access token (401); proxy will attempt refresh")
            return None
        if response.status_code != 200:
            logger.error(
                "Asana /users/me returned %d while verifying a token: %s",
                response.status_code,
                response.text[:300],
            )
            return None

        user = response.json()["data"]
        user_gid = str(user["gid"])
        if user_gid not in self.allowed_user_gids:
            logger.warning(
                "Rejected Asana user %s (%s): not in ASANA_MCP_ALLOWED_USERS",
                user_gid,
                user.get("email"),
            )
            return None

        result = AccessToken(
            token=token,
            client_id=user_gid,
            scopes=[],
            expires_at=None,
            subject=user_gid,
            claims={"sub": user_gid, "name": user.get("name"), "email": user.get("email")},
        )
        self._cache.set(token, result)
        return result


class AsanaProvider(OAuthProxy):
    """OAuthProxy wired to Asana's OAuth endpoints."""

    def __init__(
        self,
        *,
        client_id: str,
        client_secret: str,
        base_url: str,
        allowed_user_gids: set[str],
        jwt_signing_key: str | bytes | None = None,
        client_storage: AsyncKeyValue | None = None,
        allowed_client_redirect_uris: list[str] | None = None,
    ):
        super().__init__(
            upstream_authorization_endpoint=ASANA_AUTHORIZE_URL,
            upstream_token_endpoint=ASANA_TOKEN_URL,
            upstream_client_id=client_id,
            upstream_client_secret=client_secret,
            token_verifier=AsanaTokenVerifier(allowed_user_gids=allowed_user_gids),
            base_url=base_url,
            redirect_path="/auth/callback",
            token_endpoint_auth_method="client_secret_post",
            client_storage=client_storage,
            jwt_signing_key=jwt_signing_key,
            require_authorization_consent=True,
            allowed_client_redirect_uris=(
                allowed_client_redirect_uris
                if allowed_client_redirect_uris is not None
                else DEFAULT_CLIENT_REDIRECT_URIS
            ),
        )


def build_storage(
    *, dynamodb_table: str | None, region: str | None, jwt_signing_key: str
) -> AsyncKeyValue | None:
    """OAuth state store: encrypted DynamoDB when a table is configured, else None.

    None lets the OAuthProxy use its default encrypted file store under FASTMCP_HOME,
    which is fine for a single host with a persistent disk.
    """
    if not dynamodb_table:
        return None
    if not region:
        raise ValueError("MCP_STORAGE_DYNAMODB_TABLE is set but AWS_REGION is not")

    from key_value.aio.stores.dynamodb import DynamoDBStore

    key = derive_jwt_key(
        high_entropy_material=jwt_signing_key, salt="asana-mcp-storage-encryption-key"
    )
    return FernetEncryptionWrapper(
        key_value=DynamoDBStore(table_name=dynamodb_table, region_name=region, auto_create=False),
        fernet=Fernet(key=key),
        raise_on_decryption_error=False,
    )
