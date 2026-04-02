CREATE TABLE outbound_webhook_registrations (
  id TEXT PRIMARY KEY,
  task_id TEXT NOT NULL,
  session_id TEXT NOT NULL,
  target_url TEXT NOT NULL,
  signing_secret TEXT NOT NULL,
  signing_secret_prefix TEXT NOT NULL,
  status TEXT NOT NULL CHECK (status IN ('active', 'disabled')),
  description TEXT,
  last_attempt_at TEXT,
  last_success_at TEXT,
  last_failure_at TEXT,
  last_error_message TEXT,
  failure_count INTEGER NOT NULL DEFAULT 0,
  last_delivered_sequence INTEGER NOT NULL DEFAULT 0,
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL,
  FOREIGN KEY (task_id) REFERENCES a2a_tasks(task_id),
  FOREIGN KEY (session_id) REFERENCES sessions(id)
);

CREATE TABLE outbound_webhook_deliveries (
  id TEXT PRIMARY KEY,
  registration_id TEXT NOT NULL,
  task_id TEXT NOT NULL,
  session_id TEXT NOT NULL,
  event_id TEXT NOT NULL,
  event_sequence INTEGER NOT NULL,
  event_type TEXT NOT NULL,
  payload_json TEXT NOT NULL,
  status TEXT NOT NULL CHECK (status IN ('pending', 'retrying', 'delivered', 'failed')),
  attempt_count INTEGER NOT NULL DEFAULT 0,
  next_attempt_at TEXT NOT NULL,
  last_attempt_at TEXT,
  last_success_at TEXT,
  last_failure_at TEXT,
  last_response_status INTEGER,
  last_error_message TEXT,
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL,
  FOREIGN KEY (registration_id) REFERENCES outbound_webhook_registrations(id),
  FOREIGN KEY (task_id) REFERENCES a2a_tasks(task_id),
  FOREIGN KEY (session_id) REFERENCES sessions(id),
  UNIQUE (registration_id, event_id)
);

CREATE INDEX idx_outbound_webhook_registrations_task_id
  ON outbound_webhook_registrations(task_id, created_at, id);

CREATE INDEX idx_outbound_webhook_registrations_status
  ON outbound_webhook_registrations(status, updated_at, id);

CREATE INDEX idx_outbound_webhook_deliveries_registration_id
  ON outbound_webhook_deliveries(registration_id, event_sequence, created_at, id);

CREATE INDEX idx_outbound_webhook_deliveries_status_next_attempt
  ON outbound_webhook_deliveries(status, next_attempt_at, event_sequence, id);

CREATE INDEX idx_outbound_webhook_deliveries_task_id
  ON outbound_webhook_deliveries(task_id, event_sequence, created_at, id);
