CREATE TABLE IF NOT EXISTS participation_gates(
  chat_id INTEGER NOT NULL,
  gate_group_id INTEGER NOT NULL,
  gate_title TEXT NOT NULL,
  join_url TEXT NOT NULL,
  enabled INTEGER NOT NULL DEFAULT 1,
  PRIMARY KEY(chat_id, gate_group_id)
);

CREATE INDEX IF NOT EXISTS idx_participation_gates_chat
ON participation_gates(chat_id);

