import streamlit as st
import pandas as pd

from import_students import (
    read_file,
    auto_detect_mapping,
    build_preview,
    import_students,
    REQUIRED_FIELDS,
    OPTIONAL_FIELDS,
    ALL_FIELDS,
    FIELD_LABELS,
)


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


def _reset_import_state():
    for k in ["_import_df", "_import_filename", "_import_mapping",
              "_import_preview", "_import_errors", "_import_done"]:
        st.session_state.pop(k, None)


def render():
    page_header(
        "Import Students",
        "Upload your existing Excel or CSV file and add all students at once.",
    )

    # ---- Step indicator ----
    step = st.session_state.get("_import_step", 1)

    col1, col2, col3 = st.columns(3)
    with col1:
        _step_badge("1. Upload file", step >= 1, step == 1)
    with col2:
        _step_badge("2. Map columns", step >= 2, step == 2)
    with col3:
        _step_badge("3. Confirm import", step >= 3, step == 3)

    st.markdown("<div style='height: 16px;'></div>", unsafe_allow_html=True)

    # =====================================================
    # STEP 1 — UPLOAD
    # =====================================================
    if step == 1:
        st.markdown("<div class='section-heading'>Upload your file</div>",
                    unsafe_allow_html=True)
        st.caption(
            "Accepted formats: **.xlsx**, **.xls**, **.csv**. "
            "The first row should contain column headers."
        )

        # Sample template download
        sample = pd.DataFrame([
            {
                "Student Name": "Ahmed Khan",
                "Class": "Class 5",
                "Roll No": "101",
                "Section": "A",
                "Father Name": "Muhammad Khan",
                "Contact": "0300-1111111",
                "Monthly Fee": 2500,
            },
            {
                "Student Name": "Fatima Ali",
                "Class": "Class 5",
                "Roll No": "102",
                "Section": "A",
                "Father Name": "Ali Akbar",
                "Contact": "0300-2222222",
                "Monthly Fee": 2500,
            },
        ])
        csv_bytes = sample.to_csv(index=False).encode("utf-8")

        st.download_button(
            "Download sample template (CSV)",
            data=csv_bytes,
            file_name="student_import_template.csv",
            mime="text/csv",
        )

        st.markdown("<div style='height: 8px;'></div>", unsafe_allow_html=True)

        uploaded = st.file_uploader(
            "Choose file",
            type=["csv", "xlsx", "xls"],
            key="_import_file",
        )

        if uploaded is not None:
            with st.spinner("Reading file..."):
                df, err = read_file(uploaded)

            if err:
                st.error(err)
            else:
                st.session_state["_import_df"] = df
                st.session_state["_import_filename"] = uploaded.name
                st.session_state["_import_step"] = 2
                st.rerun()

    # =====================================================
    # STEP 2 — MAP COLUMNS
    # =====================================================
    elif step == 2:
        df = st.session_state.get("_import_df")
        filename = st.session_state.get("_import_filename", "file")

        if df is None:
            _reset_import_state()
            st.rerun()

        st.markdown(
            f"<div class='section-heading'>File loaded: {filename}</div>",
            unsafe_allow_html=True,
        )
        st.caption(
            f"{len(df):,} rows · {len(df.columns)} columns detected. "
            f"Now match your columns to the fields we need."
        )

        with st.expander("Preview first 5 rows of your file", expanded=True):
            st.dataframe(df.head(5), use_container_width=True, hide_index=True)

        st.markdown("<div style='height: 8px;'></div>", unsafe_allow_html=True)

        # Auto-detect
        auto_map = auto_detect_mapping(df.columns.tolist())

        st.markdown(
            "<div class='section-heading'>Match columns</div>",
            unsafe_allow_html=True,
        )
        st.caption(
            "Required fields are marked with *. Column names were pre-filled "
            "where we could auto-detect them."
        )

        columns_options = ["(skip)"] + df.columns.tolist()
        new_mapping = {}

        for field in ALL_FIELDS:
            is_required = field in REQUIRED_FIELDS
            label = FIELD_LABELS[field] + (" *" if is_required else "")

            default = auto_map.get(field, "(skip)")
            idx = columns_options.index(default) if default in columns_options else 0

            picked = st.selectbox(
                label,
                columns_options,
                index=idx,
                key=f"_map_{field}",
            )
            if picked != "(skip)":
                new_mapping[field] = picked

        # Check that required fields are mapped
        missing_required = [
            f for f in REQUIRED_FIELDS if f not in new_mapping
        ]

        if missing_required:
            st.warning(
                f"Please map these required fields: "
                f"{', '.join(FIELD_LABELS[f] for f in missing_required)}"
            )

        st.markdown("<div style='height: 8px;'></div>", unsafe_allow_html=True)

        c1, c2 = st.columns([1, 1])
        with c1:
            if st.button("Back", key="_import_back_2", use_container_width=True):
                _reset_import_state()
                st.rerun()

        with c2:
            if st.button(
                "Preview import",
                key="_import_preview_btn",
                use_container_width=True,
                disabled=bool(missing_required),
            ):
                st.session_state["_import_mapping"] = new_mapping
                st.session_state["_import_step"] = 3
                st.rerun()

    # =====================================================
    # STEP 3 — CONFIRM IMPORT
    # =====================================================
    elif step == 3:
        df = st.session_state.get("_import_df")
        mapping = st.session_state.get("_import_mapping")

        if df is None or not mapping:
            _reset_import_state()
            st.rerun()

        # Build preview
        if "_import_preview" not in st.session_state:
            with st.spinner("Validating..."):
                preview, errors = build_preview(df, mapping)
                st.session_state["_import_preview"] = preview
                st.session_state["_import_errors"] = errors

        preview = st.session_state["_import_preview"]
        errors = st.session_state["_import_errors"]

        # ---- Summary ----
        col1, col2, col3 = st.columns(3)
        with col1:
            stat_card("Ready to import", f"{len(preview)}", "#059669")
        with col2:
            stat_card("Skipped (errors)", f"{len(errors)}",
                      "#dc2626" if errors else "#475569")
        with col3:
            classes = preview["class_name"].nunique() if not preview.empty else 0
            stat_card("Classes", f"{classes}", "#4338ca")

        st.markdown("<div style='height: 12px;'></div>", unsafe_allow_html=True)

        # ---- Errors ----
        if errors:
            with st.expander(f"⚠️ {len(errors)} rows will be skipped",
                             expanded=True):
                err_df = pd.DataFrame(errors, columns=["Excel row", "Reason"])
                st.dataframe(err_df, use_container_width=True, hide_index=True)

        # ---- Preview ----
        if not preview.empty:
            st.markdown("<div class='section-heading'>Preview</div>",
                        unsafe_allow_html=True)
            st.caption(
                f"Showing first 10 of {len(preview)} students that will be added."
            )

            display = preview.head(10)[[
                "full_name", "class_name", "section",
                "roll_number", "parent_name", "parent_phone", "monthly_fee",
            ]].rename(columns={
                "full_name": "Name",
                "class_name": "Class",
                "section": "Section",
                "roll_number": "Roll #",
                "parent_name": "Parent",
                "parent_phone": "Contact",
                "monthly_fee": "Fee (Rs)",
            })

            st.dataframe(
                display,
                use_container_width=True,
                hide_index=True,
                column_config={"Fee (Rs)": st.column_config.NumberColumn(format="%d")},
            )

            # ---- Classes summary ----
            class_counts = preview.groupby("class_name").size().reset_index(name="count")
            st.markdown("<div class='section-heading'>Classes in this import</div>",
                        unsafe_allow_html=True)
            class_counts.columns = ["Class", "Students"]
            st.dataframe(class_counts, use_container_width=True, hide_index=True)

        st.markdown("<div style='height: 12px;'></div>", unsafe_allow_html=True)

        # ---- Actions ----
        c1, c2 = st.columns([1, 1])
        with c1:
            if st.button("Back to mapping", key="_import_back_3",
                         use_container_width=True):
                st.session_state["_import_step"] = 2
                st.session_state.pop("_import_preview", None)
                st.session_state.pop("_import_errors", None)
                st.rerun()

        with c2:
            if st.button(
                f"Import {len(preview)} students",
                key="_import_do_btn",
                use_container_width=True,
                disabled=preview.empty,
            ):
                records = preview.to_dict("records")
                with st.spinner(f"Importing {len(records)} students..."):
                    inserted, skipped, defaults_set = import_students(records)

                st.session_state["_import_result"] = {
                    "inserted": inserted,
                    "skipped": skipped,
                    "defaults_set": defaults_set,
                }
                st.session_state["_import_done"] = True
                st.rerun()

    # =====================================================
    # RESULT
    # =====================================================
    if st.session_state.get("_import_done"):
        result = st.session_state.get("_import_result", {})
        st.markdown("<div class='soft-divider'></div>", unsafe_allow_html=True)
        st.success(
            f"✅ Imported **{result.get('inserted', 0)}** students. "
            f"Skipped **{result.get('skipped', 0)}** existing or duplicate rows."
        )

        defaults = result.get("defaults_set", [])
        if defaults:
            lines = ", ".join([f"{c} (Rs {f:,.0f})" for c, f in defaults])
            st.info(f"Default class fees set: {lines}")

        c1, c2 = st.columns([1, 1])
        with c1:
            if st.button("Import another file", key="_import_again",
                         use_container_width=True):
                _reset_import_state()
                st.rerun()
        with c2:
            if st.button("View students", key="_import_view",
                         use_container_width=True):
                _reset_import_state()
                # Set both page AND the widget key so the menu reflects it
                st.session_state.page = "Students"
                st.session_state["schoolpulse_nav_menu"] = "Students"
                st.rerun()


def _step_badge(label, active, current):
    """Render one step indicator."""
    if current:
        bg = "#4338ca"
        color = "#ffffff"
        border = "#4338ca"
    elif active:
        bg = "#eef2ff"
        color = "#4338ca"
        border = "#c7d2fe"
    else:
        bg = "#f8fafc"
        color = "#94a3b8"
        border = "#e2e8f0"

    st.markdown(
        f"""
        <div style="
            background:{bg};
            color:{color};
            border:1px solid {border};
            border-radius:8px;
            padding:10px 14px;
            font-weight:600;
            font-size:13px;
            text-align:center;
        ">{label}</div>
        """,
        unsafe_allow_html=True,
    )