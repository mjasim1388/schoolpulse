CREATE TABLE IF NOT EXISTS school_profile (
    id              INTEGER PRIMARY KEY DEFAULT 1,
    school_name     TEXT NOT NULL DEFAULT 'My School',
    address         TEXT,
    phone           TEXT,
    email           TEXT,
    principal_name  TEXT,
    logo_base64     TEXT,
    updated_at      TIMESTAMP NOT NULL DEFAULT NOW(),
    CONSTRAINT single_row CHECK (id = 1)
);

INSERT INTO school_profile (id, school_name)
VALUES (1, 'My School')
ON CONFLICT (id) DO NOTHING;