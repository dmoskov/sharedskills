"""
Letta PostgreSQL client for Claude Code hooks.

Connects to the custom PostgreSQL-based memory system instead of Letta Cloud.
Uses SSH tunnel (localhost:5433) for local development.
"""

import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Optional

# Add the maintenance scripts to path for imports
SCAFFOLD_PATH = Path.home() / "Code" / "skof" / "claude-code-scaffold" / "scripts" / "maintenance"
sys.path.insert(0, str(SCAFFOLD_PATH))

# Try to import from the scaffold's memory system
try:
    from memory_database import (
        get_db_connection,
        get_agent_id,
        store_memory_db,
        search_memories_db,
        list_memories_db,
    )
    DB_AVAILABLE = True
except ImportError as e:
    DB_AVAILABLE = False
    IMPORT_ERROR = str(e)


class LettaClient:
    """
    PostgreSQL-based memory client for Claude Code hooks.

    Wraps the scaffold's memory_database functions to provide
    a similar interface to the Letta Cloud client.
    """

    CONFIG_FILE = Path.home() / ".claude" / "hooks" / "letta" / "config.json"
    DEFAULT_PROJECT = "claude-code-scaffold"
    DEFAULT_AGENT_TYPE = "project_assistant"

    def __init__(self, project: Optional[str] = None, agent_type: Optional[str] = None):
        """
        Initialize PostgreSQL memory client.

        Args:
            project: Project name (default: claude-code-scaffold)
            agent_type: Agent type (default: project_assistant)
        """
        if not DB_AVAILABLE:
            raise ImportError(
                f"Memory database modules not available: {IMPORT_ERROR}\n"
                f"Ensure {SCAFFOLD_PATH} exists and contains memory_database.py"
            )

        self._project = project or self._detect_project() or self.DEFAULT_PROJECT
        self._agent_type = agent_type or self.DEFAULT_AGENT_TYPE
        self._agent_id: Optional[str] = None
        self._conn = None

        # Ensure SSH tunnel is running for local development
        if not os.environ.get("AWS_EXECUTION_ENV") and not os.path.exists("/.dockerenv"):
            self._ensure_tunnel()

    def _detect_project(self) -> Optional[str]:
        """Detect project from current working directory."""
        cwd = Path.cwd()
        # Look for common project indicators
        if (cwd / "CLAUDE.md").exists():
            return cwd.name
        # Check parent directories
        for parent in cwd.parents:
            if (parent / "CLAUDE.md").exists():
                return parent.name
        return None

    def _ensure_tunnel(self) -> None:
        """Ensure SSH tunnel is running on port 5433."""
        import socket
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            result = sock.connect_ex(('localhost', 5433))
            sock.close()
            if result != 0:
                # Tunnel not running, try to start it
                print("<!-- Starting SSH tunnel for database connection -->", file=sys.stderr)
                subprocess.run([
                    "ssh", "-fN",
                    "-L", "5433:crucible-scaffold-db.cf2c6g8ccmbp.us-west-1.rds.amazonaws.com:5432",
                    "-i", os.path.expanduser("~/.ssh/crucible-bastion"),
                    "ec2-user@54.177.62.161"
                ], check=False, capture_output=True)
                import time
                time.sleep(2)
        except Exception as e:
            print(f"<!-- Tunnel check failed: {e} -->", file=sys.stderr)

    def _get_password(self) -> str:
        """Get database password from AWS Secrets Manager or environment."""
        # Check environment first
        password = os.environ.get("PGPASSWORD") or os.environ.get("DB_PASSWORD")
        if password:
            return password

        # Try AWS Secrets Manager
        try:
            result = subprocess.run([
                "aws", "secretsmanager", "get-secret-value",
                "--secret-id", "crucible/scaffold/rds-credentials",
                "--region", "us-west-1",
                "--query", "SecretString",
                "--output", "text"
            ], capture_output=True, text=True, check=True)
            secret = json.loads(result.stdout)
            return secret.get("password", "")
        except Exception as e:
            print(f"<!-- Failed to get password from Secrets Manager: {e} -->", file=sys.stderr)
            return ""

    def _get_connection(self):
        """Get database connection, creating if needed."""
        if self._conn is None:
            # Set password in environment for the connection
            password = self._get_password()
            if password:
                os.environ["PGPASSWORD"] = password
            self._conn = get_db_connection()
        return self._conn

    @property
    def agent_id(self) -> str:
        """Get or derive agent ID."""
        if not self._agent_id:
            # get_agent_id(agent_type, project_id) returns "{agent_type}_{project_id}"
            self._agent_id = get_agent_id(self._agent_type, self._project)
        return self._agent_id

    def get_core_memory(self) -> dict:
        """
        Get core memory blocks (persona, human context).

        Returns:
            Dict with persona and human keys
        """
        try:
            # Ensure password is set
            self._get_password()
            # Query core blocks from letta_memory_blocks
            blocks = list_memories_db(self.agent_id, limit=10, block_type="core")
            result = {}
            for block in blocks:
                label = block.get("label", "")
                if label in ("persona", "human", "system"):
                    result[label] = block.get("content_preview", "")
            return result
        except Exception as e:
            print(f"<!-- Core memory fetch failed: {e} -->", file=sys.stderr)
            return {}

    def search_archival(self, query: str, limit: int = 10) -> list[dict]:
        """
        Search archival memory using semantic search.

        Args:
            query: Search query
            limit: Max results

        Returns:
            List of memory dicts with text and metadata
        """
        try:
            # Ensure password is set for the connection
            self._get_password()
            # search_memories_db creates its own connection
            results = search_memories_db(
                agent_id=self.agent_id,
                query=query,
                limit=limit
            )
            return [
                {
                    "id": str(r.get("id", "")),
                    "text": r.get("content", r.get("text", "")),
                    "label": r.get("label", ""),
                    "importance": r.get("importance", 0.5),
                }
                for r in results
            ]
        except Exception as e:
            print(f"<!-- Archival search failed: {e} -->", file=sys.stderr)
            return []

    def list_archival(self, limit: int = 100) -> list[dict]:
        """
        List archival memories by importance.

        Args:
            limit: Max results

        Returns:
            List of memory dicts
        """
        try:
            # Ensure password is set
            self._get_password()
            results = list_memories_db(self.agent_id, limit=limit, block_type="archival")
            return [
                {
                    "id": str(r.get("id", "")),
                    "text": r.get("content_preview", ""),
                    "label": r.get("label", ""),
                    "importance": r.get("importance", 0.5),
                }
                for r in results
            ]
        except Exception as e:
            print(f"<!-- Archival list failed: {e} -->", file=sys.stderr)
            return []

    def insert_archival(self, text: str, label: str = "learning", importance: float = 0.7) -> Optional[str]:
        """
        Insert memory into archival storage.

        Args:
            text: Memory content
            label: Memory label/category
            importance: Importance score (0-1)

        Returns:
            Memory ID if successful
        """
        try:
            # Ensure password is set for the connection
            self._get_password()
            # store_memory_db creates its own connection
            memory_id, action = store_memory_db(
                agent_id=self.agent_id,
                label=label,
                content=text,
                block_type="archival",
                importance=importance,
                project_id=self._project
            )
            return str(memory_id) if memory_id else None
        except Exception as e:
            print(f"<!-- Archival insert failed: {e} -->", file=sys.stderr)
            return None

    def get_persona(self) -> Optional[str]:
        """Get the agent's persona/system prompt."""
        try:
            # Check core memory for persona block
            core = self.get_core_memory()
            if core.get("persona"):
                return core["persona"]
            if core.get("system"):
                return core["system"]
            return None
        except Exception as e:
            print(f"<!-- Persona fetch failed: {e} -->", file=sys.stderr)
            return None

    def close(self):
        """Close database connection."""
        if self._conn:
            try:
                self._conn.close()
            except:
                pass
            self._conn = None
