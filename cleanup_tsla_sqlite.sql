-- SQLite cleanup for tsla project
-- Run with: sqlite3 ~/Library/Application\ Support/com.crucible.app/claude_code_scaffold.db < cleanup_tsla_sqlite.sql

-- First, clean up the FTS index directly for this project
DELETE FROM fts_session_content WHERE project_id = '187868e5-6fa5-41ca-a301-94ad5a1d36eb';

-- Drop the triggers temporarily to avoid FTS virtual table errors
DROP TRIGGER IF EXISTS fts_session_events_delete;
DROP TRIGGER IF EXISTS fts_session_subtasks_delete;
DROP TRIGGER IF EXISTS fts_session_objectives_delete;

-- Now delete the data
DELETE FROM session_events WHERE session_id IN (SELECT id FROM sessions WHERE project_id = '187868e5-6fa5-41ca-a301-94ad5a1d36eb');
DELETE FROM session_analysis WHERE session_id IN (SELECT id FROM sessions WHERE project_id = '187868e5-6fa5-41ca-a301-94ad5a1d36eb');
DELETE FROM session_objectives WHERE session_id IN (SELECT id FROM sessions WHERE project_id = '187868e5-6fa5-41ca-a301-94ad5a1d36eb');
DELETE FROM session_subtasks WHERE session_id IN (SELECT id FROM sessions WHERE project_id = '187868e5-6fa5-41ca-a301-94ad5a1d36eb');
DELETE FROM session_messages WHERE session_id IN (SELECT id FROM sessions WHERE project_id = '187868e5-6fa5-41ca-a301-94ad5a1d36eb');
DELETE FROM sessions WHERE project_id = '187868e5-6fa5-41ca-a301-94ad5a1d36eb';
DELETE FROM projects WHERE id = '187868e5-6fa5-41ca-a301-94ad5a1d36eb';

-- Recreate the triggers
CREATE TRIGGER fts_session_events_delete
  AFTER DELETE ON session_events
  WHEN OLD.event_type IN ('user', 'agent')
  BEGIN
      DELETE FROM fts_session_content
      WHERE rowid IN (
          SELECT rowid FROM fts_session_content
          WHERE content_type = 'message'
          AND session_id = OLD.session_id
          AND content = OLD.message
          LIMIT 1
      );
  END;

CREATE TRIGGER fts_session_subtasks_delete
  AFTER DELETE ON session_subtasks
  BEGIN
      DELETE FROM fts_session_content
      WHERE rowid IN (
          SELECT rowid FROM fts_session_content
          WHERE content_type = 'subtask'
          AND session_id = OLD.session_id
          AND content = OLD.title
          LIMIT 1
      );
  END;

CREATE TRIGGER fts_session_objectives_delete
  AFTER DELETE ON session_objectives
  BEGIN
      DELETE FROM fts_session_content
      WHERE rowid IN (
          SELECT rowid FROM fts_session_content
          WHERE content_type = 'objective'
          AND session_id = OLD.session_id
          AND content = OLD.main_objective
          LIMIT 1
      );
  END;

SELECT 'SQLite cleanup complete';
