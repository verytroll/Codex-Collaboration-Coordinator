CREATE TABLE IF NOT EXISTS job_inputs (
  id TEXT PRIMARY KEY,
  job_id TEXT NOT NULL,
  session_id TEXT NOT NULL,
  input_type TEXT NOT NULL,
  input_payload_json TEXT,
  created_at TEXT NOT NULL,
  FOREIGN KEY (job_id) REFERENCES jobs(id),
  FOREIGN KEY (session_id) REFERENCES sessions(id)
);

CREATE INDEX IF NOT EXISTS idx_job_inputs_job_id_created_at
  ON job_inputs(job_id, created_at);

CREATE INDEX IF NOT EXISTS idx_job_inputs_session_id_created_at
  ON job_inputs(session_id, created_at);

CREATE INDEX IF NOT EXISTS idx_jobs_assigned_agent_id_status
  ON jobs(assigned_agent_id, status);
