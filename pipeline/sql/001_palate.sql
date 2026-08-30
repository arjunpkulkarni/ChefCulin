-- Palate Memory (MVP): persist F6 Save decisions. No adaptive/personalization layer.
CREATE EXTENSION IF NOT EXISTS pgcrypto;

CREATE TABLE IF NOT EXISTS palate_memories (
  id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id       TEXT NOT NULL,
  dish          JSONB NOT NULL DEFAULT '[]'::jsonb,
  form          JSONB,
  cuisine_scope JSONB,
  source        TEXT NOT NULL DEFAULT 'f6',
  created_at    TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS palate_memories_user_created_idx
  ON palate_memories (user_id, created_at DESC);
