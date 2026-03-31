CREATE TABLE IF NOT EXISTS presence_heartbeats (
  id TEXT PRIMARY KEY,
  agent_id TEXT NOT NULL,
  runtime_id TEXT,
  presence TEXT NOT NULL CHECK (presence IN ('online', 'offline', 'busy', 'unknown')),
  heartbeat_at TEXT NOT NULL,
  details_json TEXT,
  created_at TEXT NOT NULL,
  FOREIGN KEY (agent_id) REFERENCES agents(id),
  FOREIGN KEY (runtime_id) REFERENCES agent_runtimes(id)
);

CREATE TABLE IF NOT EXISTS relay_edges (
  id TEXT PRIMARY KEY,
  session_id TEXT NOT NULL,
  source_message_id TEXT,
  source_job_id TEXT,
  target_agent_id TEXT NOT NULL,
  target_job_id TEXT,
  relay_reason TEXT NOT NULL CHECK (
    relay_reason IN ('mention', 'policy_auto_relay', 'manual_relay')
  ),
  hop_number INTEGER NOT NULL,
  created_at TEXT NOT NULL,
  FOREIGN KEY (session_id) REFERENCES sessions(id),
  FOREIGN KEY (source_message_id) REFERENCES messages(id),
  FOREIGN KEY (source_job_id) REFERENCES jobs(id),
  FOREIGN KEY (target_agent_id) REFERENCES agents(id),
  FOREIGN KEY (target_job_id) REFERENCES jobs(id)
);

CREATE TABLE IF NOT EXISTS session_events (
  id TEXT PRIMARY KEY,
  session_id TEXT NOT NULL,
  event_type TEXT NOT NULL,
  actor_type TEXT,
  actor_id TEXT,
  event_payload_json TEXT,
  created_at TEXT NOT NULL,
  FOREIGN KEY (session_id) REFERENCES sessions(id)
);

CREATE INDEX IF NOT EXISTS idx_presence_heartbeats_agent_id_heartbeat_at
  ON presence_heartbeats(agent_id, heartbeat_at);

CREATE INDEX IF NOT EXISTS idx_presence_heartbeats_runtime_id_heartbeat_at
  ON presence_heartbeats(runtime_id, heartbeat_at);

CREATE INDEX IF NOT EXISTS idx_relay_edges_session_id_created_at
  ON relay_edges(session_id, created_at);

CREATE INDEX IF NOT EXISTS idx_relay_edges_source_job_id
  ON relay_edges(source_job_id);

CREATE INDEX IF NOT EXISTS idx_relay_edges_target_agent_id
  ON relay_edges(target_agent_id);

CREATE INDEX IF NOT EXISTS idx_session_events_session_id_created_at
  ON session_events(session_id, created_at);

CREATE INDEX IF NOT EXISTS idx_session_events_event_type
  ON session_events(event_type);
