import warnings
warnings.filterwarnings("ignore")
from exams import get_all_exams, get_report_card_data
from students import get_all_students
from settings import get_school_profile
from report_cards import build_report_card_pdf

if __name__ == "__main__":
    exams = get_all_exams()
    if not exams:
        print("No exams. Create one first.")
        raise SystemExit

    exam = exams[0]
    print(f"Using exam: {exam['name']}")

    students = get_all_students()
    if not students:
        print("No students.")
        raise SystemExit

    student = students[0]
    print(f"Building report for: {student['full_name']}")

    data = get_report_card_data(exam["id"], student["id"])
    if not data:
        print("No data.")
        raise SystemExit

    data["exam_name"] = exam["name"]
    data["term"] = exam.get("term")

    profile = get_school_profile()
    pdf = build_report_card_pdf(data, profile)

    out = f"report_{student['id']}.pdf"
    with open(out, "wb") as f:
        f.write(pdf)

    print(f"Saved: {out} ({len(pdf):,} bytes)")
    print("Open it with your PDF viewer to check the layout.")