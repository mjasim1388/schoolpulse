CREATE TABLE IF NOT EXISTS class_fees (
    class_name   TEXT PRIMARY KEY,
    monthly_fee  NUMERIC(10, 2) NOT NULL DEFAULT 0,
    updated_at   TIMESTAMP NOT NULL DEFAULT NOW()
);

-- Seed from existing students (one-time, only if not already present)
INSERT INTO class_fees (class_name, monthly_fee)
SELECT class_name, AVG(monthly_fee)
FROM students
WHERE status = 'active' AND class_name IS NOT NULL
GROUP BY class_name
ON CONFLICT (class_name) DO NOTHING;