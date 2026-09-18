import io
import re
import pandas as pd
from sqlalchemy import text
from db import engine
from students import get_class_fee, set_class_fee, get_next_roll_number


# ============================================================
# Required and optional fields for a student import
# ============================================================
REQUIRED_FIELDS = ["full_name", "class_name"]
OPTIONAL_FIELDS = [
    "roll_number", "section", "parent_name",
    "parent_phone", "monthly_fee",
]

ALL_FIELDS = REQUIRED_FIELDS + OPTIONAL_FIELDS

FIELD_LABELS = {
    "full_name": "Student name",
    "class_name": "Class",
    "roll_number": "Roll number",
    "section": "Section",
    "parent_name": "Parent / guardian name",
    "parent_phone": "Parent contact",
    "monthly_fee": "Monthly fee (Rs)",
}

# Common synonyms found in school Excel files
AUTO_DETECT = {
    "full_name": [
        "name", "student name", "student_name", "studentname", "full name",
        "full_name", "fullname", "student", "naam", "students name",
    ],
    "class_name": [
        "class", "class_name", "classname", "grade", "standard",
        "class name", "std", "darja",
    ],
    "roll_number": [
        "roll", "roll no", "roll_no", "rollno", "roll number",
        "roll_number", "rollno.", "roll no.", "sr", "sr no", "serial",
    ],
    "section": [
        "section", "sec", "division", "div", "branch",
    ],
    "parent_name": [
        "parent", "parent name", "parent_name", "parentname",
        "father", "father name", "father_name", "guardian",
        "guardian name", "guardian_name", "walid", "walid name",
    ],
    "parent_phone": [
        "phone", "contact", "parent phone", "parent_phone", "parentphone",
        "mobile", "phone no", "phone_no", "contact number", "contact_no",
        "father phone", "father_phone", "cell", "cell no", "whatsapp",
    ],
    "monthly_fee": [
        "fee", "monthly fee", "monthly_fee", "monthlyfee", "fees",
        "fee amount", "amount", "fees (rs)", "fee (rs)", "tuition",
        "tuition fee", "fees amount",
    ],
}


# ============================================================
# FILE READING
# ============================================================
def read_file(uploaded_file):
    """
    Read a CSV or XLSX file into a DataFrame.
    Returns (df, error_message). df is None if error.
    """
    name = uploaded_file.name.lower()
    try:
        if name.endswith(".csv"):
            df = pd.read_csv(uploaded_file)
        elif name.endswith(".xlsx") or name.endswith(".xls"):
            df = pd.read_excel(uploaded_file, engine="openpyxl")
        else:
            return None, "Unsupported file type. Please upload .csv, .xlsx, or .xls."

        if df.empty:
            return None, "The file is empty."

        # Strip whitespace from column names
        df.columns = [str(c).strip() for c in df.columns]
        return df, None

    except Exception as e:
        return None, f"Could not read file: {e}"


# ============================================================
# COLUMN AUTO-DETECTION
# ============================================================
def auto_detect_mapping(columns):
    """
    Given a list of DataFrame columns, return {required_field: actual_column}
    based on common synonyms.
    """
    lower = {str(c).strip().lower(): c for c in columns}
    result = {}

    for field, synonyms in AUTO_DETECT.items():
        # Exact match first
        if field in lower:
            result[field] = lower[field]
            continue
        # Synonym match
        for syn in synonyms:
            if syn in lower:
                result[field] = lower[syn]
                break
        # Partial match (substring)
        if field not in result:
            for key, orig in lower.items():
                if any(syn in key for syn in synonyms):
                    result[field] = orig
                    break

    return result


# ============================================================
# DATA CLEANING
# ============================================================
def clean_phone(val):
    """Convert to string, keep digits and basic characters."""
    if pd.isna(val):
        return ""
    s = str(val).strip()
    # Remove trailing .0 from float conversion
    if s.endswith(".0"):
        s = s[:-2]
    return s


def clean_fee(val):
    """Convert to float, stripping currency symbols and commas."""
    if pd.isna(val):
        return 0.0
    if isinstance(val, (int, float)):
        return float(val)
    s = str(val)
    s = re.sub(r"[^\d.\-]", "", s)
    try:
        return float(s) if s else 0.0
    except ValueError:
        return 0.0


def clean_text(val):
    if pd.isna(val):
        return ""
    return str(val).strip()


# ============================================================
# VALIDATION + PREVIEW
# ============================================================
def build_preview(df, mapping):
    """
    Given a DataFrame and a {field: column} mapping, return a cleaned DataFrame
    with standard field names, plus a list of row errors.
    """
    rows = []
    errors = []
    seen = set()

    for idx, row in df.iterrows():
        excel_row = idx + 2  # +2 because row 1 is header
        record = {}

        for field in ALL_FIELDS:
            src_col = mapping.get(field)
            val = row[src_col] if src_col else None

            if field == "monthly_fee":
                record[field] = clean_fee(val)
            elif field == "parent_phone":
                record[field] = clean_phone(val)
            else:
                record[field] = clean_text(val)

        # Validations
        if not record["full_name"]:
            errors.append((excel_row, "Missing student name"))
            continue
        if not record["class_name"]:
            errors.append((excel_row, "Missing class"))
            continue

        # Skip exact duplicates within the file itself
        key = (record["full_name"].lower(), record["class_name"].lower())
        if key in seen:
            errors.append((excel_row, f"Duplicate of another row ({record['full_name']})"))
            continue
        seen.add(key)

        # Ensure the field order in output
        record["_excel_row"] = excel_row
        rows.append(record)

    return pd.DataFrame(rows), errors


# ============================================================
# IMPORT
# ============================================================
def import_students(records, set_class_fee_from_first=True):
    """
    Insert the given records into the students table.
    records: list of dicts with standard field names.
    Returns (inserted_count, skipped_count, class_defaults_set).
    """
    inserted = 0
    skipped = 0
    classes_touched = set()

    with engine.connect() as conn:
        for rec in records:
            full_name = rec["full_name"].strip()
            class_name = rec["class_name"].strip()

            # Skip if student with same name+class already exists
            exists = conn.execute(
                text("""
                    SELECT 1 FROM students
                    WHERE LOWER(full_name) = LOWER(:n)
                      AND LOWER(class_name) = LOWER(:c)
                      AND status = 'active'
                    LIMIT 1
                """),
                {"n": full_name, "c": class_name},
            ).fetchone()

            if exists:
                skipped += 1
                continue

            # Auto-assign roll number if blank
            roll = rec.get("roll_number") or ""
            if not roll:
                roll = get_next_roll_number(class_name)

            fee = float(rec.get("monthly_fee") or 0)

            # If fee is 0 and the class has a default, use it
            if fee == 0:
                cf = get_class_fee(class_name)
                if cf is not None:
                    fee = float(cf)

            conn.execute(
                text("""
                    INSERT INTO students
                        (full_name, roll_number, class_name, section,
                         parent_name, parent_phone, monthly_fee)
                    VALUES
                        (:name, :roll, :class, :section,
                         :parent, :phone, :fee)
                """),
                {
                    "name": full_name,
                    "roll": roll,
                    "class": class_name,
                    "section": rec.get("section", ""),
                    "parent": rec.get("parent_name", ""),
                    "phone": rec.get("parent_phone", ""),
                    "fee": fee,
                },
            )
            inserted += 1
            classes_touched.add(class_name)

        conn.commit()

    # Set class default fees if this class didn't have one yet
    defaults_set = []
    if set_class_fee_from_first:
        for cls in classes_touched:
            if get_class_fee(cls) is None:
                for rec in records:
                    if rec["class_name"].strip() == cls:
                        fee = float(rec.get("monthly_fee") or 0)
                        if fee > 0:
                            set_class_fee(cls, fee)
                            defaults_set.append((cls, fee))
                            break

    # Clear cached queries so the new students show up
    import streamlit as st
    st.cache_data.clear()

    return inserted, skipped, defaults_set