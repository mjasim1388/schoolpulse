import io
import pandas as pd
from sqlalchemy import text
from db import engine


def _excel_bytes(sheets: dict):
    """Given {sheet_name: DataFrame}, return xlsx bytes."""
    buf = io.BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as writer:
        for name, df in sheets.items():
            df.to_excel(writer, sheet_name=name[:31], index=False)
    buf.seek(0)
    return buf.getvalue()


def _grade(pct):
    if pct >= 90: return "A+"
    if pct >= 80: return "A"
    if pct >= 70: return "B"
    if pct >= 60: return "C"
    if pct >= 50: return "D"
    if pct >= 40: return "E"
    return "F"


# ============================================================
# STUDENTS EXPORT
# ============================================================
def students_to_excel():
    """Export all active students to a single-sheet xlsx."""
    sql = """
        SELECT
            roll_number AS "Roll No",
            full_name AS "Name",
            class_name AS "Class",
            section AS "Section",
            parent_name AS "Parent",
            parent_phone AS "Contact",
            monthly_fee AS "Monthly Fee"
        FROM students
        WHERE status = 'active'
        ORDER BY
            class_name,
            CASE WHEN roll_number ~ '^[0-9]+$' THEN CAST(roll_number AS INTEGER) ELSE 999999 END,
            roll_number
    """
    with engine.connect() as conn:
        df = pd.read_sql(text(sql), conn)

    # Tidy column types for Excel
    df["Roll No"] = df["Roll No"].astype(str)
    df["Contact"] = df["Contact"].astype(str)
    df["Monthly Fee"] = pd.to_numeric(df["Monthly Fee"], errors="coerce").fillna(0)

    return _excel_bytes({"Students": df})


# ============================================================
# FEES EXPORT (3 sheets)
# ============================================================
def fees_to_excel(month: str, month_label: str = None):
    """Export fee summary, payments, and defaulters for a month."""
    label = month_label or month

    # Summary
    summary_sql = """
        SELECT
            (SELECT COUNT(*) FROM students WHERE status='active') AS "Total Students",
            (SELECT COALESCE(SUM(monthly_fee),0) FROM students WHERE status='active') AS "Expected (Rs)",
            (SELECT COALESCE(SUM(amount),0) FROM fee_payments WHERE month=:m) AS "Collected (Rs)",
            (SELECT COUNT(DISTINCT student_id) FROM fee_payments WHERE month=:m) AS "Paid Count"
    """
    with engine.connect() as conn:
        summary = pd.read_sql(text(summary_sql), conn, params={"m": month})

    summary["Pending (Rs)"] = summary["Expected (Rs)"] - summary["Collected (Rs)"]
    summary["Unpaid Count"] = summary["Total Students"] - summary["Paid Count"]
    summary.insert(0, "Month", label)

    # Payments
    payments_sql = """
        SELECT
            s.roll_number AS "Roll No",
            s.full_name AS "Student",
            s.class_name AS "Class",
            s.section AS "Section",
            fp.amount AS "Amount (Rs)",
            fp.paid_on AS "Paid On",
            fp.method AS "Method",
            fp.note AS "Note"
        FROM fee_payments fp
        JOIN students s ON s.id = fp.student_id
        WHERE fp.month = :m
        ORDER BY fp.paid_on DESC, s.full_name
    """
    with engine.connect() as conn:
        payments = pd.read_sql(text(payments_sql), conn, params={"m": month})

    payments["Roll No"] = payments["Roll No"].astype(str)

    # Defaulters
    defaulters_sql = """
        SELECT
            s.roll_number AS "Roll No",
            s.full_name AS "Student",
            s.class_name AS "Class",
            s.section AS "Section",
            s.parent_name AS "Parent",
            s.parent_phone AS "Contact",
            s.monthly_fee AS "Fee (Rs)"
        FROM students s
        WHERE s.status = 'active'
          AND NOT EXISTS (
              SELECT 1 FROM fee_payments fp
              WHERE fp.student_id = s.id AND fp.month = :m
          )
        ORDER BY s.class_name, s.full_name
    """
    with engine.connect() as conn:
        defaulters = pd.read_sql(text(defaulters_sql), conn, params={"m": month})

    defaulters["Roll No"] = defaulters["Roll No"].astype(str)
    defaulters["Contact"] = defaulters["Contact"].astype(str)

    return _excel_bytes({
        "Summary": summary,
        "Payments": payments,
        "Defaulters": defaulters,
    })


# ============================================================
# CLASS RESULTS EXPORT (2 sheets)
# ============================================================
def class_results_to_excel(exam_id: int, class_name: str, exam_name: str = ""):
    """Export marks grid + results summary for one class in one exam."""
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

        students = conn.execute(
            text("""
                SELECT id, full_name, roll_number, section
                FROM students
                WHERE status = 'active' AND class_name = :c
                ORDER BY
                    CASE WHEN roll_number ~ '^[0-9]+$' THEN CAST(roll_number AS INTEGER) ELSE 999999 END,
                    roll_number
            """),
            {"c": class_name},
        ).fetchall()

        marks_rows = conn.execute(
            text("""
                SELECT m.student_id, m.subject_id, m.marks_obtained, m.is_absent
                FROM marks m
                JOIN exam_subjects es ON es.id = m.subject_id
                WHERE m.exam_id = :e AND es.class_name = :c
            """),
            {"e": exam_id, "c": class_name},
        ).fetchall()

    marks_lookup = {}
    for r in marks_rows:
        marks_lookup[(r[0], r[1])] = (r[2], bool(r[3]))

    subject_list = [dict(s._mapping) for s in subjects]
    student_list = [dict(s._mapping) for s in students]

    # ---- Sheet 1: Marks grid ----
    grid_rows = []
    for s in student_list:
        row = {
            "Roll No": str(s["roll_number"] or ""),
            "Name": s["full_name"],
            "Section": s["section"] or "",
        }
        for sub in subject_list:
            key = (s["id"], sub["id"])
            if key in marks_lookup:
                marks, absent = marks_lookup[key]
                if absent:
                    row[f"{sub['subject_name']} ({sub['max_marks']})"] = "Absent"
                elif marks is not None:
                    row[f"{sub['subject_name']} ({sub['max_marks']})"] = float(marks)
                else:
                    row[f"{sub['subject_name']} ({sub['max_marks']})"] = ""
            else:
                row[f"{sub['subject_name']} ({sub['max_marks']})"] = ""
        grid_rows.append(row)

    grid_df = pd.DataFrame(grid_rows)

    # ---- Sheet 2: Results summary ----
    summary_rows = []
    for s in student_list:
        total_obtained = 0.0
        total_max = 0
        passed = 0
        failed = 0
        absent_count = 0

        for sub in subject_list:
            key = (s["id"], sub["id"])
            if key not in marks_lookup:
                continue
            marks, absent = marks_lookup[key]
            if absent:
                absent_count += 1
                continue
            m_val = float(marks or 0)
            total_obtained += m_val
            total_max += sub["max_marks"]
            if m_val >= sub["pass_marks"]:
                passed += 1
            else:
                failed += 1

        pct = (total_obtained / total_max * 100) if total_max else 0.0

        summary_rows.append({
            "Roll No": str(s["roll_number"] or ""),
            "Name": s["full_name"],
            "Section": s["section"] or "",
            "Total": round(total_obtained, 0),
            "Out Of": total_max,
            "Percentage": round(pct, 1),
            "Grade": _grade(pct),
            "Subjects Passed": passed,
            "Subjects Failed": failed,
            "Absent Subjects": absent_count,
        })

    summary_df = pd.DataFrame(summary_rows)

    if not summary_df.empty:
        summary_df["Position"] = (
            summary_df["Total"].rank(method="min", ascending=False).astype(int)
        )
        cols = [
            "Position", "Roll No", "Name", "Section",
            "Total", "Out Of", "Percentage", "Grade",
            "Subjects Passed", "Subjects Failed", "Absent Subjects",
        ]
        summary_df = summary_df[cols]
        summary_df = summary_df.sort_values("Position")

    return _excel_bytes({
        "Marks Grid": grid_df,
        "Results": summary_df,
    })