# Asana Skills Setup Guide

## Prerequisites

- Python 3.8+
- `requests` library: `pip install requests`

## Step 1: Get Authentication

### Option A: Personal Access Token (Quick Start)

1. Go to [Asana Developer Console](https://app.asana.com/0/developer-console)
2. Click **"Personal Access Tokens"** → **"Create New Token"**
3. Copy the token immediately (won't be shown again)
4. Set environment variable:
   ```bash
   export ASANA_ACCESS_TOKEN="your_token_here"
   ```

### Option B: OAuth (Recommended for Production)

1. Go to [Asana Developer Console](https://app.asana.com/0/developer-console)
2. Click **"+ Create New App"**
3. Set redirect URL: `http://localhost:8765/oauth/callback`
4. Save Client ID and Client Secret
5. Run setup:
   ```bash
   export ASANA_OAUTH_CLIENT_ID="your_client_id"
   export ASANA_OAUTH_CLIENT_SECRET="your_client_secret"
   cd asana && python3 oauth_setup.py
   ```

## Step 2: Find Your Workspace

```bash
cd asana && python3 asana_client.py workspaces
```

Output:
```
Workspaces:
- My Workspace (1234567890123456)
```

Optionally set default:
```bash
export ASANA_WORKSPACE="1234567890123456"
```

## Step 3: Test

```bash
# List projects
python3 asana_client.py projects

# Search tasks
python3 asana_client.py search "test"
```

## Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `ASANA_ACCESS_TOKEN` | Yes* | Personal Access Token |
| `ASANA_OAUTH_CLIENT_ID` | Yes** | OAuth client ID |
| `ASANA_OAUTH_CLIENT_SECRET` | Yes** | OAuth client secret |
| `ASANA_WORKSPACE` | No | Default workspace GID |

\* Required if not using OAuth
\** Required if using OAuth

## Troubleshooting

### "Authentication failed"
- Verify token is correct and hasn't expired
- For OAuth: run `python3 oauth_setup.py` again

### "Workspace not found"
- Run `python3 asana_client.py workspaces` to find correct GID
- Check `ASANA_WORKSPACE` matches your actual workspace

### "Module not found"
```bash
pip install requests
```
