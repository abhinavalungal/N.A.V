-- Runs once, on first initialisation of the data volume, before the API
-- connects. Alembic owns tables; extensions are provisioned here because they
-- need superuser rights.
CREATE EXTENSION IF NOT EXISTS "pgcrypto";
CREATE EXTENSION IF NOT EXISTS "vector";
