from datetime import date

import streamlit as st

from exams import (
    get_all_exams,
    get_exam,
    add_exam,
    set_exam_active,
    delete_exam,
    get_subjects_for_exam,
    get_classes_with_subjects,
    add_subject,
    delete_subject,
    get_subject_progress,
)
from students import get_classes


def page_header(title, subtitle=""):
    st.markdown(
        f"""
        <div class="page-header">
            <div class="page-title">{title}</div>
            {f'<div class="page-subtitle">{subtitle}</div>' if subtitle else ''}
        </div>
        """,
        unsafe_allow_html=True,
    )


def stat_card(label, value, accent="#4338ca"):
    st.markdown(
        f"""
        <div class="kpi-card">
            <div class="kpi-label">{label}</div>
            <div class="kpi-value" style="color:{accent};">{value}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render():
    page_header("Exams", "Create exams, assign subjects, and track marks.")

    exams = get_all_exams()

    # ============================================================
    # CREATE NEW EXAM
    # ============================================================
    with st.expander("Create a new exam", expanded=(len(exams) == 0)):
        with st.form("create_exam_form", clear_on_submit=True):
            c1, c2 = st.columns([2, 1])
            with c1:
                exam_name = st.text_input(
                    "Exam name *",
                    placeholder="e.g. Final Term 2026",
                )
            with c2:
                term = st.text_input(
                    "Term",
                    placeholder="e.g. Final Term",
                )

            c3, c4 = st.columns(2)
            with c3:
                start_date = st.date_input("Start date", value=None, key="exam_start")
            with c4:
                end_date = st.date_input("End date", value=None, key="exam_end")

            submitted = st.form_submit_button(
                "Create exam", use_container_width=True
            )

            if submitted:
                if not exam_name.strip():
                    st.error("Please enter an exam name.")
                else:
                    add_exam(
                        exam_name.strip(),
                        term,
                        start_date if start_date else None,
                        end_date if end_date else None,
                    )
                    st.success(f"Created exam: {exam_name}")
                    st.rerun()

    # ============================================================
    # LIST OF EXAMS
    # ============================================================
    if not exams:
        st.info("No exams yet. Create one above to get started.")
        return

    st.markdown("<div class='section-heading'>All exams</div>", unsafe_allow_html=True)

    # Exam selector
    exam_options = {
        f"{e['name']}"
        + (f" · {e['term']}" if e.get("term") else "")
        + ("  ✓ active" if e["is_active"] else "")
        + f"  (ID {e['id']})": e["id"]
        for e in exams
    }

    selected_label = st.selectbox(
        "Select an exam to manage",
        list(exam_options.keys()),
        key="exam_picker",
    )
    selected_id = exam_options[selected_label]
    selected_exam = get_exam(selected_id)

    if not selected_exam:
        st.error("Exam not found.")
        return

    # Exam actions row
    c1, c2, c3 = st.columns([1, 1, 2])
    with c1:
        if selected_exam["is_active"]:
            if st.button("Deactivate", use_container_width=True, key="deact"):
                set_exam_active(selected_id, False)
                st.rerun()
        else:
            if st.button("Activate", use_container_width=True, key="act"):
                set_exam_active(selected_id, True)
                st.rerun()

    with c2:
        if st.button("Delete exam", use_container_width=True, key="del_exam"):
            st.session_state.confirm_exam_delete = selected_id

    with c3:
        if selected_exam.get("start_date") or selected_exam.get("end_date"):
            dates = []
            if selected_exam.get("start_date"):
                dates.append(f"from {selected_exam['start_date']}")
            if selected_exam.get("end_date"):
                dates.append(f"to {selected_exam['end_date']}")
            st.markdown(
                f"<div style='padding-top:10px; color:#64748b; font-size:13px;'>"
                f"Dates: {' '.join(dates)}</div>",
                unsafe_allow_html=True,
            )

    # Confirm delete
    if st.session_state.get("confirm_exam_delete") == selected_id:
        st.warning(
            f"Delete '{selected_exam['name']}'? "
            f"All subjects and marks under it will be removed."
        )
        c1, c2 = st.columns([1, 1])
        with c1:
            if st.button("Yes, delete", type="primary", key="conf_del_yes"):
                delete_exam(selected_id)
                st.session_state.confirm_exam_delete = None
                st.success("Exam deleted.")
                st.rerun()
        with c2:
            if st.button("Cancel", key="conf_del_no"):
                st.session_state.confirm_exam_delete = None
                st.rerun()

    st.markdown("<div class='soft-divider'></div>", unsafe_allow_html=True)

    # ============================================================
    # SUBJECTS FOR THIS EXAM
    # ============================================================
    st.markdown(
        f"<div class='section-heading'>Subjects for {selected_exam['name']}</div>",
        unsafe_allow_html=True,
    )
    st.caption(
        "Add subjects per class. Each subject has a max mark (e.g. 100) "
        "and a pass mark (e.g. 40)."
    )

    existing_classes = get_classes()
    subjects_by_class = {}
    for s in get_subjects_for_exam(selected_id):
        subjects_by_class.setdefault(s["class_name"], []).append(s)

    # ---- Add a subject ----
    with st.form("add_subject_form", clear_on_submit=True):
        c1, c2, c3, c4 = st.columns([2, 2, 1, 1])
        with c1:
            new_class = st.selectbox(
                "Class",
                existing_classes or ["(no classes yet)"],
                key="subj_class",
            )
        with c2:
            new_subject = st.text_input(
                "Subject",
                placeholder="e.g. Mathematics",
            )
        with c3:
            new_max = st.number_input("Max", min_value=1, value=100, step=10)
        with c4:
            new_pass = st.number_input("Pass", min_value=0, value=40, step=5)

        add = st.form_submit_button("Add subject", use_container_width=True)

        if add:
            if new_class == "(no classes yet)":
                st.error("Add students first to create classes.")
            elif not new_subject.strip():
                st.error("Please enter a subject name.")
            elif new_pass > new_max:
                st.error("Pass marks cannot exceed max marks.")
            else:
                add_subject(selected_id, new_class, new_subject, int(new_max), int(new_pass))
                st.success(f"Added {new_subject} to {new_class}.")
                st.rerun()

    st.markdown("<div style='height: 8px;'></div>", unsafe_allow_html=True)

    # ---- List subjects grouped by class ----
    if not subjects_by_class:
        st.info("No subjects yet for this exam. Add one above.")
        return

    for cls in sorted(subjects_by_class.keys()):
        subs = subjects_by_class[cls]
        progress = {p["subject_id"]: p for p in get_subject_progress(selected_id, cls)}

        with st.container():
            st.markdown(
                f"<div style='font-weight:600; font-size:14px; color:#0f172a; "
                f"margin: 12px 0 6px 0;'>{cls}</div>",
                unsafe_allow_html=True,
            )

            for sub in subs:
                p = progress.get(sub["id"], {})
                entered = p.get("entered", 0)
                total = p.get("total", 0)
                pct = (entered / total * 100) if total else 0

                c1, c2, c3, c4 = st.columns([3, 1, 1, 1])
                with c1:
                    st.markdown(
                        f"<div style='padding-top:6px; font-size:14px; color:#0f172a;'>"
                        f"{sub['subject_name']}"
                        f" <span style='color:#94a3b8; font-size:12px;'>"
                        f"(max {sub['max_marks']}, pass {sub['pass_marks']})</span>"
                        f"</div>",
                        unsafe_allow_html=True,
                    )
                with c2:
                    st.markdown(
                        f"<div style='padding-top:6px; font-size:12px; color:#64748b;'>"
                        f"{entered}/{total} marked</div>",
                        unsafe_allow_html=True,
                    )
                with c3:
                    if pct == 100:
                        st.markdown(
                            "<div style='padding-top:6px; font-size:12px; "
                            "color:#059669; font-weight:600;'>Complete</div>",
                            unsafe_allow_html=True,
                        )
                    elif pct > 0:
                        st.markdown(
                            f"<div style='padding-top:6px; font-size:12px; "
                            f"color:#f59e0b; font-weight:600;'>{pct:.0f}%</div>",
                            unsafe_allow_html=True,
                        )
                    else:
                        st.markdown(
                            "<div style='padding-top:6px; font-size:12px; "
                            "color:#94a3b8;'>Not started</div>",
                            unsafe_allow_html=True,
                        )
                with c4:
                    if st.button("Delete", key=f"del_sub_{sub['id']}", use_container_width=True):
                        delete_subject(sub["id"])
                        st.rerun()