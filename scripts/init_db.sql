-- Runs once, when the Postgres volume is first created.
--
-- The extension must exist before SQLAlchemy creates any table carrying a
-- vector column, so it is enabled here rather than in application startup.

CREATE EXTENSION IF NOT EXISTS vector;

-- Confirms in the container log which extension version is active, so a
-- version mismatch surfaces at boot rather than at first query.
DO $$
DECLARE version text;
BEGIN
  SELECT extversion INTO version FROM pg_extension WHERE extname = 'vector';
  RAISE NOTICE 'pgvector enabled, version %', version;
END $$;
