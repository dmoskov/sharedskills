#!/usr/bin/env python3
"""
Asana OAuth Setup

Interactive script to authenticate with Asana using OAuth 2.0.
Stores tokens in ~/.config/asana/tokens.json for use by asana_client and asana_sdk.

Usage:
    python3 oauth_setup.py

Requirements:
    1. Create an Asana app at https://app.asana.com/0/my-apps
    2. Set redirect URL to: http://localhost:8765/callback
    3. Note your Client ID and Client Secret

The script will:
    1. Prompt for your Client ID and Client Secret
    2. Open browser for Asana authorization
    3. Capture the callback and exchange for tokens
    4. Save tokens to ~/.config/asana/tokens.json
"""

import http.server
import json
import os
import secrets
import socketserver
import sys
import threading
import time
import urllib.parse
import urllib.request
import webbrowser
from pathlib import Path
from typing import Optional, Dict, Any

# Token storage location
TOKEN_FILE = Path.home() / ".config" / "asana" / "tokens.json"
CREDENTIALS_FILE = Path.home() / ".config" / "asana" / "credentials.json"

# OAuth endpoints
ASANA_AUTH_URL = "https://app.asana.com/-/oauth_authorize"
ASANA_TOKEN_URL = "https://app.asana.com/-/oauth_token"

# Local callback server
CALLBACK_PORT = 8765
CALLBACK_PATH = "/callback"
REDIRECT_URI = f"http://localhost:{CALLBACK_PORT}{CALLBACK_PATH}"


class OAuthCallbackHandler(http.server.BaseHTTPRequestHandler):
    """HTTP handler to capture OAuth callback."""

    auth_code: Optional[str] = None
    error: Optional[str] = None

    def do_GET(self):
        """Handle GET request from OAuth callback."""
        parsed = urllib.parse.urlparse(self.path)

        if parsed.path != CALLBACK_PATH:
            self.send_response(404)
            self.end_headers()
            return

        params = urllib.parse.parse_qs(parsed.query)

        if "code" in params:
            OAuthCallbackHandler.auth_code = params["code"][0]
            self.send_response(200)
            self.send_header("Content-type", "text/html")
            self.end_headers()
            self.wfile.write(b"""
                <html><body style="font-family: sans-serif; text-align: center; padding: 50px;">
                <h1>Authorization Successful!</h1>
                <p>You can close this window and return to the terminal.</p>
                </body></html>
            """)
        elif "error" in params:
            OAuthCallbackHandler.error = params.get("error_description", params["error"])[0]
            self.send_response(400)
            self.send_header("Content-type", "text/html")
            self.end_headers()
            self.wfile.write(f"""
                <html><body style="font-family: sans-serif; text-align: center; padding: 50px;">
                <h1>Authorization Failed</h1>
                <p>{OAuthCallbackHandler.error}</p>
                </body></html>
            """.encode())
        else:
            self.send_response(400)
            self.end_headers()

    def log_message(self, format, *args):
        """Suppress HTTP logging."""
        pass


def load_credentials() -> Optional[Dict[str, str]]:
    """Load saved credentials if they exist."""
    if CREDENTIALS_FILE.exists():
        try:
            with open(CREDENTIALS_FILE) as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            pass
    return None


def save_credentials(client_id: str, client_secret: str):
    """Save credentials for future use."""
    CREDENTIALS_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(CREDENTIALS_FILE, "w") as f:
        json.dump({"client_id": client_id, "client_secret": client_secret}, f, indent=2)
    os.chmod(CREDENTIALS_FILE, 0o600)
    print(f"Credentials saved to {CREDENTIALS_FILE}")


def get_credentials() -> tuple[str, str]:
    """Get OAuth credentials from user or saved file."""
    saved = load_credentials()

    if saved:
        print(f"\nFound saved credentials (Client ID: {saved['client_id'][:8]}...)")
        use_saved = input("Use saved credentials? [Y/n]: ").strip().lower()
        if use_saved != "n":
            return saved["client_id"], saved["client_secret"]

    print("\n" + "=" * 60)
    print("ASANA OAUTH SETUP")
    print("=" * 60)
    print("\nFirst, create an Asana app if you haven't already:")
    print("  1. Go to https://app.asana.com/0/my-apps")
    print("  2. Click 'Create new app'")
    print("  3. Name it (e.g., 'CLI Tool')")
    print(f"  4. Add redirect URL: {REDIRECT_URI}")
    print("  5. Copy your Client ID and Client Secret")
    print()

    client_id = input("Client ID: ").strip()
    if not client_id:
        print("Error: Client ID is required")
        sys.exit(1)

    client_secret = input("Client Secret: ").strip()
    if not client_secret:
        print("Error: Client Secret is required")
        sys.exit(1)

    save_creds = input("\nSave credentials for future use? [Y/n]: ").strip().lower()
    if save_creds != "n":
        save_credentials(client_id, client_secret)

    return client_id, client_secret


def start_callback_server() -> socketserver.TCPServer:
    """Start local server to capture OAuth callback."""
    # Reset handler state
    OAuthCallbackHandler.auth_code = None
    OAuthCallbackHandler.error = None

    server = socketserver.TCPServer(("localhost", CALLBACK_PORT), OAuthCallbackHandler)
    server.timeout = 120  # 2 minute timeout

    thread = threading.Thread(target=server.handle_request)
    thread.daemon = True
    thread.start()

    return server


def build_auth_url(client_id: str, state: str) -> str:
    """Build Asana authorization URL."""
    params = {
        "client_id": client_id,
        "redirect_uri": REDIRECT_URI,
        "response_type": "code",
        "state": state,
    }
    return f"{ASANA_AUTH_URL}?{urllib.parse.urlencode(params)}"


def exchange_code_for_tokens(code: str, client_id: str, client_secret: str) -> Dict[str, Any]:
    """Exchange authorization code for access and refresh tokens."""
    data = urllib.parse.urlencode({
        "grant_type": "authorization_code",
        "client_id": client_id,
        "client_secret": client_secret,
        "redirect_uri": REDIRECT_URI,
        "code": code,
    }).encode()

    req = urllib.request.Request(
        ASANA_TOKEN_URL,
        data=data,
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )

    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.loads(resp.read())
    except urllib.error.HTTPError as e:
        error_body = e.read().decode()
        raise RuntimeError(f"Token exchange failed: {e.code} - {error_body}")


def save_tokens(tokens: Dict[str, Any], client_id: str, client_secret: str):
    """Save tokens to file with expiry timestamp."""
    TOKEN_FILE.parent.mkdir(parents=True, exist_ok=True)

    # Calculate absolute expiry time
    expires_in = tokens.get("expires_in", 3600)
    expires_at = time.time() + expires_in

    token_data = {
        "access_token": tokens["access_token"],
        "refresh_token": tokens.get("refresh_token"),
        "token_type": tokens.get("token_type", "bearer"),
        "expires_at": expires_at,
        "expires_in": expires_in,
        "client_id": client_id,
        "client_secret": client_secret,
        "created_at": time.time(),
    }

    with open(TOKEN_FILE, "w") as f:
        json.dump(token_data, f, indent=2)

    # Secure the token file
    os.chmod(TOKEN_FILE, 0o600)

    print(f"\nTokens saved to {TOKEN_FILE}")


def verify_token(access_token: str) -> Dict[str, Any]:
    """Verify token by fetching user info."""
    req = urllib.request.Request(
        "https://app.asana.com/api/1.0/users/me",
        headers={"Authorization": f"Bearer {access_token}"},
    )

    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read())


def main():
    """Run OAuth setup flow."""
    print("\n" + "=" * 60)
    print("ASANA OAUTH AUTHENTICATION")
    print("=" * 60)

    # Get credentials
    client_id, client_secret = get_credentials()

    # Generate state for CSRF protection
    state = secrets.token_urlsafe(32)

    # Start callback server
    print("\nStarting local callback server...")
    server = start_callback_server()

    # Build and open auth URL
    auth_url = build_auth_url(client_id, state)
    print(f"\nOpening browser for authorization...")
    print(f"If browser doesn't open, visit:\n{auth_url}\n")
    webbrowser.open(auth_url)

    # Wait for callback
    print("Waiting for authorization (2 minute timeout)...")
    timeout = 120
    start = time.time()

    while time.time() - start < timeout:
        if OAuthCallbackHandler.auth_code or OAuthCallbackHandler.error:
            break
        time.sleep(0.5)

    server.server_close()

    if OAuthCallbackHandler.error:
        print(f"\nAuthorization failed: {OAuthCallbackHandler.error}")
        sys.exit(1)

    if not OAuthCallbackHandler.auth_code:
        print("\nTimeout waiting for authorization.")
        sys.exit(1)

    # Exchange code for tokens
    print("\nExchanging authorization code for tokens...")
    try:
        tokens = exchange_code_for_tokens(
            OAuthCallbackHandler.auth_code,
            client_id,
            client_secret
        )
    except Exception as e:
        print(f"\nFailed to exchange code: {e}")
        sys.exit(1)

    # Save tokens
    save_tokens(tokens, client_id, client_secret)

    # Verify by fetching user info
    print("\nVerifying authentication...")
    try:
        user_data = verify_token(tokens["access_token"])
        user = user_data.get("data", {})
        print(f"\nAuthenticated as: {user.get('name')} ({user.get('email')})")

        workspaces = user.get("workspaces", [])
        if workspaces:
            print(f"Workspaces: {', '.join(w['name'] for w in workspaces)}")
    except Exception as e:
        print(f"Warning: Could not verify token: {e}")

    print("\n" + "=" * 60)
    print("SETUP COMPLETE!")
    print("=" * 60)
    print("\nYou can now use the Asana client:")
    print("  python3 asana_client.py workspaces")
    print("  python3 asana_client.py my-tasks")
    print()


if __name__ == "__main__":
    main()
