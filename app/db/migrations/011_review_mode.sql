CREATE TABLE IF NOT EXISTS session_reviews (
  id TEXT PRIMARY KEY,
  session_id TEXT NOT NULL,
  source_job_id TEXT NOT NULL,
  reviewer_agent_id TEXT NOT NULL,
  requested_by_agent_id TEXT,
  review_scope TEXT NOT NULL DEFAULT 'job' CHECK (review_scope IN ('job', 'session')),
  review_status TEXT NOT NULL CHECK (
    review_status IN ('requested', 'approved', 'changes_requested')
  ),
  review_channel_key TEXT NOT NULL DEFAULT 'review',
  template_key TEXT NOT NULL CHECK (
    template_key IN (
      'planner_to_builder',
      'builder_to_reviewer',
      'reviewer_to_builder_revise'
    )
  ),
  request_message_id TEXT,
  decision_message_id TEXT,
  summary_artifact_id TEXT,
  revision_job_id TEXT,
  request_payload_json TEXT,
  decision_payload_json TEXT,
  requested_at TEXT NOT NULL,
  decided_at TEXT,
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL,
  FOREIGN KEY (session_id) REFERENCES sessions(id),
  FOREIGN KEY (source_job_id) REFERENCES jobs(id),
  FOREIGN KEY (reviewer_agent_id) REFERENCES agents(id),
  FOREIGN KEY (requested_by_agent_id) REFERENCES agents(id),
  FOREIGN KEY (request_message_id) REFERENCES messages(id),
  FOREIGN KEY (decision_message_id) REFERENCES messages(id),
  FOREIGN KEY (summary_artifact_id) REFERENCES artifacts(id),
  FOREIGN KEY (revision_job_id) REFERENCES jobs(id)
);

CREATE INDEX IF NOT EXISTS idx_session_reviews_session_id_created_at
  ON session_reviews(session_id, created_at, id);

CREATE INDEX IF NOT EXISTS idx_session_reviews_source_job_id
  ON session_reviews(source_job_id);

CREATE INDEX IF NOT EXISTS idx_session_reviews_reviewer_agent_id
  ON session_reviews(reviewer_agent_id);

CREATE INDEX IF NOT EXISTS idx_session_reviews_review_status
  ON session_reviews(review_status);
