import os
from pathlib import Path
from dotenv import load_dotenv
from sqlalchemy import create_engine, text

# Try Streamlit secrets first (for cloud deployment)
DATABASE_URL = None
try:
    import streamlit as st
    DATABASE_URL = st.secrets.get("DATABASE_URL")
except Exception:
    DATABASE_URL = None

# Fall back to .env (for local development)
if not DATABASE_URL:
    env_path = Path(__file__).resolve().parent.parent / ".env"
    load_dotenv(dotenv_path=env_path)
    DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    raise ValueError("DATABASE_URL not found in .env or Streamlit secrets")

engine = create_engine(
    DATABASE_URL,
    echo=False,
    pool_size=5,
    max_overflow=10,
    pool_pre_ping=True,
    pool_recycle=280,
    connect_args={
        "keepalives": 1,
        "keepalives_idle": 30,
        "keepalives_interval": 10,
        "keepalives_count": 5,
    },
)


def test_connection():
    with engine.connect() as conn:
        result = conn.execute(text("SELECT version();"))
        print("Connected to:")
        print(result.fetchone()[0])


def run_sql_file(path):
    with open(path, "r", encoding="utf-8") as f:
        sql = f.read()
    with engine.connect() as conn:
        conn.execute(text(sql))
        conn.commit()
    print(f"Executed {path}")


if __name__ == "__main__":
    test_connection()