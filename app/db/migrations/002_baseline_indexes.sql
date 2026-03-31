CREATE INDEX IF NOT EXISTS idx_sessions_lead_agent_id
  ON sessions(lead_agent_id);

CREATE INDEX IF NOT EXISTS idx_agent_runtimes_agent_id
  ON agent_runtimes(agent_id);

CREATE INDEX IF NOT EXISTS idx_session_participants_session_id
  ON session_participants(session_id);

CREATE INDEX IF NOT EXISTS idx_session_participants_agent_id
  ON session_participants(agent_id);
