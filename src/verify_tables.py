from db import engine
from sqlalchemy import text

sql = """
SELECT table_name
FROM information_schema.tables
WHERE table_schema = 'public'
ORDER BY table_name
"""

with engine.connect() as conn:
    rows = conn.execute(text(sql)).fetchall()

print("Tables in database:")
for r in rows:
    print(f"  - {r[0]}")

expected = ["exams", "exam_subjects", "marks"]
missing = [t for t in expected if t not in [r[0] for r in rows]]

if missing:
    print(f"\n❌ Missing: {missing}")
else:
    print("\n✅ All exam tables exist.")