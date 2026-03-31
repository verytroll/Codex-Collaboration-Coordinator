CREATE TABLE phases (
  id TEXT PRIMARY KEY,
  session_id TEXT NOT NULL,
  phase_key TEXT NOT NULL,
  title TEXT NOT NULL,
  description TEXT,
  relay_template_key TEXT NOT NULL,
  default_channel_key TEXT NOT NULL,
  sort_order INTEGER NOT NULL,
  is_default INTEGER NOT NULL DEFAULT 0,
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL,
  FOREIGN KEY (session_id) REFERENCES sessions(id),
  UNIQUE (session_id, phase_key)
);

CREATE INDEX idx_phases_session_id_sort_order
  ON phases(session_id, sort_order, created_at, id);

CREATE INDEX idx_phases_session_id_is_default
  ON phases(session_id, is_default, sort_order, created_at, id);
