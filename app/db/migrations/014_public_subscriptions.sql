CREATE TABLE a2a_public_subscriptions (
  id TEXT PRIMARY KEY,
  task_id TEXT NOT NULL,
  session_id TEXT NOT NULL,
  cursor_sequence INTEGER NOT NULL DEFAULT 0,
  delivery_mode TEXT NOT NULL DEFAULT 'sse',
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL,
  FOREIGN KEY (task_id) REFERENCES a2a_tasks(task_id),
  FOREIGN KEY (session_id) REFERENCES sessions(id)
);

CREATE TABLE a2a_public_events (
  id TEXT PRIMARY KEY,
  task_id TEXT NOT NULL,
  session_id TEXT NOT NULL,
  sequence INTEGER NOT NULL,
  event_type TEXT NOT NULL,
  event_payload_json TEXT NOT NULL,
  created_at TEXT NOT NULL,
  FOREIGN KEY (task_id) REFERENCES a2a_tasks(task_id),
  FOREIGN KEY (session_id) REFERENCES sessions(id),
  UNIQUE (task_id, sequence)
);

CREATE INDEX idx_a2a_public_subscriptions_task_id
  ON a2a_public_subscriptions(task_id, created_at, id);

CREATE INDEX idx_a2a_public_subscriptions_cursor_sequence
  ON a2a_public_subscriptions(cursor_sequence, created_at, id);

CREATE INDEX idx_a2a_public_events_task_id_sequence
  ON a2a_public_events(task_id, sequence, created_at, id);

CREATE INDEX idx_a2a_public_events_event_type
  ON a2a_public_events(event_type, created_at, id);
