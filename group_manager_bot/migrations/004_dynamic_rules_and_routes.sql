CREATE TABLE IF NOT EXISTS dynamic_remove_rules(
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  chat_id INTEGER NOT NULL,
  pattern TEXT NOT NULL,
  enabled INTEGER NOT NULL DEFAULT 1
);

CREATE INDEX IF NOT EXISTS idx_dynamic_remove_rules_chat
ON dynamic_remove_rules(chat_id);

CREATE TABLE IF NOT EXISTS link_routes(
  chat_id INTEGER NOT NULL,
  keyword TEXT NOT NULL,
  destination TEXT NOT NULL,
  gate_group_id INTEGER,
  enabled INTEGER NOT NULL DEFAULT 1,
  PRIMARY KEY(chat_id, keyword)
);

CREATE INDEX IF NOT EXISTS idx_link_routes_chat
ON link_routes(chat_id);

