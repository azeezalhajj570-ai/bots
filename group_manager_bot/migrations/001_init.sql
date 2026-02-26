CREATE TABLE IF NOT EXISTS group_settings(
  chat_id INTEGER PRIMARY KEY,
  anti_links INTEGER DEFAULT 1,
  anti_bots  INTEGER DEFAULT 1,
  hide_system INTEGER DEFAULT 0
);

CREATE TABLE IF NOT EXISTS warnings(
  chat_id INTEGER,
  user_id INTEGER,
  warns INTEGER DEFAULT 0,
  PRIMARY KEY(chat_id, user_id)
);
