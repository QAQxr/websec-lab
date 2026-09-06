# Database Migrations

Phase 2.2a uses `database/schema.sql` as the canonical schema. The bootstrap records version `002_phase22a_schema` in `schema_migrations` after applying it, then executes the idempotent `database/seed.sql`. The earlier `001_initial_schema` marker is accepted as the Phase 2.2a migration predecessor.

Future schema changes should add numbered migration files here and update the bootstrap migration runner. Keep `database/schema.sql` synchronized with the fresh-database result of all applied migrations.
