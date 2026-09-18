from datetime import date

import streamlit as st
import pandas as pd

from students import (
    get_all_students,
    add_student,
    update_student,
    soft_delete_student,
    count_students,
    get_classes,
    get_class_fee,
    set_class_fee,
    get_next_roll_number,
    STANDARD_CLASSES,
    STANDARD_SECTIONS,
)
from exports import students_to_excel
from ui import _html


def page_header(title, subtitle=""):
    sub = f'<div class="page-subtitle">{subtitle}</div>' if subtitle else ""
    st.markdown(_html(f"""
        <div class="page-header">
            <div class="page-title">{title}</div>
            {sub}
        </div>
    """), unsafe_allow_html=True)


def stat_card(label, value, accent="#4338ca"):
    st.markdown(_html(f"""
        <div class="kpi-card">
            <div class="kpi-label">{label}</div>
            <div class="kpi-value" style="color:{accent};">{value}</div>
        </div>
    """), unsafe_allow_html=True)


def students_list_view(students):
    df = pd.DataFrame(students)

    # ---- Build full class and section option lists ----
    base_classes = list(STANDARD_CLASSES)
    extra_classes = sorted([
        c for c in df["class_name"].dropna().unique().tolist()
        if c and c not in base_classes
    ])
    class_options = ["All classes"] + base_classes + extra_classes

    base_sections = list(STANDARD_SECTIONS)
    extra_sections = sorted([
        s for s in df["section"].dropna().unique().tolist()
        if s and s not in base_sections
    ])
    section_options = ["All sections"] + base_sections + extra_sections

    # ---- Filters ----
    fcol1, fcol2, fcol3 = st.columns([2, 1, 1])

    with fcol1:
        search = st.text_input(
            "Search",
            placeholder="Search by name, roll number, or parent...",
            label_visibility="collapsed",
            key="student_search",
        )

    with fcol2:
        class_filter = st.selectbox(
            "Class",
            class_options,
            label_visibility="collapsed",
            key="student_class_filter",
        )

    with fcol3:
        section_filter = st.selectbox(
            "Section",
            section_options,
            label_visibility="collapsed",
            key="student_section_filter",
        )

    # ---- Apply filters ----
    filtered = df.copy()

    if search:
        search_lower = search.lower()
        mask = (
            filtered["full_name"].str.lower().str.contains(search_lower, na=False)
            | filtered["roll_number"].astype(str).str.lower().str.contains(search_lower, na=False)
            | filtered["parent_name"].str.lower().str.contains(search_lower, na=False)
        )
        filtered = filtered[mask]

    if class_filter != "All classes":
        filtered = filtered[filtered["class_name"] == class_filter]

    if section_filter != "All sections":
        filtered = filtered[filtered["section"] == section_filter]

    # ---- Count ----
    st.markdown(
        f"<div style='color:#64748b; font-size:13px; margin: 8px 0 12px 0;'>"
        f"Showing <b>{len(filtered)}</b> of {len(df)} students</div>",
        unsafe_allow_html=True,
    )

    if filtered.empty:
        st.info("No students match your filters.")
        return

    display = filtered[[
        "id", "full_name", "roll_number", "class_name", "section",
        "parent_name", "parent_phone", "monthly_fee",
    ]].rename(columns={
        "id": "ID",
        "full_name": "Name",
        "roll_number": "Roll #",
        "class_name": "Class",
        "section": "Section",
        "parent_name": "Parent",
        "parent_phone": "Contact",
        "monthly_fee": "Monthly Fee (Rs)",
    })

    st.dataframe(
        display,
        use_container_width=True,
        hide_index=True,
        column_config={
            "Monthly Fee (Rs)": st.column_config.NumberColumn(format="%d"),
        },
    )

    st.markdown("<div style='height: 20px;'></div>", unsafe_allow_html=True)
    st.markdown("#### Manage a student")

    acol1, acol2, acol3 = st.columns([2, 1, 1])

    student_options = {
        f"{row['full_name']} — {row['class_name']} {row['section']} (ID {row['id']})": row["id"]
        for _, row in filtered.iterrows()
    }

    with acol1:
        selected_label = st.selectbox(
            "Pick a student",
            list(student_options.keys()),
            label_visibility="collapsed",
            key="manage_student_pick",
        )

    selected_id = student_options[selected_label]

    with acol2:
        if st.button("Edit", use_container_width=True, key="edit_btn"):
            st.session_state.edit_student_id = selected_id
            st.rerun()

    with acol3:
        if st.button("Delete", use_container_width=True, key="delete_btn"):
            st.session_state.confirm_delete_id = selected_id
            st.rerun()

    # ---- Confirm delete ----
    if st.session_state.get("confirm_delete_id"):
        st.warning(
            "Are you sure you want to delete this student? "
            "They will be marked inactive."
        )
        dcol1, dcol2 = st.columns([1, 1])
        with dcol1:
            if st.button("Yes, delete", type="primary", key="confirm_del_yes"):
                soft_delete_student(st.session_state.confirm_delete_id)
                st.session_state.confirm_delete_id = None
                st.success("Student removed.")
                st.rerun()
        with dcol2:
            if st.button("Cancel", key="confirm_del_no"):
                st.session_state.confirm_delete_id = None
                st.rerun()


def student_form(mode="add", student=None):
    is_edit = (mode == "edit" and student is not None)
    ks = f"_edit_{student['id']}" if is_edit else "_add"

    st.markdown(
        f"<div class='section-heading'>"
        f"{'Edit Student' if is_edit else 'Add New Student'}</div>",
        unsafe_allow_html=True,
    )

    # ---- Class options: Nursery → Class 10 ----
    class_options = list(STANDARD_CLASSES)

    # If editing a student whose class isn't in the standard list,
    # add it so the dropdown reflects reality
    if is_edit and student["class_name"] and student["class_name"] not in class_options:
        class_options = class_options + [student["class_name"]]

    if is_edit:
        default_idx = (
            class_options.index(student["class_name"])
            if student["class_name"] in class_options
            else 0
        )
        class_name = st.selectbox(
            "Class *",
            class_options,
            index=default_idx,
            key=f"class{ks}",
        )
    else:
        class_name = st.selectbox(
            "Class *",
            class_options,
            key=f"class{ks}",
        )

    # ---- Auto-compute fee and roll ----
    default_fee = 0.0
    default_roll = ""

    if class_name:
        if is_edit:
            default_fee = float(student["monthly_fee"] or 0)
            default_roll = student["roll_number"] or ""
        else:
            cf = get_class_fee(class_name)
            default_fee = float(cf) if cf is not None else 0.0
            default_roll = get_next_roll_number(class_name)

    if class_name and not is_edit:
        if get_class_fee(class_name) is not None:
            st.caption(
                f"Class fee for {class_name}: Rs {default_fee:,.0f}  ·  "
                f"Next roll number: {default_roll}"
            )
        else:
            st.caption(
                f"No default fee set for {class_name} yet — enter it below. "
                f"Next roll number: {default_roll}"
            )

    st.markdown("<div style='height: 6px;'></div>", unsafe_allow_html=True)

    c1, c2 = st.columns(2)
    with c1:
        full_name = st.text_input(
            "Full name *",
            value=student["full_name"] if is_edit else "",
            key=f"name{ks}",
            placeholder="e.g. Ahmed Khan",
        )
    with c2:
        roll_number = st.text_input(
            "Roll number",
            value=default_roll,
            key=f"roll_{class_name}{ks}",
            placeholder="auto-assigned",
        )

    c3, c4 = st.columns([1, 1])
    with c3:
        section_options = list(STANDARD_SECTIONS)
        if is_edit and student["section"] and student["section"] not in section_options:
            section_options = section_options + [student["section"]]

        if is_edit:
            sec_idx = (
                section_options.index(student["section"])
                if student["section"] in section_options
                else 0
            )
            section = st.selectbox(
                "Section",
                section_options,
                index=sec_idx,
                key=f"section{ks}",
            )
        else:
            section = st.selectbox(
                "Section",
                section_options,
                key=f"section{ks}",
            )
    with c4:
        monthly_fee = st.number_input(
            "Monthly fee (Rs) *",
            min_value=0.0,
            step=100.0,
            value=default_fee,
            key=f"fee_{class_name}{ks}",
            format="%.0f",
        )

    c5, c6 = st.columns(2)
    with c5:
        parent_name = st.text_input(
            "Parent / guardian name",
            value=student["parent_name"] if is_edit else "",
            key=f"parent{ks}",
        )
    with c6:
        parent_phone = st.text_input(
            "Parent contact",
            value=student["parent_phone"] if is_edit else "",
            key=f"phone{ks}",
            placeholder="e.g. 0300-1234567",
        )

    st.markdown("<div style='height: 6px;'></div>", unsafe_allow_html=True)

    col_submit, col_cancel = st.columns([1, 1])

    with col_submit:
        submit_label = "Save changes" if is_edit else "Add student"
        if st.button(submit_label, use_container_width=True, key=f"submit{ks}"):
            if not full_name.strip() or not class_name.strip():
                st.error("Please fill in at least the student name and class.")
            else:
                if is_edit:
                    update_student(
                        student["id"], full_name, roll_number, class_name,
                        section, parent_name, parent_phone, monthly_fee,
                    )
                    st.success(f"Updated {full_name}.")
                    st.session_state.edit_student_id = None
                    st.rerun()
                else:
                    add_student(
                        full_name, roll_number, class_name, section,
                        parent_name, parent_phone, monthly_fee,
                    )
                    # If this class had no default fee yet, save the one typed
                    if get_class_fee(class_name) is None and monthly_fee > 0:
                        set_class_fee(class_name, monthly_fee)
                    st.success(f"Added {full_name} to {class_name}.")
                    st.rerun()

    if is_edit:
        with col_cancel:
            if st.button("Cancel", use_container_width=True, key=f"cancel{ks}"):
                st.session_state.edit_student_id = None
                st.rerun()


def render():
    students = get_all_students()

    page_header("Students", "Manage your school's student records.")

    total = count_students()
    classes = get_classes()
    total_fee = sum(s["monthly_fee"] or 0 for s in students)

    s1, s2, s3 = st.columns(3)
    with s1:
        stat_card("Total Students", f"{total:,}", "#4338ca")
    with s2:
        stat_card("Classes", f"{len(classes)}", "#f59e0b")
    with s3:
        stat_card("Monthly Fee Roll", f"Rs {total_fee:,.0f}", "#059669")

    st.markdown("<div style='height: 24px;'></div>", unsafe_allow_html=True)

    tab_list, tab_add = st.tabs(["All Students", "Add Student"])

    with tab_list:
        exp_l, exp_r = st.columns([4, 1])
        with exp_r:
            xlsx = students_to_excel()
            st.download_button(
                "Export to Excel",
                data=xlsx,
                file_name=f"students_{date.today().isoformat()}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True,
                key="export_students_btn",
            )

        if st.session_state.get("edit_student_id"):
            student = next(
                (s for s in students if s["id"] == st.session_state.edit_student_id),
                None,
            )
            if student:
                student_form(mode="edit", student=student)
                st.markdown('<div class="soft-divider"></div>', unsafe_allow_html=True)

        students_list_view(students)

    with tab_add:
        student_form(mode="add")