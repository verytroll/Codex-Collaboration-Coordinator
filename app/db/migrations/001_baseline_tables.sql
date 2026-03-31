CREATE TABLE IF NOT EXISTS agents (
  id TEXT PRIMARY KEY,
  display_name TEXT NOT NULL UNIQUE,
  role TEXT NOT NULL,
  is_lead_default INTEGER NOT NULL DEFAULT 0,
  runtime_kind TEXT NOT NULL,
  capabilities_json TEXT,
  default_config_json TEXT,
  status TEXT NOT NULL CHECK (status IN ('active', 'disabled', 'archived')),
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS agent_runtimes (
  id TEXT PRIMARY KEY,
  agent_id TEXT NOT NULL,
  runtime_kind TEXT NOT NULL,
  transport_kind TEXT NOT NULL,
  transport_config_json TEXT,
  workspace_path TEXT,
  approval_policy TEXT,
  sandbox_policy TEXT,
  runtime_status TEXT NOT NULL CHECK (runtime_status IN ('starting', 'online', 'offline', 'crashed', 'busy')),
  last_heartbeat_at TEXT,
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL,
  FOREIGN KEY (agent_id) REFERENCES agents(id)
);

CREATE TABLE IF NOT EXISTS sessions (
  id TEXT PRIMARY KEY,
  title TEXT NOT NULL,
  goal TEXT,
  status TEXT NOT NULL CHECK (status IN ('draft', 'active', 'paused', 'completed', 'archived')),
  lead_agent_id TEXT,
  active_phase_id TEXT,
  loop_guard_status TEXT NOT NULL DEFAULT 'normal' CHECK (loop_guard_status IN ('normal', 'warning', 'paused')),
  loop_guard_reason TEXT,
  last_message_at TEXT,
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL,
  FOREIGN KEY (lead_agent_id) REFERENCES agents(id)
);

CREATE TABLE IF NOT EXISTS session_participants (
  id TEXT PRIMARY KEY,
  session_id TEXT NOT NULL,
  agent_id TEXT NOT NULL,
  runtime_id TEXT,
  is_lead INTEGER NOT NULL DEFAULT 0,
  read_scope TEXT NOT NULL,
  write_scope TEXT NOT NULL,
  participant_status TEXT NOT NULL CHECK (participant_status IN ('invited', 'joined', 'left', 'removed')),
  joined_at TEXT,
  left_at TEXT,
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL,
  UNIQUE (session_id, agent_id),
  FOREIGN KEY (session_id) REFERENCES sessions(id),
  FOREIGN KEY (agent_id) REFERENCES agents(id),
  FOREIGN KEY (runtime_id) REFERENCES agent_runtimes(id)
);
