CREATE TABLE IF NOT EXISTS messages (
  id TEXT PRIMARY KEY,
  session_id TEXT NOT NULL,
  sender_type TEXT NOT NULL CHECK (sender_type IN ('user', 'agent', 'system')),
  sender_id TEXT,
  message_type TEXT NOT NULL CHECK (
    message_type IN (
      'chat',
      'command',
      'relay',
      'status',
      'approval_request',
      'approval_decision',
      'artifact_notice'
    )
  ),
  content TEXT NOT NULL,
  content_format TEXT NOT NULL DEFAULT 'plain_text' CHECK (
    content_format IN ('plain_text', 'markdown', 'json')
  ),
  reply_to_message_id TEXT,
  source_message_id TEXT,
  visibility TEXT NOT NULL DEFAULT 'session' CHECK (visibility IN ('session', 'system_only', 'lead_only')),
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL,
  FOREIGN KEY (session_id) REFERENCES sessions(id),
  FOREIGN KEY (reply_to_message_id) REFERENCES messages(id),
  FOREIGN KEY (source_message_id) REFERENCES messages(id)
);

CREATE TABLE IF NOT EXISTS message_mentions (
  id TEXT PRIMARY KEY,
  message_id TEXT NOT NULL,
  mentioned_agent_id TEXT NOT NULL,
  mention_text TEXT NOT NULL,
  mention_order INTEGER NOT NULL,
  created_at TEXT NOT NULL,
  UNIQUE (message_id, mentioned_agent_id, mention_order),
  FOREIGN KEY (message_id) REFERENCES messages(id),
  FOREIGN KEY (mentioned_agent_id) REFERENCES agents(id)
);

CREATE INDEX IF NOT EXISTS idx_messages_session_id_created_at
  ON messages(session_id, created_at);

CREATE INDEX IF NOT EXISTS idx_messages_sender_id
  ON messages(sender_id);

CREATE INDEX IF NOT EXISTS idx_messages_reply_to_message_id
  ON messages(reply_to_message_id);

CREATE INDEX IF NOT EXISTS idx_messages_source_message_id
  ON messages(source_message_id);

CREATE INDEX IF NOT EXISTS idx_message_mentions_message_id
  ON message_mentions(message_id);

CREATE INDEX IF NOT EXISTS idx_message_mentions_mentioned_agent_id
  ON message_mentions(mentioned_agent_id);
