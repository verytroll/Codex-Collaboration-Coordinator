ALTER TABLE sessions ADD COLUMN template_key TEXT;

CREATE TABLE IF NOT EXISTS policies (
  id TEXT PRIMARY KEY,
  session_id TEXT,
  template_key TEXT,
  phase_key TEXT,
  policy_type TEXT NOT NULL CHECK (
    policy_type IN (
      'conditional_auto_approve',
      'escalation',
      'template_scoped',
      'phase_scoped'
    )
  ),
  name TEXT NOT NULL,
  description TEXT,
  is_active INTEGER NOT NULL DEFAULT 1,
  automation_paused INTEGER NOT NULL DEFAULT 0,
  pause_reason TEXT,
  priority INTEGER NOT NULL DEFAULT 100,
  conditions_json TEXT,
  actions_json TEXT,
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL,
  FOREIGN KEY (session_id) REFERENCES sessions(id)
);

CREATE TABLE IF NOT EXISTS policy_decisions (
  id TEXT PRIMARY KEY,
  policy_id TEXT,
  session_id TEXT,
  subject_type TEXT NOT NULL CHECK (
    subject_type IN ('approval_gate', 'review_gate', 'policy_control')
  ),
  subject_id TEXT NOT NULL,
  gate_type TEXT NOT NULL CHECK (
    gate_type IN ('approval_required', 'review_required', 'automation_control')
  ),
  decision TEXT NOT NULL CHECK (
    decision IN (
      'allow',
      'auto_approve',
      'escalate_review',
      'paused',
      'resumed',
      'deferred'
    )
  ),
  matched INTEGER NOT NULL DEFAULT 0,
  reason TEXT NOT NULL,
  context_json TEXT NOT NULL,
  created_at TEXT NOT NULL,
  FOREIGN KEY (policy_id) REFERENCES policies(id),
  FOREIGN KEY (session_id) REFERENCES sessions(id)
);

CREATE INDEX IF NOT EXISTS idx_sessions_template_key
  ON sessions(template_key);

CREATE INDEX IF NOT EXISTS idx_policies_session_id_priority
  ON policies(session_id, priority, created_at, id);

CREATE INDEX IF NOT EXISTS idx_policies_template_key_priority
  ON policies(template_key, priority, created_at, id);

CREATE INDEX IF NOT EXISTS idx_policies_phase_key_priority
  ON policies(phase_key, priority, created_at, id);

CREATE INDEX IF NOT EXISTS idx_policies_policy_type
  ON policies(policy_type, created_at, id);

CREATE INDEX IF NOT EXISTS idx_policy_decisions_policy_id_created_at
  ON policy_decisions(policy_id, created_at, id);

CREATE INDEX IF NOT EXISTS idx_policy_decisions_session_id_created_at
  ON policy_decisions(session_id, created_at, id);
