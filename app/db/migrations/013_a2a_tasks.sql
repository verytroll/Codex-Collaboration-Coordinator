CREATE TABLE a2a_tasks (
  id TEXT PRIMARY KEY,
  session_id TEXT NOT NULL,
  job_id TEXT NOT NULL UNIQUE,
  phase_id TEXT,
  task_id TEXT NOT NULL UNIQUE,
  context_id TEXT NOT NULL,
  task_status TEXT NOT NULL,
  relay_template_key TEXT,
  primary_artifact_id TEXT,
  task_payload_json TEXT NOT NULL,
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL,
  FOREIGN KEY (session_id) REFERENCES sessions(id),
  FOREIGN KEY (job_id) REFERENCES jobs(id)
);

CREATE INDEX idx_a2a_tasks_session_id
  ON a2a_tasks(session_id, created_at, id);

CREATE INDEX idx_a2a_tasks_task_id
  ON a2a_tasks(task_id);

CREATE INDEX idx_a2a_tasks_context_id
  ON a2a_tasks(context_id, created_at, id);

CREATE INDEX idx_a2a_tasks_task_status
  ON a2a_tasks(task_status, updated_at, id);
