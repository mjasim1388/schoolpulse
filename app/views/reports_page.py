from datetime import date

import streamlit as st
import pandas as pd

from exams import (
    get_all_exams,
    get_classes_with_subjects,
    get_report_card_data,
    get_subjects_for_exam,
    get_marks_for_subject,
)
from students import get_all_students
from settings import get_school_profile
from report_cards import build_report_card_pdf, build_bulk_zip
from exports import class_results_to_excel
from ui import _html


def page_header(title, subtitle=""):
    sub = f'<div class="page-subtitle">{subtitle}</div>' if subtitle else ""
    st.markdown(_html(f"""
        <div class="page-header">
            <div class="page-title">{title}</div>
            {sub}
        </div>
    """), unsafe_allow_html=True)


def _student_sort_key(s):
    rn = str(s.get("roll_number") or "")
    try:
        return (0, int(rn))
    except ValueError:
        return (1, rn)


def _prepare_report_data(exam, student):
    data = get_report_card_data(exam["id"], student["id"])
    if not data:
        return None
    data["exam_name"] = exam["name"]
    data["term"] = exam.get("term")
    return data


def render():
    page_header("Reports", "Generate report cards for individual students or an entire class.")

    exams = get_all_exams()
    if not exams:
        st.info("No exams yet. Go to **Exams** first.")
        return

    exam_options = {
        f"{e['name']}" + (f" · {e['term']}" if e.get("term") else ""): e
        for e in exams
    }

    c1, c2 = st.columns([2, 1])
    with c1:
        picked_exam_label = st.selectbox(
            "Exam", list(exam_options.keys()), key="reports_exam"
        )
        exam = exam_options[picked_exam_label]

    classes = get_classes_with_subjects(exam["id"])
    if not classes:
        st.warning(
            "This exam has no subjects configured yet. "
            "Go to **Exams** to add subjects first."
        )
        return

    with c2:
        picked_class = st.selectbox("Class", classes, key="reports_class")

    st.markdown("<div class='soft-divider'></div>", unsafe_allow_html=True)

    all_students = get_all_students()
    students = [s for s in all_students if s["class_name"] == picked_class]
    students.sort(key=_student_sort_key)

    if not students:
        st.info(f"No active students in {picked_class}.")
        return

    subjects = get_subjects_for_exam(exam["id"], picked_class)
    if not subjects:
        st.warning("No subjects for this class in this exam.")
        return

    subject_coverage = []
    for sub in subjects:
        marks = get_marks_for_subject(exam["id"], sub["id"])
        entered = sum(
            1 for s in students
            if s["id"] in marks and (
                marks[s["id"]]["marks_obtained"] is not None
                or marks[s["id"]]["is_absent"]
            )
        )
        subject_coverage.append({
            "subject": sub["subject_name"],
            "entered": entered,
            "total": len(students),
        })

    df_cov = pd.DataFrame(subject_coverage)
    df_cov["progress"] = df_cov.apply(
        lambda r: f"{r['entered']}/{r['total']}", axis=1
    )
    df_cov_display = df_cov[["subject", "progress"]].rename(columns={
        "subject": "Subject", "progress": "Marks entered"
    })

    all_complete = all(c["entered"] == c["total"] for c in subject_coverage)

    with st.expander("Marks coverage for this class", expanded=not all_complete):
        st.dataframe(df_cov_display, use_container_width=True, hide_index=True)
        if all_complete:
            st.success("All marks entered. Ready to generate report cards.")
        else:
            st.warning(
                "Some subjects are missing marks. You can still generate, "
                "but report cards will show 0 for missing entries."
            )

    st.markdown("<div class='section-heading'>Generate report cards</div>",
                unsafe_allow_html=True)

    tab_one, tab_all = st.tabs(["Single student", "Whole class"])

    profile = get_school_profile()

    # =====================================================
    # SINGLE STUDENT
    # =====================================================
    with tab_one:
        st.caption("Pick a student and download their report card as a PDF.")

        student_options = {
            f"{s['full_name']}"
            + (f"  ·  Roll {s['roll_number']}" if s.get("roll_number") else ""): s
            for s in students
        }

        picked_label = st.selectbox(
            "Student", list(student_options.keys()), key="report_single_student"
        )
        picked = student_options[picked_label]

        if st.button("Generate report card", key="gen_single", use_container_width=True):
            data = _prepare_report_data(exam, picked)
            if not data:
                st.error("No data for this student.")
            else:
                pdf = build_report_card_pdf(data, profile)
                roll = picked.get("roll_number") or "no-roll"
                safe_name = "".join(
                    c for c in picked["full_name"] if c.isalnum() or c in " _-"
                ).strip()
                filename = f"{roll}_{safe_name}_report.pdf"

                st.download_button(
                    label="Download report card (PDF)",
                    data=pdf,
                    file_name=filename,
                    mime="application/pdf",
                    use_container_width=True,
                )
                st.success(f"Ready: {picked['full_name']}")

                c1, c2, c3, c4 = st.columns(4)
                c1.metric("Total marks", f"{data['total_obtained']:.0f} / {data['total_max']}")
                c2.metric("Percentage", f"{data['percentage']:.1f}%")
                c3.metric("Grade", data["grade"])
                pos = (
                    f"{data['position']} of {data['total_in_class']}"
                    if data.get("position") else "-"
                )
                c4.metric("Position", pos)

    # =====================================================
    # WHOLE CLASS
    # =====================================================
    with tab_all:
        st.caption(
            f"Generate report cards for all {len(students)} students in "
            f"**{picked_class}** as a ZIP of PDFs."
        )

        # ---- Export results to Excel ----
        exp_l, exp_r = st.columns([4, 1])
        with exp_r:
            xlsx = class_results_to_excel(
                exam["id"], picked_class, exam.get("name", "")
            )
            class_safe = picked_class.replace(" ", "_")
            st.download_button(
                "Export Excel",
                data=xlsx,
                file_name=f"results_{class_safe}_{date.today().isoformat()}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True,
                key="export_results_btn",
            )

        if not all_complete:
            st.warning(
                "Some subjects are missing marks. Missing entries will appear "
                "as 0 in the report cards."
            )

        if st.button(
            f"Generate all {len(students)} report cards",
            key="gen_all",
            use_container_width=True,
        ):
            with st.spinner(f"Building {len(students)} report cards..."):
                all_data = []
                for s in students:
                    rd = _prepare_report_data(exam, s)
                    if rd:
                        all_data.append(rd)

            if not all_data:
                st.error("No report card data could be built.")
            else:
                zip_bytes = build_bulk_zip(all_data, profile)
                class_safe = "".join(
                    c for c in picked_class if c.isalnum() or c in " _-"
                ).strip().replace(" ", "_")
                exam_safe = "".join(
                    c for c in exam["name"] if c.isalnum() or c in " _-"
                ).strip().replace(" ", "_")
                filename = f"report_cards_{class_safe}_{exam_safe}.zip"

                st.download_button(
                    label=f"Download {len(all_data)} report cards (ZIP)",
                    data=zip_bytes,
                    file_name=filename,
                    mime="application/zip",
                    use_container_width=True,
                )
                st.success(
                    f"Ready: {len(all_data)} report cards zipped for {picked_class}."
                )