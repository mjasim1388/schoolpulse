-- ============================================================
-- SchoolPulse — Exams, Subjects, Marks
-- ============================================================

DROP TABLE IF EXISTS marks;
DROP TABLE IF EXISTS exam_subjects;
DROP TABLE IF EXISTS exams;

-- ------------------------------------------------------------
-- EXAMS (e.g. "Final Term 2026", "Mid-Term 2025")
-- ------------------------------------------------------------
CREATE TABLE exams (
    id              SERIAL PRIMARY KEY,
    name            TEXT NOT NULL,
    term            TEXT,                 -- e.g. "Final Term", "Mid-Term"
    start_date      DATE,
    end_date        DATE,
    is_active       BOOLEAN NOT NULL DEFAULT TRUE,
    created_at      TIMESTAMP NOT NULL DEFAULT NOW()
);

CREATE INDEX idx_exams_active ON exams(is_active);

-- ------------------------------------------------------------
-- EXAM SUBJECTS (per class, per exam)
-- e.g. Final Term 2026 — Class 5 — Mathematics — max 100 — pass 40
-- ------------------------------------------------------------
CREATE TABLE exam_subjects (
    id              SERIAL PRIMARY KEY,
    exam_id         INTEGER NOT NULL REFERENCES exams(id) ON DELETE CASCADE,
    class_name      TEXT NOT NULL,
    subject_name    TEXT NOT NULL,
    max_marks       INTEGER NOT NULL DEFAULT 100,
    pass_marks      INTEGER NOT NULL DEFAULT 40,
    created_at      TIMESTAMP NOT NULL DEFAULT NOW(),
    UNIQUE (exam_id, class_name, subject_name)
);

CREATE INDEX idx_subjects_exam ON exam_subjects(exam_id);
CREATE INDEX idx_subjects_class ON exam_subjects(class_name);

-- ------------------------------------------------------------
-- MARKS (one row per student per subject per exam)
-- ------------------------------------------------------------
CREATE TABLE marks (
    id              SERIAL PRIMARY KEY,
    exam_id         INTEGER NOT NULL REFERENCES exams(id) ON DELETE CASCADE,
    subject_id      INTEGER NOT NULL REFERENCES exam_subjects(id) ON DELETE CASCADE,
    student_id      INTEGER NOT NULL REFERENCES students(id) ON DELETE CASCADE,
    marks_obtained  NUMERIC(6, 2),
    is_absent       BOOLEAN NOT NULL DEFAULT FALSE,
    created_at      TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMP NOT NULL DEFAULT NOW(),
    UNIQUE (exam_id, subject_id, student_id)
);

CREATE INDEX idx_marks_exam ON marks(exam_id);
CREATE INDEX idx_marks_student ON marks(student_id);
CREATE INDEX idx_marks_subject ON marks(subject_id);