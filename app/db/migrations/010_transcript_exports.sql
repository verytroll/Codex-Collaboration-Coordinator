CREATE TABLE IF NOT EXISTS transcript_exports (
  id TEXT PRIMARY KEY,
  session_id TEXT NOT NULL,
  export_kind TEXT NOT NULL CHECK (export_kind IN ('transcript')),
  export_format TEXT NOT NULL CHECK (export_format IN ('json', 'text')),
  title TEXT NOT NULL,
  file_name TEXT NOT NULL,
  mime_type TEXT NOT NULL,
  content_text TEXT NOT NULL,
  size_bytes INTEGER NOT NULL,
  checksum_sha256 TEXT NOT NULL,
  metadata_json TEXT,
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL,
  FOREIGN KEY (session_id) REFERENCES sessions(id)
);

CREATE INDEX IF NOT EXISTS idx_transcript_exports_session_id_created_at
  ON transcript_exports(session_id, created_at, id);

CREATE INDEX IF NOT EXISTS idx_transcript_exports_export_kind
  ON transcript_exports(export_kind);
