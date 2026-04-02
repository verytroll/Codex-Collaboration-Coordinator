CREATE TABLE IF NOT EXISTS integration_principals (
  id TEXT PRIMARY KEY,
  display_label TEXT NOT NULL,
  principal_type TEXT NOT NULL CHECK (
    principal_type IN ('integration_client', 'service_account')
  ),
  actor_role TEXT NOT NULL,
  actor_type TEXT NOT NULL CHECK (actor_type IN ('human', 'service')),
  source TEXT NOT NULL,
  default_scopes_json TEXT NOT NULL,
  notes TEXT,
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS integration_credentials (
  id TEXT PRIMARY KEY,
  principal_id TEXT NOT NULL,
  label TEXT NOT NULL,
  secret_hash TEXT NOT NULL UNIQUE,
  secret_prefix TEXT NOT NULL,
  scopes_json TEXT NOT NULL,
  status TEXT NOT NULL CHECK (status IN ('active', 'revoked', 'expired')),
  status_reason TEXT,
  status_note TEXT,
  expires_at TEXT,
  revoked_at TEXT,
  last_used_at TEXT,
  last_used_surface TEXT,
  notes TEXT,
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL,
  FOREIGN KEY (principal_id) REFERENCES integration_principals(id)
);

CREATE INDEX IF NOT EXISTS idx_integration_principals_principal_type
  ON integration_principals(principal_type);

CREATE INDEX IF NOT EXISTS idx_integration_principals_actor_role
  ON integration_principals(actor_role);

CREATE INDEX IF NOT EXISTS idx_integration_credentials_principal_id
  ON integration_credentials(principal_id);

CREATE INDEX IF NOT EXISTS idx_integration_credentials_status
  ON integration_credentials(status);

CREATE INDEX IF NOT EXISTS idx_integration_credentials_secret_prefix
  ON integration_credentials(secret_prefix);
