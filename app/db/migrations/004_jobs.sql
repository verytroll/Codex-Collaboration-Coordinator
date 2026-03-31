CREATE TABLE IF NOT EXISTS jobs (
  id TEXT PRIMARY KEY,
  session_id TEXT NOT NULL,
  assigned_agent_id TEXT NOT NULL,
  runtime_id TEXT,
  source_message_id TEXT,
  parent_job_id TEXT,
  title TEXT NOT NULL,
  instructions TEXT,
  status TEXT NOT NULL CHECK (
    status IN (
      'queued',
      'running',
      'input_required',
      'auth_required',
      'completed',
      'failed',
      'canceled',
      'paused_by_loop_guard'
    )
  ),
  hop_count INTEGER NOT NULL DEFAULT 0,
  priority TEXT NOT NULL DEFAULT 'normal' CHECK (priority IN ('low', 'normal', 'high')),
  codex_runtime_id TEXT,
  codex_thread_id TEXT,
  active_turn_id TEXT,
  last_known_turn_status TEXT,
  result_summary TEXT,
  error_code TEXT,
  error_message TEXT,
  started_at TEXT,
  completed_at TEXT,
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL,
  FOREIGN KEY (session_id) REFERENCES sessions(id),
  FOREIGN KEY (assigned_agent_id) REFERENCES agents(id),
  FOREIGN KEY (runtime_id) REFERENCES agent_runtimes(id),
  FOREIGN KEY (source_message_id) REFERENCES messages(id),
  FOREIGN KEY (parent_job_id) REFERENCES jobs(id)
);

CREATE TABLE IF NOT EXISTS job_events (
  id TEXT PRIMARY KEY,
  job_id TEXT NOT NULL,
  session_id TEXT NOT NULL,
  event_type TEXT NOT NULL,
  event_payload_json TEXT,
  created_at TEXT NOT NULL,
  FOREIGN KEY (job_id) REFERENCES jobs(id),
  FOREIGN KEY (session_id) REFERENCES sessions(id)
);

CREATE TABLE IF NOT EXISTS artifacts (
  id TEXT PRIMARY KEY,
  job_id TEXT NOT NULL,
  session_id TEXT NOT NULL,
  source_message_id TEXT,
  artifact_type TEXT NOT NULL CHECK (
    artifact_type IN ('final_text', 'diff', 'file', 'json', 'log_excerpt')
  ),
  title TEXT NOT NULL,
  content_text TEXT,
  file_path TEXT,
  file_name TEXT,
  mime_type TEXT,
  size_bytes INTEGER,
  checksum_sha256 TEXT,
  metadata_json TEXT,
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL,
  FOREIGN KEY (job_id) REFERENCES jobs(id),
  FOREIGN KEY (session_id) REFERENCES sessions(id),
  FOREIGN KEY (source_message_id) REFERENCES messages(id)
);

CREATE TABLE IF NOT EXISTS approval_requests (
  id TEXT PRIMARY KEY,
  job_id TEXT NOT NULL,
  agent_id TEXT NOT NULL,
  approval_type TEXT NOT NULL CHECK (
    approval_type IN ('command_execution', 'file_change', 'network_access', 'custom')
  ),
  status TEXT NOT NULL CHECK (status IN ('pending', 'accepted', 'declined', 'canceled')),
  request_payload_json TEXT NOT NULL,
  decision_payload_json TEXT,
  requested_at TEXT NOT NULL,
  resolved_at TEXT,
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL,
  FOREIGN KEY (job_id) REFERENCES jobs(id),
  FOREIGN KEY (agent_id) REFERENCES agents(id)
);

CREATE INDEX IF NOT EXISTS idx_jobs_session_id
  ON jobs(session_id);

CREATE INDEX IF NOT EXISTS idx_jobs_assigned_agent_id
  ON jobs(assigned_agent_id);

CREATE INDEX IF NOT EXISTS idx_jobs_status
  ON jobs(status);

CREATE INDEX IF NOT EXISTS idx_jobs_source_message_id
  ON jobs(source_message_id);

CREATE INDEX IF NOT EXISTS idx_jobs_parent_job_id
  ON jobs(parent_job_id);

CREATE INDEX IF NOT EXISTS idx_jobs_codex_thread_id
  ON jobs(codex_thread_id);

CREATE INDEX IF NOT EXISTS idx_job_events_job_id_created_at
  ON job_events(job_id, created_at);

CREATE INDEX IF NOT EXISTS idx_job_events_session_id_created_at
  ON job_events(session_id, created_at);

CREATE INDEX IF NOT EXISTS idx_job_events_event_type
  ON job_events(event_type);

CREATE INDEX IF NOT EXISTS idx_artifacts_job_id
  ON artifacts(job_id);

CREATE INDEX IF NOT EXISTS idx_artifacts_session_id
  ON artifacts(session_id);

CREATE INDEX IF NOT EXISTS idx_artifacts_artifact_type
  ON artifacts(artifact_type);

CREATE INDEX IF NOT EXISTS idx_approval_requests_job_id
  ON approval_requests(job_id);

CREATE INDEX IF NOT EXISTS idx_approval_requests_agent_id
  ON approval_requests(agent_id);

CREATE INDEX IF NOT EXISTS idx_approval_requests_status
  ON approval_requests(status);
