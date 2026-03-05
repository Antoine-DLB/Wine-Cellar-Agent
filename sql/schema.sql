-- ============================================================
-- Schéma de base de données - Wine Cellar Bot
-- À exécuter dans le SQL Editor de Supabase
-- ============================================================

-- ============================================================
-- TABLE : bottles
-- ============================================================
CREATE TABLE IF NOT EXISTS bottles (
    id                UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    name              TEXT        NOT NULL,
    color             TEXT        NOT NULL CHECK (color IN ('rouge', 'blanc', 'rosé', 'champagne', 'mousseux', 'liquoreux')),
    region            TEXT,
    appellation       TEXT,
    producer          TEXT,
    vintage           INTEGER,
    grape_varieties   TEXT[],
    purchase_price    DECIMAL(10, 2),
    purchase_date     DATE,
    quantity          INTEGER     NOT NULL DEFAULT 1,
    storage_location  TEXT,
    drink_from        INTEGER,
    drink_until       INTEGER,
    notes             TEXT,
    image_url         TEXT,
    created_at        TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at        TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- ============================================================
-- TABLE : tasting_log
-- ============================================================
CREATE TABLE IF NOT EXISTS tasting_log (
    id            UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    bottle_id     UUID        REFERENCES bottles(id) ON DELETE SET NULL,
    bottle_name   TEXT        NOT NULL,
    tasted_at     DATE        NOT NULL DEFAULT CURRENT_DATE,
    rating        INTEGER     CHECK (rating >= 1 AND rating <= 5),
    tasting_notes TEXT,
    food_pairing  TEXT,
    occasion      TEXT,
    created_at    TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- ============================================================
-- TABLE : wishlist
-- ============================================================
CREATE TABLE IF NOT EXISTS wishlist (
    id       UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    name     TEXT        NOT NULL,
    notes    TEXT,
    priority INTEGER     NOT NULL DEFAULT 3 CHECK (priority >= 1 AND priority <= 5),
    added_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- ============================================================
-- TABLE : conversation_history
-- ============================================================
CREATE TABLE IF NOT EXISTS conversation_history (
    id           UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
    phone_number TEXT        NOT NULL,
    role         TEXT        NOT NULL CHECK (role IN ('user', 'assistant')),
    content      TEXT        NOT NULL,
    created_at   TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- ============================================================
-- INDEX
-- ============================================================
CREATE INDEX IF NOT EXISTS idx_conversation_history_phone_created
    ON conversation_history (phone_number, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_bottles_color
    ON bottles (color);

CREATE INDEX IF NOT EXISTS idx_bottles_region
    ON bottles (region);

-- ============================================================
-- TRIGGER : auto-update updated_at sur bottles
-- ============================================================
CREATE OR REPLACE FUNCTION update_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = now();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE OR REPLACE TRIGGER bottles_updated_at
    BEFORE UPDATE ON bottles
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at();

-- ============================================================
-- ROW LEVEL SECURITY
-- ============================================================
ALTER TABLE bottles              ENABLE ROW LEVEL SECURITY;
ALTER TABLE tasting_log          ENABLE ROW LEVEL SECURITY;
ALTER TABLE wishlist             ENABLE ROW LEVEL SECURITY;
ALTER TABLE conversation_history ENABLE ROW LEVEL SECURITY;

-- Politique : accès complet pour le service role
CREATE POLICY "service_role_all_bottles"
    ON bottles FOR ALL
    TO service_role
    USING (true)
    WITH CHECK (true);

CREATE POLICY "service_role_all_tasting_log"
    ON tasting_log FOR ALL
    TO service_role
    USING (true)
    WITH CHECK (true);

CREATE POLICY "service_role_all_wishlist"
    ON wishlist FOR ALL
    TO service_role
    USING (true)
    WITH CHECK (true);

CREATE POLICY "service_role_all_conversation_history"
    ON conversation_history FOR ALL
    TO service_role
    USING (true)
    WITH CHECK (true);
