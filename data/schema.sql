-- Inventory schema for the portable workspace.
-- This file is committed to git.  data/inventory.db is local and gitignored.
-- Run "python3 tools/inventory.py init" to create or verify the database.
--
-- Redesigned models table (v2):
--   * tier        -- free / paid / unknown
--   * context_window -- max input tokens (optional)
--   * cost_per_1k  -- indicative cost per 1000 tokens (optional)
--   * provider    -- denormalised provider name for quick filtering
-- A model belongs to exactly one provider.  Providers may be free-tier or paid.
--
-- v3: the settings table is gone (nothing read it; tool paths and git settings live in
-- settings.json).  An older data/inventory.db keeps its settings table; that is a
-- harmless leftover and may be dropped by hand.

PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS schema_meta (
    key   TEXT PRIMARY KEY,
    value TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS machines (
    id        INTEGER PRIMARY KEY,
    name      TEXT NOT NULL UNIQUE,
    os        TEXT,
    arch      TEXT,
    python    TEXT,
    user_name TEXT,
    role      TEXT,
    status    TEXT NOT NULL DEFAULT 'active'
              CHECK (status IN ('active', 'planned', 'broken', 'retired', 'unknown')),
    notes     TEXT
);

CREATE TABLE IF NOT EXISTS services (
    id      INTEGER PRIMARY KEY,
    name    TEXT NOT NULL UNIQUE,
    kind    TEXT,
    account TEXT,
    status  TEXT NOT NULL DEFAULT 'active'
            CHECK (status IN ('active', 'planned', 'broken', 'retired', 'unknown')),
    notes   TEXT
);

CREATE TABLE IF NOT EXISTS providers (
    id       INTEGER PRIMARY KEY,
    name     TEXT NOT NULL UNIQUE,
    kind     TEXT,
    base_url TEXT,
    free_tier INTEGER NOT NULL DEFAULT 0
              CHECK (free_tier IN (0, 1)),
    status   TEXT NOT NULL DEFAULT 'active'
             CHECK (status IN ('active', 'planned', 'broken', 'retired', 'unknown')),
    notes    TEXT
);

CREATE TABLE IF NOT EXISTS keys (
    id          INTEGER PRIMARY KEY,
    path        TEXT NOT NULL UNIQUE,
    service_id  INTEGER REFERENCES services(id) ON DELETE SET NULL,
    provider_id INTEGER REFERENCES providers(id) ON DELETE SET NULL,
    kind        TEXT,
    status      TEXT NOT NULL DEFAULT 'active'
                CHECK (status IN ('active', 'planned', 'broken', 'retired', 'unknown')),
    notes       TEXT,
    CHECK (service_id IS NULL OR provider_id IS NULL)
);

CREATE TABLE IF NOT EXISTS models (
    id             INTEGER PRIMARY KEY,
    alias          TEXT NOT NULL UNIQUE,
    model_id       TEXT NOT NULL,          -- the actual model identifier sent to the API
    provider_id    INTEGER NOT NULL REFERENCES providers(id) ON DELETE RESTRICT,
    key_id         INTEGER REFERENCES keys(id) ON DELETE SET NULL,
    tier           TEXT NOT NULL DEFAULT 'unknown'
                   CHECK (tier IN ('free', 'paid', 'unknown')),
    context_window INTEGER,
    cost_per_1k    REAL,
    status         TEXT NOT NULL DEFAULT 'active'
                   CHECK (status IN ('active', 'planned', 'broken', 'retired', 'unknown')),
    notes          TEXT
);

CREATE TABLE IF NOT EXISTS tools (
    id         INTEGER PRIMARY KEY,
    name       TEXT NOT NULL,
    machine_id INTEGER REFERENCES machines(id) ON DELETE SET NULL,
    status     TEXT NOT NULL DEFAULT 'active'
               CHECK (status IN ('active', 'planned', 'broken', 'retired', 'unknown')),
    notes      TEXT,
    UNIQUE (name, machine_id)
);

CREATE INDEX IF NOT EXISTS idx_keys_service ON keys(service_id);
CREATE INDEX IF NOT EXISTS idx_keys_provider ON keys(provider_id);
CREATE INDEX IF NOT EXISTS idx_models_provider ON models(provider_id);
CREATE INDEX IF NOT EXISTS idx_models_tier ON models(tier);
