CREATE TABLE IF NOT EXISTS outbox_messages(
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  chat_id INTEGER,
  user_id INTEGER,
  payload_json TEXT NOT NULL,
  not_before_ts INTEGER NOT NULL DEFAULT (CAST(strftime('%s','now') AS INTEGER)),
  status TEXT NOT NULL DEFAULT 'pending',
  attempts INTEGER NOT NULL DEFAULT 0,
  last_error TEXT,
  created_ts INTEGER NOT NULL DEFAULT (CAST(strftime('%s','now') AS INTEGER)),
  sent_ts INTEGER,
  CHECK(status IN ('pending', 'sent', 'failed'))
);

