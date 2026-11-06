# Asana MCP server (remote, multi-user)

A remote MCP server that exposes this directory's Asana library (`asana_client.py`
+ `asana_sdk/`) to Claude Desktop, claude.ai and the Claude mobile apps as a custom
connector. Each person signs in with their own Asana account and every tool call
runs as them.

## How it works

```
Claude (desktop / web / mobile)
   │  OAuth 2.1 + dynamic client registration
   ▼
this server (FastMCP OAuthProxy)  ──login──▶  Asana OAuth (dedicated app)
   │  per-request Asana token
   ▼
asana_client / asana_sdk  ───────────────▶  Asana REST API
```

- `asana_auth.py`: `AsanaProvider` sends people through Asana's own login, stores their
  Asana tokens encrypted, refreshes them when the one-hour access token lapses, and lets
  in only the Asana user GIDs listed in `ASANA_MCP_ALLOWED_USERS`.
- `server.py`: 48 tools covering tasks, subtasks, search, sections, comments,
  dependencies, tags, custom fields, teams, portfolios, project status updates, goals,
  and attachments. Descriptions and comments take markdown and are converted to Asana
  rich text; task descriptions come back as markdown; task results include a `url`.
- The SDK runs in per-request mode (`ASANA_SDK_REQUIRE_TOKEN_OVERRIDE=1`, set by
  `server.py`), so a request can never fall back to a token configured on the server.

## Configuration

| Variable | Required | Meaning |
|---|---|---|
| `ASANA_OAUTH_CLIENT_ID` / `ASANA_OAUTH_CLIENT_SECRET` | yes | A dedicated Asana OAuth app (see SETUP.md) |
| `MCP_BASE_URL` | yes | Public HTTPS origin, e.g. `https://asana-mcp.example.com` |
| `MCP_JWT_SIGNING_KEY` | yes | Long random string. Signs the tokens issued to Claude and derives the storage encryption key; changing it signs everyone out |
| `ASANA_MCP_ALLOWED_USERS` | yes | Comma-separated Asana user GIDs allowed to connect |
| `ASANA_WORKSPACE` | yes | Default workspace GID |
| `MCP_STORAGE_DYNAMODB_TABLE` + `AWS_REGION` | no | Store OAuth state in DynamoDB (hash key `collection`, range key `key`, TTL attribute `ttl`). Otherwise it is an encrypted file store under `FASTMCP_HOME` (`/data` in the image), which must persist across deploys |
| `MCP_SERVER_NAME` | no | Name shown to clients (default `Asana`) |
| `ASANA_MCP_CLIENT_REDIRECT_URIS` | no | Override the allowed MCP client callbacks (default: claude.ai, claude.com, loopback) |
| `HOST` / `PORT` | no | Default `0.0.0.0:8000`. The MCP endpoint is `/mcp` |

The server refuses to start if `ASANA_ACCESS_TOKEN` or `ASANA_OAUTH_SECRET` is set.

## Develop

```bash
cd asana/mcp_server
uv venv --python 3.13 .venv
uv pip install --python .venv/bin/python -r requirements.txt pytest pytest-asyncio
.venv/bin/python -m pytest tests -q
```

Container (build from `asana/` so the lib is in the context):

```bash
docker build -f mcp_server/Dockerfile -t asana-mcp .
```

Deploy and connect: see [SETUP.md](SETUP.md).
