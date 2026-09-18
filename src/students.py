import streamlit as st
from sqlalchemy import text
from db import engine

STANDARD_CLASSES = [
    "Nursery",
    "KG",
    "Class 1",
    "Class 2",
    "Class 3",
    "Class 4",
    "Class 5",
    "Class 6",
    "Class 7",
    "Class 8",
    "Class 9",
    "Class 10",
]

STANDARD_SECTIONS = ["A", "B", "C", "D"]

@st.cache_data(ttl=120, show_spinner=False)
def get_all_students():
    """Return all active students, sorted by class then name."""
    with engine.connect() as conn:
        rows = conn.execute(
            text("""
                SELECT id, full_name, roll_number, class_name, section,
                       parent_name, parent_phone, monthly_fee, status, created_at
                FROM students
                WHERE status = 'active'
                ORDER BY class_name, full_name
            """)
        ).fetchall()
    return [dict(r._mapping) for r in rows]

@st.cache_data(ttl=120, show_spinner=False)
def get_student(student_id: int):
    """Return one student by ID, or None."""
    with engine.connect() as conn:
        row = conn.execute(
            text("""
                SELECT id, full_name, roll_number, class_name, section,
                       parent_name, parent_phone, monthly_fee, status, created_at
                FROM students
                WHERE id = :id
                LIMIT 1
            """),
            {"id": student_id},
        ).fetchone()
    return dict(row._mapping) if row else None


def add_student(
    full_name: str,
    roll_number: str,
    class_name: str,
    section: str,
    parent_name: str,
    parent_phone: str,
    monthly_fee: float,
):
    """Insert a new student."""
    with engine.connect() as conn:
        conn.execute(
            text("""
                INSERT INTO students
                    (full_name, roll_number, class_name, section,
                     parent_name, parent_phone, monthly_fee)
                VALUES
                    (:full_name, :roll_number, :class_name, :section,
                     :parent_name, :parent_phone, :monthly_fee)
            """),
            {
                "full_name": full_name.strip(),
                "roll_number": (roll_number or "").strip(),
                "class_name": class_name.strip(),
                "section": (section or "").strip(),
                "parent_name": (parent_name or "").strip(),
                "parent_phone": (parent_phone or "").strip(),
                "monthly_fee": float(monthly_fee or 0),
            },
        )
        conn.commit()
    st.cache_data.clear()
    return True


def update_student(
    student_id: int,
    full_name: str,
    roll_number: str,
    class_name: str,
    section: str,
    parent_name: str,
    parent_phone: str,
    monthly_fee: float,
):
    """Update an existing student."""
    with engine.connect() as conn:
        conn.execute(
            text("""
                UPDATE students SET
                    full_name = :full_name,
                    roll_number = :roll_number,
                    class_name = :class_name,
                    section = :section,
                    parent_name = :parent_name,
                    parent_phone = :parent_phone,
                    monthly_fee = :monthly_fee
                WHERE id = :id
            """),
            {
                "id": student_id,
                "full_name": full_name.strip(),
                "roll_number": (roll_number or "").strip(),
                "class_name": class_name.strip(),
                "section": (section or "").strip(),
                "parent_name": (parent_name or "").strip(),
                "parent_phone": (parent_phone or "").strip(),
                "monthly_fee": float(monthly_fee or 0),
            },
        )
        conn.commit()
        st.cache_data.clear()    
    return True


def soft_delete_student(student_id: int):
    """Mark a student as inactive instead of physically deleting."""
    with engine.connect() as conn:
        conn.execute(
            text("UPDATE students SET status = 'inactive' WHERE id = :id"),
            {"id": student_id},
        )
        conn.commit()
        st.cache_data.clear()    
    return True

@st.cache_data(ttl=120, show_spinner=False)
def count_students():
    """Return total number of active students."""
    with engine.connect() as conn:
        n = conn.execute(
            text("SELECT COUNT(*) FROM students WHERE status = 'active'")
        ).scalar()
    return int(n or 0)

@st.cache_data(ttl=120, show_spinner=False)
def get_classes():
    """Return distinct list of class names in use."""
    with engine.connect() as conn:
        rows = conn.execute(
            text("""
                SELECT DISTINCT class_name
                FROM students
                WHERE status = 'active' AND class_name IS NOT NULL
                ORDER BY class_name
            """)
        ).fetchall()
    return [r[0] for r in rows]

def get_class_fee(class_name: str):
    """Return the default monthly fee for a class, or None."""
    if not class_name:
        return None
    with engine.connect() as conn:
        row = conn.execute(
            text("""
                SELECT monthly_fee FROM class_fees
                WHERE class_name = :c LIMIT 1
            """),
            {"c": class_name.strip()},
        ).fetchone()
    return float(row[0]) if row else None


def set_class_fee(class_name: str, monthly_fee: float):
    """Upsert the default fee for a class."""
    with engine.connect() as conn:
        conn.execute(
            text("""
                INSERT INTO class_fees (class_name, monthly_fee, updated_at)
                VALUES (:c, :f, NOW())
                ON CONFLICT (class_name) DO UPDATE
                    SET monthly_fee = EXCLUDED.monthly_fee,
                        updated_at = NOW()
            """),
            {"c": class_name.strip(), "f": float(monthly_fee)},
        )
        conn.commit()
    return True


def get_next_roll_number(class_name: str) -> str:
    """Return the next numeric roll number for a class."""
    if not class_name:
        return "1"
    with engine.connect() as conn:
        rows = conn.execute(
            text("""
                SELECT roll_number FROM students
                WHERE status = 'active'
                  AND class_name = :c
                  AND roll_number IS NOT NULL
            """),
            {"c": class_name.strip()},
        ).fetchall()

    max_num = 0
    for r in rows:
        try:
            n = int(str(r[0]).strip())
            if n > max_num:
                max_num = n
        except (ValueError, TypeError):
            continue

    return str(max_num + 1) if max_num > 0 else "1"