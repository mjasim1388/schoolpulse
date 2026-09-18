import streamlit as st
import pandas as pd

from exams import (
    get_all_exams,
    get_subjects_for_exam,
    get_classes_with_subjects,
    get_marks_for_subject,
    save_marks_bulk,
)
from students import get_all_students
from ui import _html


def page_header(title, subtitle=""):
    sub = f'<div class="page-subtitle">{subtitle}</div>' if subtitle else ""
    st.markdown(_html(f"""
        <div class="page-header">
            <div class="page-title">{title}</div>
            {sub}
        </div>
    """), unsafe_allow_html=True)


def render():
    page_header("Enter Marks", "Type in marks per subject. Save all at once.")

    exams = get_all_exams()
    if not exams:
        st.info("No exams created yet. Go to **Exams** first to create one.")
        return

    # ---- Exam picker ----
    exam_options = {
        f"{e['name']}" + (f" · {e['term']}" if e.get("term") else ""): e["id"]
        for e in exams
    }

    c1, c2, c3 = st.columns([2, 2, 2])

    with c1:
        picked_exam_label = st.selectbox(
            "Exam",
            list(exam_options.keys()),
            key="marks_exam",
        )
        exam_id = exam_options[picked_exam_label]

    classes = get_classes_with_subjects(exam_id)
    if not classes:
        st.warning("This exam has no subjects yet.")
        return

    with c2:
        picked_class = st.selectbox("Class", classes, key="marks_class")

    subjects = get_subjects_for_exam(exam_id, picked_class)
    if not subjects:
        st.warning("No subjects for this class.")
        return

    subject_options = {
        f"{s['subject_name']} (max {s['max_marks']}, pass {s['pass_marks']})": s
        for s in subjects
    }

    with c3:
        picked_subject_label = st.selectbox(
            "Subject",
            list(subject_options.keys()),
            key="marks_subject",
        )
        picked_subject = subject_options[picked_subject_label]

    st.markdown("<div class='soft-divider'></div>", unsafe_allow_html=True)

    all_students = get_all_students()
    students_in_class = [s for s in all_students if s["class_name"] == picked_class]

    if not students_in_class:
        st.info(f"No active students in {picked_class}.")
        return

    def sort_key(s):
        rn = str(s.get("roll_number") or "")
        try:
            return (0, int(rn))
        except ValueError:
            return (1, rn)

    students_in_class.sort(key=sort_key)

    existing = get_marks_for_subject(exam_id, picked_subject["id"])

    entered = sum(
        1 for s in students_in_class
        if s["id"] in existing and (
            existing[s["id"]]["marks_obtained"] is not None
            or existing[s["id"]]["is_absent"]
        )
    )
    total = len(students_in_class)

    max_m = int(picked_subject["max_marks"])

    # ---- Info cards ----
    c1, c2, c3 = st.columns(3)
    with c1:
        st.markdown(_html(f"""
            <div class="kpi-card">
                <div class="kpi-label">Subject</div>
                <div class="kpi-value" style="font-size:18px;">{picked_subject['subject_name']}</div>
            </div>
        """), unsafe_allow_html=True)
    with c2:
        st.markdown(_html(f"""
            <div class="kpi-card">
                <div class="kpi-label">Max / Pass</div>
                <div class="kpi-value" style="font-size:18px;">{max_m} / {picked_subject['pass_marks']}</div>
            </div>
        """), unsafe_allow_html=True)
    with c3:
        accent = "#059669" if entered == total else ("#f59e0b" if entered > 0 else "#dc2626")
        st.markdown(_html(f"""
            <div class="kpi-card">
                <div class="kpi-label">Progress</div>
                <div class="kpi-value" style="font-size:18px; color:{accent};">{entered} / {total}</div>
            </div>
        """), unsafe_allow_html=True)

    st.markdown("<div style='height: 16px;'></div>", unsafe_allow_html=True)

    # ---- Entry form ----
    with st.form(key=f"marks_form_{exam_id}_{picked_subject['id']}"):
        st.markdown(_html("""
            <div class="section-heading">Enter marks</div>
        """), unsafe_allow_html=True)

        st.caption(
            "Type each student's marks. Press **Enter** or **Tab** to move to the "
            "next student. Tick **Absent** where needed. Click **Save all marks** at the end."
        )

        # Header row
        h1, h2, h3 = st.columns([4, 2, 1.2])
        with h1:
            st.markdown(_html("""
                <div style='font-size:12px; font-weight:600; color:#64748b;'>Student</div>
            """), unsafe_allow_html=True)
        with h2:
            st.markdown(_html(f"""
                <div style='font-size:12px; font-weight:600; color:#64748b;'>Marks (out of {max_m})</div>
            """), unsafe_allow_html=True)
        with h3:
            st.markdown(_html("""
                <div style='font-size:12px; font-weight:600; color:#64748b;'>Absent</div>
            """), unsafe_allow_html=True)

        rows = []

        for st_row in students_in_class:
            existing_mark = existing.get(st_row["id"])
            current_val = None
            current_absent = False
            if existing_mark:
                current_val = existing_mark["marks_obtained"]
                current_absent = existing_mark["is_absent"]

            c1, c2, c3 = st.columns([4, 2, 1.2])

            with c1:
                label = f"{st_row['full_name']}"
                if st_row.get("roll_number"):
                    label += f"  ·  Roll {st_row['roll_number']}"
                st.markdown(_html(f"""
                    <div style='padding-top:8px; font-size:14px; color:#0f172a;'>{label}</div>
                """), unsafe_allow_html=True)

            with c2:
                marks_val = st.number_input(
                    "Marks",
                    min_value=0.0,
                    max_value=float(max_m),
                    step=1.0,
                    value=float(current_val) if current_val is not None else None,
                    placeholder=f"0 – {max_m}",
                    format="%.0f",
                    key=f"m_{st_row['id']}",
                    label_visibility="collapsed",
                )

            with c3:
                is_absent = st.checkbox(
                    "Absent",
                    value=current_absent,
                    key=f"abs_{st_row['id']}",
                    label_visibility="collapsed",
                )

            rows.append({
                "student_id": st_row["id"],
                "marks_obtained": marks_val,
                "is_absent": is_absent,
            })

        st.markdown("<div style='height: 8px;'></div>", unsafe_allow_html=True)

        submitted = st.form_submit_button(
            "Save all marks", use_container_width=True
        )

        if submitted:
            # Only save rows that have a value or are marked absent
            clean_rows = []
            for r in rows:
                if r["is_absent"] or r["marks_obtained"] is not None:
                    clean_rows.append({
                        "student_id": r["student_id"],
                        "marks_obtained": r["marks_obtained"] if r["marks_obtained"] is not None else 0.0,
                        "is_absent": r["is_absent"],
                    })

            if not clean_rows:
                st.warning("No marks entered yet.")
            else:
                save_marks_bulk(exam_id, picked_subject["id"], clean_rows)
                st.success(f"Saved marks for {len(clean_rows)} students.")
                st.rerun()

    # ---- Auto-advance: Enter moves to next input, no submit ----
    st.markdown(_html("""
        <script>
        (function() {
            function setupAutoAdvance() {
                try {
                    const doc = window.parent.document;
                    const inputs = Array.from(doc.querySelectorAll('input[type="number"]'));

                    inputs.forEach(function(inp) {
                        if (inp.dataset.autoAdvance === 'true') return;
                        inp.dataset.autoAdvance = 'true';

                        // Press Enter → focus next number input
                        inp.addEventListener('keydown', function(e) {
                            if (e.key === 'Enter') {
                                e.preventDefault();
                                e.stopPropagation();
                                const all = Array.from(doc.querySelectorAll('input[type="number"]'));
                                const i = all.indexOf(inp);
                                if (i >= 0 && i < all.length - 1) {
                                    all[i + 1].focus();
                                    all[i + 1].select();
                                }
                            }
                        });

                        // On focus → select existing value so typing replaces it
                        inp.addEventListener('focus', function() {
                            if (inp.value && inp.value !== '') {
                                inp.select();
                            }
                        });
                    });
                } catch (e) {}
            }
            setupAutoAdvance();
            setInterval(setupAutoAdvance, 800);
        })();
        </script>
    """), unsafe_allow_html=True)