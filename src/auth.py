import bcrypt
from sqlalchemy import text
from db import engine


def hash_password(password: str) -> str:
    """Hash a plain password using bcrypt."""
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(password.encode("utf-8"), salt)
    return hashed.decode("utf-8")


def verify_password(password: str, password_hash: str) -> bool:
    """Check a plain password against a stored hash."""
    try:
        return bcrypt.checkpw(
            password.encode("utf-8"),
            password_hash.encode("utf-8"),
        )
    except Exception:
        return False


def create_user(full_name: str, email: str, password: str, role: str = "admin"):
    """Insert a new user into the database."""
    password_hash = hash_password(password)
    with engine.connect() as conn:
        conn.execute(
            text("""
                INSERT INTO users (full_name, email, password_hash, role)
                VALUES (:name, :email, :hash, :role)
            """),
            {"name": full_name, "email": email.lower(), "hash": password_hash, "role": role},
        )
        conn.commit()
    return True


def authenticate(email: str, password: str):
    """Return user dict if credentials are valid, else None."""
    with engine.connect() as conn:
        row = conn.execute(
            text("""
                SELECT id, full_name, email, password_hash, role
                FROM users
                WHERE email = :email
                LIMIT 1
            """),
            {"email": email.lower().strip()},
        ).fetchone()

    if row is None:
        return None

    user = dict(row._mapping)
    if not verify_password(password, user["password_hash"]):
        return None

    # Don't return the hash to the caller
    user.pop("password_hash", None)
    return user


def user_exists(email: str) -> bool:
    """Check if a user with this email already exists."""
    with engine.connect() as conn:
        row = conn.execute(
            text("SELECT 1 FROM users WHERE email = :email LIMIT 1"),
            {"email": email.lower().strip()},
        ).fetchone()
    return row is not None