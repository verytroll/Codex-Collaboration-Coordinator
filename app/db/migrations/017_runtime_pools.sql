CREATE TABLE IF NOT EXISTS runtime_pools (
  id TEXT PRIMARY KEY,
  pool_key TEXT NOT NULL UNIQUE,
  title TEXT NOT NULL,
  description TEXT,
  runtime_kind TEXT NOT NULL,
  preferred_transport_kind TEXT,
  required_capabilities_json TEXT,
  fallback_pool_key TEXT,
  max_active_contexts INTEGER NOT NULL DEFAULT 1,
  default_isolation_mode TEXT NOT NULL CHECK (default_isolation_mode IN ('shared', 'isolated', 'ephemeral')),
  pool_status TEXT NOT NULL CHECK (pool_status IN ('ready', 'degraded', 'offline')),
  metadata_json TEXT,
  is_default INTEGER NOT NULL DEFAULT 0,
  sort_order INTEGER NOT NULL DEFAULT 100,
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS work_contexts (
  id TEXT PRIMARY KEY,
  session_id TEXT NOT NULL,
  job_id TEXT NOT NULL UNIQUE,
  agent_id TEXT NOT NULL,
  runtime_pool_id TEXT NOT NULL,
  runtime_id TEXT,
  context_key TEXT NOT NULL UNIQUE,
  workspace_path TEXT,
  isolation_mode TEXT NOT NULL CHECK (isolation_mode IN ('shared', 'isolated', 'ephemeral')),
  context_status TEXT NOT NULL CHECK (context_status IN ('active', 'waiting_for_runtime', 'fallback', 'recovered', 'released', 'failed')),
  ownership_state TEXT NOT NULL CHECK (ownership_state IN ('owned', 'borrowed', 'released')),
  selection_reason TEXT,
  failure_reason TEXT,
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL,
  FOREIGN KEY (session_id) REFERENCES sessions(id),
  FOREIGN KEY (job_id) REFERENCES jobs(id),
  FOREIGN KEY (agent_id) REFERENCES agents(id),
  FOREIGN KEY (runtime_id) REFERENCES agent_runtimes(id)
);

CREATE INDEX IF NOT EXISTS idx_runtime_pools_pool_key
  ON runtime_pools(pool_key);

CREATE INDEX IF NOT EXISTS idx_runtime_pools_is_default
  ON runtime_pools(is_default);

CREATE INDEX IF NOT EXISTS idx_runtime_pools_runtime_kind
  ON runtime_pools(runtime_kind);

CREATE INDEX IF NOT EXISTS idx_work_contexts_session_id
  ON work_contexts(session_id);

CREATE INDEX IF NOT EXISTS idx_work_contexts_job_id
  ON work_contexts(job_id);

CREATE INDEX IF NOT EXISTS idx_work_contexts_agent_id
  ON work_contexts(agent_id);

CREATE INDEX IF NOT EXISTS idx_work_contexts_runtime_pool_id
  ON work_contexts(runtime_pool_id);

CREATE INDEX IF NOT EXISTS idx_work_contexts_runtime_id
  ON work_contexts(runtime_id);

CREATE INDEX IF NOT EXISTS idx_work_contexts_context_status
  ON work_contexts(context_status);

CREATE INDEX IF NOT EXISTS idx_work_contexts_ownership_state
  ON work_contexts(ownership_state);
