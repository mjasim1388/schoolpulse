import streamlit as st
from sqlalchemy import text
from db import engine


@st.cache_data(ttl=300, show_spinner=False)
def get_school_profile():
    """Return the school profile row as a dict."""
    with engine.connect() as conn:
        row = conn.execute(
            text("""
                SELECT id, school_name, address, phone, email,
                       principal_name, logo_base64, updated_at
                FROM school_profile WHERE id = 1
            """)
        ).fetchone()
    if row is None:
        return {
            "id": 1,
            "school_name": "My School",
            "address": "",
            "phone": "",
            "email": "",
            "principal_name": "",
            "logo_base64": None,
        }
    return dict(row._mapping)


def update_school_profile(
    school_name: str,
    address: str,
    phone: str,
    email: str,
    principal_name: str,
    logo_base64: str = None,
    keep_logo: bool = True,
):
    """Update the school profile. If keep_logo is False, logo is replaced (or cleared)."""
    with engine.connect() as conn:
        if keep_logo:
            conn.execute(
                text("""
                    UPDATE school_profile SET
                        school_name = :n,
                        address = :a,
                        phone = :p,
                        email = :e,
                        principal_name = :pr,
                        updated_at = NOW()
                    WHERE id = 1
                """),
                {
                    "n": school_name.strip() or "My School",
                    "a": (address or "").strip(),
                    "p": (phone or "").strip(),
                    "e": (email or "").strip(),
                    "pr": (principal_name or "").strip(),
                },
            )
        else:
            conn.execute(
                text("""
                    UPDATE school_profile SET
                        school_name = :n,
                        address = :a,
                        phone = :p,
                        email = :e,
                        principal_name = :pr,
                        logo_base64 = :logo,
                        updated_at = NOW()
                    WHERE id = 1
                """),
                {
                    "n": school_name.strip() or "My School",
                    "a": (address or "").strip(),
                    "p": (phone or "").strip(),
                    "e": (email or "").strip(),
                    "pr": (principal_name or "").strip(),
                    "logo": logo_base64,
                },
            )
        conn.commit()

    st.cache_data.clear()
    return True


def change_user_password(user_id: int, current_password: str, new_password: str):
    """Verify current password and set a new one. Returns (ok, message)."""
    from auth import hash_password, verify_password

    with engine.connect() as conn:
        row = conn.execute(
            text("SELECT password_hash FROM users WHERE id = :id"),
            {"id": user_id},
        ).fetchone()

    if row is None:
        return False, "User not found."

    if not verify_password(current_password, row[0]):
        return False, "Current password is incorrect."

    if len(new_password) < 6:
        return False, "New password must be at least 6 characters."

    new_hash = hash_password(new_password)

    with engine.connect() as conn:
        conn.execute(
            text("UPDATE users SET password_hash = :h WHERE id = :id"),
            {"h": new_hash, "id": user_id},
        )
        conn.commit()

    return True, "Password updated successfully."


@st.cache_data(ttl=120, show_spinner=False)
def get_all_class_fees():
    """Return list of {class_name, monthly_fee} from class_fees."""
    with engine.connect() as conn:
        rows = conn.execute(
            text("""
                SELECT class_name, monthly_fee
                FROM class_fees
                ORDER BY class_name
            """)
        ).fetchall()
    return [dict(r._mapping) for r in rows]


def update_class_fee(class_name: str, monthly_fee: float):
    """Update a class's default fee and optionally update students who haven't paid this month."""
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

    st.cache_data.clear()
    return True