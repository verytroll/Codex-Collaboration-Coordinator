CREATE TABLE IF NOT EXISTS orchestration_runs (
  id TEXT PRIMARY KEY,
  session_id TEXT NOT NULL UNIQUE,
  status TEXT NOT NULL CHECK (status IN ('active', 'blocked', 'completed')),
  current_phase_id TEXT,
  current_phase_key TEXT NOT NULL,
  pending_phase_key TEXT,
  failure_phase_key TEXT NOT NULL DEFAULT 'revise',
  gate_type TEXT CHECK (
    gate_type IN ('review_required', 'approval_required', 'revise_on_reject')
  ),
  gate_status TEXT NOT NULL CHECK (gate_status IN ('idle', 'pending', 'approved', 'rejected')),
  source_job_id TEXT,
  handoff_job_id TEXT,
  review_id TEXT,
  approval_id TEXT,
  transition_artifact_id TEXT,
  decision_artifact_id TEXT,
  revision_job_id TEXT,
  requested_by_agent_id TEXT,
  transition_reason TEXT,
  started_at TEXT NOT NULL,
  decided_at TEXT,
  completed_at TEXT,
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL,
  FOREIGN KEY (session_id) REFERENCES sessions(id),
  FOREIGN KEY (current_phase_id) REFERENCES phases(id),
  FOREIGN KEY (source_job_id) REFERENCES jobs(id),
  FOREIGN KEY (handoff_job_id) REFERENCES jobs(id),
  FOREIGN KEY (review_id) REFERENCES session_reviews(id),
  FOREIGN KEY (approval_id) REFERENCES approval_requests(id),
  FOREIGN KEY (transition_artifact_id) REFERENCES artifacts(id),
  FOREIGN KEY (decision_artifact_id) REFERENCES artifacts(id),
  FOREIGN KEY (revision_job_id) REFERENCES jobs(id),
  FOREIGN KEY (requested_by_agent_id) REFERENCES agents(id)
);

CREATE INDEX IF NOT EXISTS idx_orchestration_runs_session_id
  ON orchestration_runs(session_id, created_at, id);

CREATE INDEX IF NOT EXISTS idx_orchestration_runs_gate_status
  ON orchestration_runs(gate_status, status, created_at, id);

CREATE INDEX IF NOT EXISTS idx_orchestration_runs_gate_type
  ON orchestration_runs(gate_type, created_at, id);

CREATE INDEX IF NOT EXISTS idx_orchestration_runs_review_id
  ON orchestration_runs(review_id);

CREATE INDEX IF NOT EXISTS idx_orchestration_runs_approval_id
  ON orchestration_runs(approval_id);
