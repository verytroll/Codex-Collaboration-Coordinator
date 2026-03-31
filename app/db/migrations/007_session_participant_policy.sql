ALTER TABLE session_participants ADD COLUMN role TEXT NOT NULL DEFAULT 'builder';
ALTER TABLE session_participants ADD COLUMN policy_json TEXT;

CREATE INDEX IF NOT EXISTS idx_session_participants_session_id_role
  ON session_participants(session_id, role);
