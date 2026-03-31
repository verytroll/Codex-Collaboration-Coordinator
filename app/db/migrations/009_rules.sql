CREATE TABLE IF NOT EXISTS rules (
  id TEXT PRIMARY KEY,
  session_id TEXT NOT NULL,
  rule_type TEXT NOT NULL CHECK (
    rule_type IN (
      'relay',
      'review_required',
      'approval_escalation',
      'channel_routing_preference'
    )
  ),
  name TEXT NOT NULL,
  description TEXT,
  is_active INTEGER NOT NULL DEFAULT 0 CHECK (is_active IN (0, 1)),
  priority INTEGER NOT NULL DEFAULT 100,
  conditions_json TEXT,
  actions_json TEXT,
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL,
  FOREIGN KEY (session_id) REFERENCES sessions(id)
);

CREATE INDEX IF NOT EXISTS idx_rules_session_id_priority
  ON rules(session_id, priority, created_at);

CREATE INDEX IF NOT EXISTS idx_rules_session_id_is_active
  ON rules(session_id, is_active);

CREATE INDEX IF NOT EXISTS idx_rules_rule_type
  ON rules(rule_type);
