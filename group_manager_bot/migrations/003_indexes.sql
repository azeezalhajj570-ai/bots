CREATE INDEX IF NOT EXISTS idx_warnings_chat_user
ON warnings(chat_id, user_id);

CREATE INDEX IF NOT EXISTS idx_outbox_status_not_before
ON outbox_messages(status, not_before_ts);

CREATE INDEX IF NOT EXISTS idx_outbox_chat
ON outbox_messages(chat_id);

CREATE INDEX IF NOT EXISTS idx_outbox_user
ON outbox_messages(user_id);

