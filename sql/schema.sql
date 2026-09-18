-- ============================================================
-- SchoolPulse Database Schema
-- ============================================================

-- Drop in reverse dependency order
DROP TABLE IF EXISTS fee_payments;
DROP TABLE IF EXISTS students;
DROP TABLE IF EXISTS users;

-- ------------------------------------------------------------
-- USERS (login accounts for school staff)
-- ------------------------------------------------------------
CREATE TABLE users (
    id              SERIAL PRIMARY KEY,
    full_name       TEXT NOT NULL,
    email           TEXT NOT NULL UNIQUE,
    password_hash   TEXT NOT NULL,
    role            TEXT NOT NULL DEFAULT 'admin',
    created_at      TIMESTAMP NOT NULL DEFAULT NOW()
);

-- ------------------------------------------------------------
-- STUDENTS
-- ------------------------------------------------------------
CREATE TABLE students (
    id              SERIAL PRIMARY KEY,
    full_name       TEXT NOT NULL,
    roll_number     TEXT,
    class_name      TEXT NOT NULL,
    section         TEXT,
    parent_name     TEXT,
    parent_phone    TEXT,
    monthly_fee     NUMERIC(10, 2) NOT NULL DEFAULT 0,
    status          TEXT NOT NULL DEFAULT 'active',
    created_at      TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_students_class ON students(class_name);
CREATE INDEX idx_students_status ON students(status);

-- ------------------------------------------------------------
-- FEE PAYMENTS
-- ------------------------------------------------------------
CREATE TABLE fee_payments (
    id              SERIAL PRIMARY KEY,
    student_id      INTEGER NOT NULL REFERENCES students(id) ON DELETE CASCADE,
    amount          NUMERIC(10, 2) NOT NULL,
    month           TEXT NOT NULL,           -- format: '2025-01'
    paid_on         DATE NOT NULL DEFAULT CURRENT_DATE,
    method          TEXT DEFAULT 'cash',     -- cash, bank, easypaisa, jazzcash
    note            TEXT,
    created_at      TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_fee_student ON fee_payments(student_id);
CREATE INDEX idx_fee_month ON fee_payments(month);