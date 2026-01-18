#!/bin/bash
# Cleanup script for tsla project
# This removes the redundant tsla directory and cleans up database entries
# The financial/tesla-financial-explorer project supersedes this one

set -e

TSLA_PATH="/Users/moskov/Code/tsla"
TSLA_PROJECT_ID="187868e5-6fa5-41ca-a301-94ad5a1d36eb"
SQLITE_DB="$HOME/Library/Application Support/com.crucible.app/claude_code_scaffold.db"
POSTGRES_CONN="postgresql://crucible_admin:UbK89O3uuDVB2Yowd9ev1cN4eTXQvGXX@localhost:5433/claude_code_scaffold"

echo "=========================================="
echo "TSLA Project Cleanup Script"
echo "=========================================="
echo ""
echo "This script will:"
echo "  1. Remove tsla project from PostgreSQL (prod)"
echo "  2. Remove tsla project from SQLite (local)"
echo "  3. Delete the tsla directory"
echo ""
echo "Project ID: $TSLA_PROJECT_ID"
echo "Path: $TSLA_PATH"
echo ""

# Check if SSH tunnel is active for PostgreSQL
echo "Checking PostgreSQL connection..."
if ! psql "$POSTGRES_CONN" -c "SELECT 1" > /dev/null 2>&1; then
    echo "ERROR: Cannot connect to PostgreSQL."
    echo "Please ensure SSH tunnel is active:"
    echo "  ssh -N -L 5433:crucible-scaffold-db.cf2c6g8ccmbp.us-west-1.rds.amazonaws.com:5432 -i ~/.ssh/crucible-bastion ec2-user@54.177.62.161"
    exit 1
fi
echo "PostgreSQL connection OK"

# Check if directory exists
if [ ! -d "$TSLA_PATH" ]; then
    echo "WARNING: Directory $TSLA_PATH does not exist"
fi

echo ""
read -p "Are you sure you want to proceed? (y/N) " -n 1 -r
echo ""

if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "Aborted."
    exit 0
fi

echo ""
echo "Step 1: Removing from PostgreSQL..."
echo "----------------------------------------"

# Delete related records in order (respecting foreign keys)
psql "$POSTGRES_CONN" <<EOF
BEGIN;

-- Show what will be deleted
SELECT 'Sessions to delete: ' || COUNT(*) FROM sessions WHERE project_id = '$TSLA_PROJECT_ID';
SELECT 'Session analyses to delete: ' || COUNT(*) FROM session_analysis WHERE session_id IN (SELECT id FROM sessions WHERE project_id = '$TSLA_PROJECT_ID');
SELECT 'Session events to delete: ' || COUNT(*) FROM session_events WHERE session_id IN (SELECT id FROM sessions WHERE project_id = '$TSLA_PROJECT_ID');

-- Delete in proper order (child tables first)
DELETE FROM session_events WHERE session_id IN (SELECT id FROM sessions WHERE project_id = '$TSLA_PROJECT_ID');
DELETE FROM session_analysis WHERE session_id IN (SELECT id FROM sessions WHERE project_id = '$TSLA_PROJECT_ID');
DELETE FROM session_objectives WHERE session_id IN (SELECT id FROM sessions WHERE project_id = '$TSLA_PROJECT_ID');
DELETE FROM session_messages WHERE session_id IN (SELECT id FROM sessions WHERE project_id = '$TSLA_PROJECT_ID');
DELETE FROM sessions WHERE project_id = '$TSLA_PROJECT_ID';
DELETE FROM projects WHERE id = '$TSLA_PROJECT_ID';

COMMIT;
EOF

echo "PostgreSQL cleanup complete."

echo ""
echo "Step 2: Removing from SQLite..."
echo "----------------------------------------"

sqlite3 "$SQLITE_DB" <<EOF
BEGIN;

-- Show what will be deleted
SELECT 'Sessions to delete: ' || COUNT(*) FROM sessions WHERE project_id = '$TSLA_PROJECT_ID';

-- Delete in proper order
DELETE FROM session_events WHERE session_id IN (SELECT id FROM sessions WHERE project_id = '$TSLA_PROJECT_ID');
DELETE FROM session_analysis WHERE session_id IN (SELECT id FROM sessions WHERE project_id = '$TSLA_PROJECT_ID');
DELETE FROM session_objectives WHERE session_id IN (SELECT id FROM sessions WHERE project_id = '$TSLA_PROJECT_ID');
DELETE FROM session_messages WHERE session_id IN (SELECT id FROM sessions WHERE project_id = '$TSLA_PROJECT_ID');
DELETE FROM sessions WHERE project_id = '$TSLA_PROJECT_ID';
DELETE FROM projects WHERE id = '$TSLA_PROJECT_ID';

COMMIT;
EOF

echo "SQLite cleanup complete."

echo ""
echo "Step 3: Removing directory..."
echo "----------------------------------------"

if [ -d "$TSLA_PATH" ]; then
    # Remove .git first to avoid any git hooks
    if [ -d "$TSLA_PATH/.git" ]; then
        rm -rf "$TSLA_PATH/.git"
    fi
    rm -rf "$TSLA_PATH"
    echo "Directory removed: $TSLA_PATH"
else
    echo "Directory already removed or doesn't exist"
fi

echo ""
echo "=========================================="
echo "Cleanup complete!"
echo "=========================================="
echo ""
echo "The tsla project has been removed."
echo "Use financial/tesla-financial-explorer for Tesla financial analysis."
