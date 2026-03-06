"""Letta tool for safe parameterized PostgreSQL queries."""

import json
import os


def db_query(
    query: str,
    params: str = "[]",
    database: str = "",
    max_rows: int = 100,
    timeout: int = 30,
) -> str:
    """Execute a parameterized read-only SQL query against PostgreSQL.

    Connects to the configured PostgreSQL database and runs the given query
    with parameterized values. Only SELECT queries are allowed for safety.
    Results are returned as a JSON array of row objects.

    Args:
        query: SQL SELECT query with %s placeholders for parameters.
            Example: "SELECT * FROM projects WHERE name = %s"
        params: JSON array string of parameter values to bind.
            Example: '["claude-code-scaffold"]'. Defaults to "[]".
        database: Database name to connect to. Defaults to the DATABASE_URL
            environment variable, or "claude_code_scaffold" if not set.
        max_rows: Maximum number of rows to return. Defaults to 100.
        timeout: Statement timeout in seconds. Defaults to 30.

    Returns:
        JSON string with query results as an array of row objects, or an
        error message string on failure.
    """
    try:
        import psycopg2
        import psycopg2.extras
    except ImportError:
        return "Error: psycopg2 package not installed. pip install psycopg2-binary"

    # Safety: only allow SELECT/WITH queries
    stripped = query.strip().upper()
    if not (stripped.startswith("SELECT") or stripped.startswith("WITH")):
        return (
            "Error: Only SELECT and WITH queries are allowed. "
            "This tool is read-only for safety."
        )

    # Dangerous statement patterns
    dangerous = [
        "INSERT ",
        "UPDATE ",
        "DELETE ",
        "DROP ",
        "ALTER ",
        "TRUNCATE ",
        "CREATE ",
        "GRANT ",
        "REVOKE ",
        "EXEC ",
    ]
    for keyword in dangerous:
        if keyword in stripped:
            return f"Error: Query contains forbidden keyword '{keyword.strip()}'. Read-only queries only."

    # Parse parameters
    try:
        param_list = json.loads(params) if params.strip() else []
    except json.JSONDecodeError as e:
        return f"Error parsing params JSON: {e}"

    if not isinstance(param_list, list):
        return "Error: params must be a JSON array (e.g. '[\"value1\", 42]')."

    # Build connection string
    database_url = os.environ.get("DATABASE_URL", "")

    if database_url:
        dsn = database_url
        if database and database not in database_url:
            # Override database name in the URL
            dsn = _replace_dbname(database_url, database)
    else:
        # Fall back to individual env vars
        host = os.environ.get("DB_HOST", "localhost")
        port = os.environ.get("DB_PORT", "5432")
        user = os.environ.get("DB_USER", "crucible_admin")
        password = os.environ.get("DB_PASSWORD", "")
        dbname = database or "claude_code_scaffold"

        dsn = f"host={host} port={port} dbname={dbname} user={user}"
        if password:
            dsn += f" password={password}"

        sslmode = os.environ.get("DB_SSLMODE", "require")
        dsn += f" sslmode={sslmode}"

    conn = None
    try:
        conn = psycopg2.connect(dsn, connect_timeout=10)
        conn.set_session(readonly=True, autocommit=True)

        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(f"SET statement_timeout = '{timeout}s'")
            cur.execute(query, tuple(param_list) if param_list else None)
            rows = cur.fetchmany(max_rows)

        # Convert to serializable dicts
        results = []
        for row in rows:
            results.append({k: _serialize_value(v) for k, v in dict(row).items()})

        total_info = ""
        if len(results) == max_rows:
            total_info = f" (limited to {max_rows} rows)"

        return json.dumps(
            {"rows": results, "count": len(results), "note": total_info.strip()},
            indent=2,
            default=str,
        )

    except psycopg2.OperationalError as e:
        return f"Error: Database connection failed: {e}"
    except psycopg2.errors.QueryCanceled:
        return f"Error: Query timed out after {timeout} seconds."
    except psycopg2.Error as e:
        return f"Error executing query: {e}"
    except Exception as e:
        return f"Error: {e}"
    finally:
        if conn:
            conn.close()


def _serialize_value(v: object) -> object:
    """Convert non-JSON-serializable values to strings."""
    from datetime import date, datetime
    from decimal import Decimal
    from uuid import UUID

    if v is None or isinstance(v, (str, int, float, bool)):
        return v
    if isinstance(v, datetime):
        return v.isoformat()
    if isinstance(v, date):
        return v.isoformat()
    if isinstance(v, Decimal):
        return float(v)
    if isinstance(v, UUID):
        return str(v)
    if isinstance(v, (list, dict)):
        return v
    return str(v)


def _replace_dbname(url: str, new_dbname: str) -> str:
    """Replace the database name in a PostgreSQL connection URL."""
    # postgresql://user:pass@host:port/dbname?params
    if "/" in url.split("@")[-1]:
        base, rest = url.rsplit("/", 1)
        if "?" in rest:
            _, params = rest.split("?", 1)
            return f"{base}/{new_dbname}?{params}"
        return f"{base}/{new_dbname}"
    return url + f"/{new_dbname}"
