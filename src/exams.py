import streamlit as st
from sqlalchemy import text
from db import engine


# ============================================================
# EXAMS
# ============================================================

@st.cache_data(ttl=120, show_spinner=False)
def get_all_exams():
    """Return all exams, active first, then newest."""
    with engine.connect() as conn:
        rows = conn.execute(
            text("""
                SELECT id, name, term, start_date, end_date, is_active, created_at
                FROM exams
                ORDER BY is_active DESC, created_at DESC
            """)
        ).fetchall()
    return [dict(r._mapping) for r in rows]


@st.cache_data(ttl=120, show_spinner=False)
def get_exam(exam_id: int):
    """Return one exam by ID."""
    with engine.connect() as conn:
        row = conn.execute(
            text("""
                SELECT id, name, term, start_date, end_date, is_active
                FROM exams WHERE id = :id LIMIT 1
            """),
            {"id": exam_id},
        ).fetchone()
    return dict(row._mapping) if row else None


def add_exam(name: str, term: str, start_date=None, end_date=None):
    """Create a new exam."""
    with engine.connect() as conn:
        conn.execute(
            text("""
                INSERT INTO exams (name, term, start_date, end_date, is_active)
                VALUES (:n, :t, :s, :e, TRUE)
            """),
            {"n": name.strip(), "t": (term or "").strip(), "s": start_date, "e": end_date},
        )
        conn.commit()
    st.cache_data.clear()
    return True


def set_exam_active(exam_id: int, active: bool):
    """Activate or deactivate an exam."""
    with engine.connect() as conn:
        conn.execute(
            text("UPDATE exams SET is_active = :a WHERE id = :id"),
            {"a": bool(active), "id": exam_id},
        )
        conn.commit()
    st.cache_data.clear()
    return True


def delete_exam(exam_id: int):
    """Delete an exam and all its subjects and marks."""
    with engine.connect() as conn:
        conn.execute(text("DELETE FROM exams WHERE id = :id"), {"id": exam_id})
        conn.commit()
    st.cache_data.clear()
    return True


# ============================================================
# EXAM SUBJECTS
# ============================================================

@st.cache_data(ttl=120, show_spinner=False)
def get_subjects_for_exam(exam_id: int, class_name: str = None):
    """Return subjects for an exam, optionally filtered by class."""
    if class_name:
        sql = """
            SELECT id, exam_id, class_name, subject_name, max_marks, pass_marks
            FROM exam_subjects
            WHERE exam_id = :e AND class_name = :c
            ORDER BY subject_name
        """
        params = {"e": exam_id, "c": class_name}
    else:
        sql = """
            SELECT id, exam_id, class_name, subject_name, max_marks, pass_marks
            FROM exam_subjects
            WHERE exam_id = :e
            ORDER BY class_name, subject_name
        """
        params = {"e": exam_id}

    with engine.connect() as conn:
        rows = conn.execute(text(sql), params).fetchall()
    return [dict(r._mapping) for r in rows]


@st.cache_data(ttl=120, show_spinner=False)
def get_classes_with_subjects(exam_id: int):
    """Return distinct classes that have at least one subject for this exam."""
    with engine.connect() as conn:
        rows = conn.execute(
            text("""
                SELECT DISTINCT class_name
                FROM exam_subjects
                WHERE exam_id = :e
                ORDER BY class_name
            """),
            {"e": exam_id},
        ).fetchall()
    return [r[0] for r in rows]


def add_subject(exam_id: int, class_name: str, subject_name: str,
                max_marks: int = 100, pass_marks: int = 40):
    """Add a subject to an exam for a class."""
    with engine.connect() as conn:
        conn.execute(
            text("""
                INSERT INTO exam_subjects
                    (exam_id, class_name, subject_name, max_marks, pass_marks)
                VALUES (:e, :c, :s, :m, :p)
                ON CONFLICT (exam_id, class_name, subject_name) DO UPDATE
                    SET max_marks = EXCLUDED.max_marks,
                        pass_marks = EXCLUDED.pass_marks
            """),
            {
                "e": exam_id,
                "c": class_name.strip(),
                "s": subject_name.strip(),
                "m": int(max_marks),
                "p": int(pass_marks),
            },
        )
        conn.commit()
    st.cache_data.clear()
    return True


def delete_subject(subject_id: int):
    """Delete a subject and its marks."""
    with engine.connect() as conn:
        conn.execute(text("DELETE FROM exam_subjects WHERE id = :id"), {"id": subject_id})
        conn.commit()
    st.cache_data.clear()
    return True


# ============================================================
# MARKS
# ============================================================

@st.cache_data(ttl=120, show_spinner=False)
def get_marks_for_subject(exam_id: int, subject_id: int):
    """Return {student_id: {marks_obtained, is_absent}} for a subject."""
    with engine.connect() as conn:
        rows = conn.execute(
            text("""
                SELECT student_id, marks_obtained, is_absent
                FROM marks
                WHERE exam_id = :e AND subject_id = :s
            """),
            {"e": exam_id, "s": subject_id},
        ).fetchall()
    return {
        r[0]: {"marks_obtained": r[1], "is_absent": r[2]}
        for r in rows
    }


def save_marks(exam_id: int, subject_id: int, student_id: int,
               marks_obtained, is_absent: bool = False):
    """Upsert a mark row."""
    with engine.connect() as conn:
        conn.execute(
            text("""
                INSERT INTO marks (exam_id, subject_id, student_id,
                                   marks_obtained, is_absent, updated_at)
                VALUES (:e, :s, :st, :m, :a, NOW())
                ON CONFLICT (exam_id, subject_id, student_id) DO UPDATE
                    SET marks_obtained = EXCLUDED.marks_obtained,
                        is_absent = EXCLUDED.is_absent,
                        updated_at = NOW()
            """),
            {
                "e": exam_id,
                "s": subject_id,
                "st": student_id,
                "m": None if is_absent else marks_obtained,
                "a": bool(is_absent),
            },
        )
        conn.commit()
    st.cache_data.clear()
    return True


def save_marks_bulk(exam_id: int, subject_id: int, rows: list):
    """Save many marks at once. rows = [{student_id, marks_obtained, is_absent}, ...]"""
    if not rows:
        return True
    with engine.connect() as conn:
        for r in rows:
            conn.execute(
                text("""
                    INSERT INTO marks (exam_id, subject_id, student_id,
                                       marks_obtained, is_absent, updated_at)
                    VALUES (:e, :s, :st, :m, :a, NOW())
                    ON CONFLICT (exam_id, subject_id, student_id) DO UPDATE
                        SET marks_obtained = EXCLUDED.marks_obtained,
                            is_absent = EXCLUDED.is_absent,
                            updated_at = NOW()
                """),
                {
                    "e": exam_id,
                    "s": subject_id,
                    "st": r["student_id"],
                    "m": None if r.get("is_absent") else r.get("marks_obtained"),
                    "a": bool(r.get("is_absent", False)),
                },
            )
        conn.commit()
    st.cache_data.clear()
    return True


@st.cache_data(ttl=120, show_spinner=False)
def get_subject_progress(exam_id: int, class_name: str):
    """Return [{subject_id, subject_name, entered, total}] showing how many students have marks entered."""
    with engine.connect() as conn:
        subjects = conn.execute(
            text("""
                SELECT id, subject_name, max_marks, pass_marks
                FROM exam_subjects
                WHERE exam_id = :e AND class_name = :c
                ORDER BY subject_name
            """),
            {"e": exam_id, "c": class_name},
        ).fetchall()

        total_students = conn.execute(
            text("""
                SELECT COUNT(*) FROM students
                WHERE status = 'active' AND class_name = :c
            """),
            {"c": class_name},
        ).scalar() or 0

        progress = []
        for sub in subjects:
            entered = conn.execute(
                text("""
                    SELECT COUNT(*) FROM marks
                    WHERE exam_id = :e AND subject_id = :s
                      AND (marks_obtained IS NOT NULL OR is_absent = TRUE)
                """),
                {"e": exam_id, "s": sub[0]},
            ).scalar() or 0

            progress.append({
                "subject_id": sub[0],
                "subject_name": sub[1],
                "max_marks": sub[2],
                "pass_marks": sub[3],
                "entered": int(entered),
                "total": int(total_students),
            })

    return progress


# ============================================================
# REPORT CARD DATA
# ============================================================

@st.cache_data(ttl=120, show_spinner=False)
def get_report_card_data(exam_id: int, student_id: int):
    """
    Return everything needed to render one student's report card.
    Includes: student info, per-subject marks, totals, percentage, grade, position.
    """
    with engine.connect() as conn:
        # Student
        student = conn.execute(
            text("""
                SELECT id, full_name, roll_number, class_name, section,
                       parent_name, parent_phone
                FROM students WHERE id = :id
            """),
            {"id": student_id},
        ).fetchone()

        if not student:
            return None

        student = dict(student._mapping)

        # All subjects for this exam in the student's class
        subjects = conn.execute(
            text("""
                SELECT id, subject_name, max_marks, pass_marks
                FROM exam_subjects
                WHERE exam_id = :e AND class_name = :c
                ORDER BY subject_name
            """),
            {"e": exam_id, "c": student["class_name"]},
        ).fetchall()

        subject_rows = []
        total_obtained = 0.0
        total_max = 0
        subjects_passed = 0
        subjects_failed = 0

        for sub in subjects:
            sub_dict = dict(sub._mapping)
            mark_row = conn.execute(
                text("""
                    SELECT marks_obtained, is_absent
                    FROM marks
                    WHERE exam_id = :e AND subject_id = :s AND student_id = :st
                """),
                {"e": exam_id, "s": sub_dict["id"], "st": student_id},
            ).fetchone()

            if mark_row:
                obtained = float(mark_row[0]) if mark_row[0] is not None else 0.0
                is_absent = bool(mark_row[1])
            else:
                obtained = 0.0
                is_absent = False

            pct = (obtained / sub_dict["max_marks"] * 100) if sub_dict["max_marks"] else 0
            passed = obtained >= sub_dict["pass_marks"] and not is_absent

            if not is_absent:
                total_obtained += obtained
                total_max += sub_dict["max_marks"]
                if passed:
                    subjects_passed += 1
                else:
                    subjects_failed += 1

            subject_rows.append({
                "subject_name": sub_dict["subject_name"],
                "marks_obtained": obtained,
                "max_marks": sub_dict["max_marks"],
                "pass_marks": sub_dict["pass_marks"],
                "percentage": round(pct, 1),
                "is_absent": is_absent,
                "passed": passed,
            })

        # Percentage and grade
        percentage = (total_obtained / total_max * 100) if total_max else 0.0
        grade = _compute_grade(percentage)

        # Class position
        position, total_in_class = _compute_position(
            conn, exam_id, student["class_name"], student_id
        )

        return {
            "student": student,
            "subjects": subject_rows,
            "total_obtained": round(total_obtained, 2),
            "total_max": total_max,
            "percentage": round(percentage, 1),
            "grade": grade,
            "position": position,
            "total_in_class": total_in_class,
            "subjects_passed": subjects_passed,
            "subjects_failed": subjects_failed,
        }


def _compute_grade(percentage: float) -> str:
    """Simple grade scale. Can be customised later."""
    if percentage >= 90:
        return "A+"
    if percentage >= 80:
        return "A"
    if percentage >= 70:
        return "B"
    if percentage >= 60:
        return "C"
    if percentage >= 50:
        return "D"
    if percentage >= 40:
        return "E"
    return "F"


def _compute_position(conn, exam_id, class_name, student_id):
    """
    Compute (position, total) for a student in their class for this exam.
    Position is based on total marks across all subjects.
    """
    # Total per student
    rows = conn.execute(
        text("""
            SELECT m.student_id, SUM(m.marks_obtained) AS total
            FROM marks m
            JOIN exam_subjects es ON es.id = m.subject_id
            JOIN students s ON s.id = m.student_id
            WHERE m.exam_id = :e
              AND es.class_name = :c
              AND s.class_name = :c
              AND m.is_absent = FALSE
              AND m.marks_obtained IS NOT NULL
            GROUP BY m.student_id
            ORDER BY total DESC
        """),
        {"e": exam_id, "c": class_name},
    ).fetchall()

    totals = [(r[0], float(r[1] or 0)) for r in rows]
    if not totals:
        return None, 0

    totals.sort(key=lambda x: x[1], reverse=True)
    position = next((i + 1 for i, (sid, _) in enumerate(totals) if sid == student_id), None)
    return position, len(totals)