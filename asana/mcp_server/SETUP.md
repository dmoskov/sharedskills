# Setup

## 1. Create a dedicated Asana OAuth app

Use a new app just for this server. Re-authorizing an app that another system already
uses can invalidate that system's refresh token.

1. https://app.asana.com/0/my-apps → **Create new app**.
2. **OAuth** → Redirect URLs: add `https://<public host>/auth/callback`
   (and optionally `http://localhost:8011/auth/callback` for local end-to-end tests).
3. Permission scopes: **Full permissions** (goals, portfolios and attachments need it).
4. **Manage distribution**: limit it to your workspace.
5. Put the client ID and secret in your host's secret store.

## 2. Deploy

Run the container anywhere that provides:

- a public HTTPS URL (Claude's cloud must reach it; localhost won't work for mobile),
- persistent OAuth state: a DynamoDB table, or a persistent volume at `/data`,
- the environment variables from README.md, with secrets injected from a secret store.

Health check: `GET /.well-known/oauth-authorization-server` returns 200.

## 3. Connect from Claude (each person, once)

1. claude.ai → **Settings → Connectors → Add custom connector**.
2. URL: `https://<public host>/mcp`.
3. **Connect** → approve the consent screen → sign in to Asana → allow.

Connectors added on claude.ai are also available in Claude Desktop and the mobile apps
for the same account. In a Team/Enterprise org, an owner can add it once for everyone.

## 4. Check it

Ask Claude "Using the Asana connector, who am I?" It should call `whoami`. People not on
`ASANA_MCP_ALLOWED_USERS` can finish Asana's login, but every request then fails with
401, and the server logs `Rejected Asana user <gid>`.
