import streamlit as st
from datetime import date
from sqlalchemy import text
from db import engine


def current_month_str():
    """Return current month in YYYY-MM format."""
    today = date.today()
    return f"{today.year}-{today.month:02d}"


def month_str(d):
    """Convert a date object to YYYY-MM."""
    return f"{d.year}-{d.month:02d}"


def recent_months(n=12):
    """Return the last n months as ['YYYY-MM', ...], newest first."""
    today = date.today()
    months = []
    y, m = today.year, today.month
    for _ in range(n):
        months.append(f"{y}-{m:02d}")
        m -= 1
        if m == 0:
            m = 12
            y -= 1
    return months


def record_payment(student_id: int, amount: float, month: str, method: str = "cash", note: str = ""):
    """Insert a payment record."""
    with engine.connect() as conn:
        conn.execute(
            text("""
                INSERT INTO fee_payments (student_id, amount, month, paid_on, method, note)
                VALUES (:sid, :amount, :month, CURRENT_DATE, :method, :note)
            """),
            {
                "sid": student_id,
                "amount": float(amount),
                "month": month,
                "method": method,
                "note": (note or "").strip(),
            },
        )
        conn.commit()
    st.cache_data.clear()    
    return True

@st.cache_data(ttl=120, show_spinner=False)
def has_paid(student_id: int, month: str):

    """Return True if the student has any payment for this month."""
    with engine.connect() as conn:
        row = conn.execute(
            text("""
                SELECT 1 FROM fee_payments
                WHERE student_id = :sid AND month = :month
                LIMIT 1
            """),
            {"sid": student_id, "month": month},
        ).fetchone()
    return row is not None

@st.cache_data(ttl=120, show_spinner=False)
def get_payments_for_month(month: str):
    """Return all payments for the given month, joined with student info."""
    with engine.connect() as conn:
        rows = conn.execute(
            text("""
                SELECT
                    fp.id,
                    fp.student_id,
                    s.full_name,
                    s.class_name,
                    s.section,
                    fp.amount,
                    fp.paid_on,
                    fp.method,
                    fp.note
                FROM fee_payments fp
                JOIN students s ON s.id = fp.student_id
                WHERE fp.month = :month
                ORDER BY fp.paid_on DESC, s.full_name
            """),
            {"month": month},
        ).fetchall()
    return [dict(r._mapping) for r in rows]

@st.cache_data(ttl=120, show_spinner=False)
def get_defaulters(month: str):
    """Return active students who have NOT paid the given month."""
    with engine.connect() as conn:
        rows = conn.execute(
            text("""
                SELECT
                    s.id,
                    s.full_name,
                    s.roll_number,
                    s.class_name,
                    s.section,
                    s.parent_name,
                    s.parent_phone,
                    s.monthly_fee
                FROM students s
                WHERE s.status = 'active'
                  AND NOT EXISTS (
                      SELECT 1 FROM fee_payments fp
                      WHERE fp.student_id = s.id AND fp.month = :month
                  )
                ORDER BY s.class_name, s.full_name
            """),
            {"month": month},
        ).fetchall()
    return [dict(r._mapping) for r in rows]

@st.cache_data(ttl=120, show_spinner=False)
def month_summary(month: str):
    """Return {collected, expected, pending, paid_count, total_students}."""
    with engine.connect() as conn:
        collected = conn.execute(
            text("SELECT COALESCE(SUM(amount), 0) FROM fee_payments WHERE month = :m"),
            {"m": month},
        ).scalar()

        total_students = conn.execute(
            text("SELECT COUNT(*) FROM students WHERE status = 'active'")
        ).scalar()

        expected = conn.execute(
            text("SELECT COALESCE(SUM(monthly_fee), 0) FROM students WHERE status = 'active'")
        ).scalar()

        paid_count = conn.execute(
            text("""
                SELECT COUNT(DISTINCT student_id) FROM fee_payments WHERE month = :m
            """),
            {"m": month},
        ).scalar()

    collected = float(collected or 0)
    expected = float(expected or 0)
    pending = max(expected - collected, 0)
    return {
        "collected": collected,
        "expected": expected,
        "pending": pending,
        "paid_count": int(paid_count or 0),
        "total_students": int(total_students or 0),
    }

@st.cache_data(ttl=120, show_spinner=False)
def payments_by_month(months: list):
    """Return list of {month, collected} for the given months (oldest first)."""
    if not months:
        return []
    with engine.connect() as conn:
        rows = conn.execute(
            text("""
                SELECT month, COALESCE(SUM(amount), 0) AS collected
                FROM fee_payments
                WHERE month = ANY(:months)
                GROUP BY month
            """),
            {"months": months},
        ).fetchall()
    data = {r[0]: float(r[1]) for r in rows}
    return [{"month": m, "collected": data.get(m, 0.0)} for m in sorted(months)]


def delete_payment(payment_id: int):
    """Delete a payment record."""
    with engine.connect() as conn:
        conn.execute(text("DELETE FROM fee_payments WHERE id = :id"), {"id": payment_id})
        conn.commit()
    st.cache_data.clear()    
    return True