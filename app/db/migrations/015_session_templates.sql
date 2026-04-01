CREATE TABLE IF NOT EXISTS session_templates (
  id TEXT PRIMARY KEY,
  template_key TEXT NOT NULL UNIQUE,
  title TEXT NOT NULL,
  description TEXT,
  default_goal TEXT,
  participant_roles_json TEXT NOT NULL,
  channels_json TEXT NOT NULL,
  phase_order_json TEXT NOT NULL,
  rule_presets_json TEXT NOT NULL,
  orchestration_json TEXT,
  is_default INTEGER NOT NULL DEFAULT 0,
  sort_order INTEGER NOT NULL DEFAULT 100,
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_session_templates_is_default
  ON session_templates(is_default, sort_order, title, template_key);
