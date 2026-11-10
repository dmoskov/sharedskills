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
- `server.py`: 79 tools covering tasks, subtasks, followers, search, sections, comments,
  dependencies, tags, custom fields, teams, portfolios, project status updates, goals,
  attachments, the Inbox, project create/update/search, task and project duplication and
  templates, comment editing, likes and reactions, and out-of-office entries.
- Duplication, templates and date rollups are asynchronous jobs in Asana. Those tools wait
  up to 20 seconds and return the new task or project, or `status` if it is still running.
- Asana's API can like a task but cannot like a comment or add an emoji reaction; reactions
  are read-only. Project search needs a paid Asana plan. Descriptions and comments take markdown and are converted to Asana
  rich text; task descriptions come back as markdown; task results include a `url`.
- File attachments: MCP tool arguments are text, so real files don't go through them.
  `get_upload_link` returns a one-time, 15-minute URL under `/uploads/`; the client PUTs
  the raw bytes there (`curl -T photo.jpg '<url>'`) and the server attaches them as the
  person who asked for the link. `attach_file_from_url` downloads a public https URL
  (SSRF-guarded: public IPs only, no redirects). `attach_file` remains for small text.
  The client must be able to reach the server over HTTPS from its shell, e.g. Claude
  Code, or a claude.ai sandbox whose network settings allow the server's domain.
- Inbox: `get_notifications` lists the caller's unarchived Inbox, and
  `mark_notifications_read` / `mark_notifications_unread` change read state (unread also
  unarchives). Asana's public API has no archive action, so these tools can't archive.
- `create_task(remove_me_as_follower=true)` drops the creator, whom Asana adds as a
  follower automatically; `remove_followers` does the same for any existing task.
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
| `MCP_STORAGE_DYNAMODB_TABLE` + `AWS_REGION` | no | Store OAuth state in DynamoDB (hash key `collection`, range key `key`, TTL attribute `ttl`). Otherwise it is an encrypted file store under `FASTMCP_HOME` (`/data` in the image), which must persist across deploys. Pending upload links share this store (in memory when no table is set) |
| `MCP_SERVER_NAME` | no | Name shown to clients (default `Asana`) |
| `ASANA_MCP_CLIENT_REDIRECT_URIS` | no | Override the allowed MCP client callbacks (default: claude.ai, claude.com, loopback) |
| `HOST` / `PORT` | no | Default `0.0.0.0:8000`. The MCP endpoint is `/mcp` |
| `ASANA_MCP_MAX_UPLOAD_MB` | no | Largest file accepted by upload links and URL attachments (default 50; Asana's own limit is 100) |
| `FORWARDED_ALLOW_IPS` | no | Read by uvicorn. Behind a load balancer, set it to the balancer's addresses or CIDRs so redirects keep `https` |

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
