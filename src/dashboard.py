import streamlit as st
from sqlalchemy import text
from db import engine


@st.cache_data(ttl=180, show_spinner=False)
def get_dashboard_snapshot(month: str):
    """
    One round-trip for all dashboard headline numbers.
    Returns a single dict with everything the KPI row needs.
    """
    sql = """
    SELECT
        (SELECT COUNT(*) FROM students WHERE status = 'active') AS total_students,
        (SELECT COUNT(DISTINCT class_name) FROM students WHERE status = 'active') AS total_classes,
        (SELECT COALESCE(SUM(monthly_fee), 0) FROM students WHERE status = 'active') AS monthly_fee_roll,
        (SELECT COALESCE(SUM(amount), 0) FROM fee_payments WHERE month = :m) AS collected,
        (SELECT COUNT(DISTINCT student_id) FROM fee_payments WHERE month = :m) AS paid_count
    """
    with engine.connect() as conn:
        row = conn.execute(text(sql), {"m": month}).fetchone()

    data = dict(row._mapping)
    collected = float(data["collected"] or 0)
    expected = float(data["monthly_fee_roll"] or 0)
    paid_count = int(data["paid_count"] or 0)
    total_students = int(data["total_students"] or 0)

    return {
        "total_students": total_students,
        "total_classes": int(data["total_classes"] or 0),
        "monthly_fee_roll": expected,
        "collected": collected,
        "paid_count": paid_count,
        "unpaid_count": max(total_students - paid_count, 0),
        "pending": max(expected - collected, 0),
    }


@st.cache_data(ttl=120, show_spinner=False)
def get_6month_trend():
    """Return list of {month, label, collected} for last 6 months."""
    from fees import recent_months

    months = sorted(recent_months(6))
    with engine.connect() as conn:
        rows = conn.execute(
            text("""
                SELECT month, COALESCE(SUM(amount),0) AS collected
                FROM fee_payments
                WHERE month = ANY(:months)
                GROUP BY month
            """),
            {"months": months},
        ).fetchall()

    data = {r[0]: float(r[1]) for r in rows}
    names = ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
             "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
    result = []
    for m in months:
        y, mo = m.split("-")
        result.append({
            "month": m,
            "label": f"{names[int(mo)-1]} {y[2:]}",
            "collected": data.get(m, 0.0),
        })
    return result


@st.cache_data(ttl=120, show_spinner=False)
def get_students_per_class():
    """Return list of {class_name, count}."""
    with engine.connect() as conn:
        rows = conn.execute(
            text("""
                SELECT class_name, COUNT(*) AS n
                FROM students
                WHERE status = 'active'
                GROUP BY class_name
                ORDER BY class_name
            """)
        ).fetchall()
    return [{"class_name": r[0], "count": int(r[1])} for r in rows]


@st.cache_data(ttl=120, show_spinner=False)
def get_top_defaulters(month: str, limit: int = 5):
    """Return list of top defaulters by fee amount for a month."""
    with engine.connect() as conn:
        rows = conn.execute(
            text("""
                SELECT
                    s.full_name,
                    s.class_name,
                    s.section,
                    s.parent_phone,
                    s.monthly_fee
                FROM students s
                WHERE s.status = 'active'
                  AND NOT EXISTS (
                      SELECT 1 FROM fee_payments fp
                      WHERE fp.student_id = s.id AND fp.month = :m
                  )
                ORDER BY s.monthly_fee DESC, s.full_name
                LIMIT :lim
            """),
            {"m": month, "lim": limit},
        ).fetchall()
    return [dict(r._mapping) for r in rows]


@st.cache_data(ttl=120, show_spinner=False)
def get_recent_payments(limit: int = 8):
    """Return most recent payments across all months."""
    with engine.connect() as conn:
        rows = conn.execute(
            text("""
                SELECT
                    s.full_name,
                    s.class_name,
                    s.section,
                    fp.amount,
                    fp.paid_on,
                    fp.month,
                    fp.method
                FROM fee_payments fp
                JOIN students s ON s.id = fp.student_id
                ORDER BY fp.created_at DESC
                LIMIT :lim
            """),
            {"lim": limit},
        ).fetchall()
    return [dict(r._mapping) for r in rows]