CREATE TABLE IF NOT EXISTS session_channels (
  id TEXT PRIMARY KEY,
  session_id TEXT NOT NULL,
  channel_key TEXT NOT NULL,
  display_name TEXT NOT NULL,
  description TEXT,
  is_default INTEGER NOT NULL DEFAULT 0,
  sort_order INTEGER NOT NULL DEFAULT 0,
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL,
  UNIQUE (session_id, channel_key),
  FOREIGN KEY (session_id) REFERENCES sessions(id)
);

CREATE TABLE IF NOT EXISTS session_channel_views (
  id TEXT PRIMARY KEY,
  session_id TEXT NOT NULL,
  channel_id TEXT NOT NULL,
  view_key TEXT NOT NULL,
  view_name TEXT NOT NULL,
  description TEXT,
  is_default INTEGER NOT NULL DEFAULT 0,
  sort_order INTEGER NOT NULL DEFAULT 0,
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL,
  UNIQUE (session_id, view_key),
  FOREIGN KEY (session_id) REFERENCES sessions(id),
  FOREIGN KEY (channel_id) REFERENCES session_channels(id)
);

ALTER TABLE messages ADD COLUMN channel_key TEXT NOT NULL DEFAULT 'general';
ALTER TABLE jobs ADD COLUMN channel_key TEXT NOT NULL DEFAULT 'general';
ALTER TABLE artifacts ADD COLUMN channel_key TEXT NOT NULL DEFAULT 'general';

CREATE INDEX IF NOT EXISTS idx_session_channels_session_id_sort_order
  ON session_channels(session_id, sort_order, created_at, id);

CREATE INDEX IF NOT EXISTS idx_session_channels_session_id_channel_key
  ON session_channels(session_id, channel_key);

CREATE INDEX IF NOT EXISTS idx_session_channel_views_session_id_sort_order
  ON session_channel_views(session_id, sort_order, created_at, id);

CREATE INDEX IF NOT EXISTS idx_session_channel_views_session_id_view_key
  ON session_channel_views(session_id, view_key);

CREATE INDEX IF NOT EXISTS idx_messages_session_id_channel_key_created_at
  ON messages(session_id, channel_key, created_at);

CREATE INDEX IF NOT EXISTS idx_jobs_session_id_channel_key
  ON jobs(session_id, channel_key);

CREATE INDEX IF NOT EXISTS idx_artifacts_session_id_channel_key
  ON artifacts(session_id, channel_key);
