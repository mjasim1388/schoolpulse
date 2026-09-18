import base64
from io import BytesIO

import streamlit as st
from PIL import Image

from settings import (
    get_school_profile,
    update_school_profile,
    change_user_password,
    get_all_class_fees,
    update_class_fee,
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


def _image_to_base64(uploaded_file, max_size=(400, 400)):
    """Convert an uploaded image to a base64 string, resizing if needed."""
    img = Image.open(uploaded_file).convert("RGBA")

    # Paste on white background in case of transparency
    bg = Image.new("RGB", img.size, (255, 255, 255))
    bg.paste(img, mask=img.split()[3] if img.mode == "RGBA" else None)
    img = bg

    img.thumbnail(max_size, Image.LANCZOS)

    buf = BytesIO()
    img.save(buf, format="PNG", optimize=True)
    return base64.b64encode(buf.getvalue()).decode("utf-8")


def _base64_to_image(b64):
    """Convert base64 string back to PIL Image."""
    if not b64:
        return None
    try:
        return Image.open(BytesIO(base64.b64decode(b64)))
    except Exception:
        return None


def render():
    page_header("Settings", "School profile, class fees, and your account.")

    tab_profile, tab_fees, tab_account = st.tabs(
        ["School Profile", "Class Fees", "Change Password"]
    )

    # =====================================================
    # TAB 1 — SCHOOL PROFILE
    # =====================================================
    with tab_profile:
        profile = get_school_profile()

        st.markdown(
            "<div class='section-heading'>Basic information</div>",
            unsafe_allow_html=True,
        )

        # ---- Logo section ----
        left, right = st.columns([1, 3], gap="large")

        with left:
            st.markdown(
                "<div style='font-size:13px; color:#475569; margin-bottom:8px;'>"
                "School logo</div>",
                unsafe_allow_html=True,
            )
            existing_logo = _base64_to_image(profile.get("logo_base64"))
            if existing_logo:
                st.image(existing_logo, use_container_width=True)
            else:
                st.markdown(
                    """
                    <div style="
                        background:#f1f5f9;
                        border:1px dashed #cbd5e1;
                        border-radius:8px;
                        padding:32px 12px;
                        text-align:center;
                        color:#64748b;
                        font-size:13px;
                    ">No logo uploaded</div>
                    """,
                    unsafe_allow_html=True,
                )

        with right:
            with st.form("school_profile_form", clear_on_submit=False):
                school_name = st.text_input(
                    "School name *",
                    value=profile.get("school_name", ""),
                    placeholder="e.g. Rashid's Academy",
                )

                address = st.text_input(
                    "Address",
                    value=profile.get("address", ""),
                    placeholder="e.g. Block C, North Nazimabad, Karachi",
                )

                c1, c2 = st.columns(2)
                with c1:
                    phone = st.text_input(
                        "Phone",
                        value=profile.get("phone", ""),
                        placeholder="e.g. 021-1234567",
                    )
                with c2:
                    email = st.text_input(
                        "Email",
                        value=profile.get("email", ""),
                        placeholder="e.g. info@school.com",
                    )

                principal_name = st.text_input(
                    "Principal name",
                    value=profile.get("principal_name", ""),
                    placeholder="e.g. Mr. Rashid Ahmed",
                )

                logo_file = st.file_uploader(
                    "Upload new logo (PNG or JPG, max 400×400)",
                    type=["png", "jpg", "jpeg"],
                )

                remove_logo = st.checkbox("Remove existing logo")

                st.markdown("<div style='height: 4px;'></div>", unsafe_allow_html=True)

                saved = st.form_submit_button(
                    "Save profile", use_container_width=True
                )

            if saved:
                new_logo_b64 = profile.get("logo_base64")
                keep = True

                if remove_logo:
                    new_logo_b64 = None
                    keep = False
                elif logo_file is not None:
                    new_logo_b64 = _image_to_base64(logo_file)
                    keep = False

                update_school_profile(
                    school_name=school_name,
                    address=address,
                    phone=phone,
                    email=email,
                    principal_name=principal_name,
                    logo_base64=new_logo_b64,
                    keep_logo=keep,
                )
                st.success("Profile saved.")
                st.rerun()

    # =====================================================
    # TAB 2 — CLASS FEES
    # =====================================================
    with tab_fees:
        st.markdown(
            "<div class='section-heading'>Classes & default fees</div>",
            unsafe_allow_html=True,
        )
        st.caption(
            "Classes are created here. New students pick from this list — "
            "they cannot type a class name, so duplicates like "
            "'Class 5' and 'class5' can't happen."
        )

        class_fees = get_all_class_fees()

        if not class_fees:
            st.info(
                "No classes yet. Add your first class below — "
                "for example, **Class 5** with a fee of **Rs 2500**."
            )
        else:
            # ---- Existing classes ----
            st.markdown(
                "<div class='section-heading' style='margin-top:12px;'>"
                "Existing classes</div>",
                unsafe_allow_html=True,
            )

            for cf in class_fees:
                col_name, col_fee, col_btn = st.columns([2, 1, 1])

                with col_name:
                    st.markdown(
                        f"<div style='padding-top:10px; font-weight:500; color:#0f172a;'>"
                        f"{cf['class_name']}</div>",
                        unsafe_allow_html=True,
                    )

                with col_fee:
                    new_fee = st.number_input(
                        "Fee",
                        min_value=0.0,
                        step=100.0,
                        value=float(cf["monthly_fee"]),
                        format="%.0f",
                        key=f"cf_{cf['class_name']}",
                        label_visibility="collapsed",
                    )

                with col_btn:
                    if st.button(
                        "Save",
                        key=f"save_{cf['class_name']}",
                        use_container_width=True,
                    ):
                        update_class_fee(cf["class_name"], new_fee)
                        st.success(f"Updated {cf['class_name']}.")
                        st.rerun()

        st.markdown("<div style='height: 20px;'></div>", unsafe_allow_html=True)

        # ---- Add a new class ----
        st.markdown(
            "<div class='section-heading'>Add a new class</div>",
            unsafe_allow_html=True,
        )
        st.caption(
            "Write the class name **exactly** as you want it to appear "
            "everywhere (e.g. `Class 5`, `Class 6-A`, `Nursery`). "
            "This name is used in students, fees, and reports."
        )

        with st.form("add_class_fee_form", clear_on_submit=True):
            c1, c2, c3 = st.columns([2, 1, 1])
            with c1:
                new_class_name = st.text_input(
                    "Class name",
                    placeholder="e.g. Class 7",
                )
            with c2:
                new_class_fee = st.number_input(
                    "Monthly fee (Rs)",
                    min_value=0.0,
                    step=100.0,
                    value=0.0,
                    format="%.0f",
                )
            with c3:
                st.markdown(
                    "<div style='height: 28px;'></div>",
                    unsafe_allow_html=True,
                )
                add = st.form_submit_button(
                    "Add class", use_container_width=True
                )

            if add:
                name = new_class_name.strip()

                if not name:
                    st.error("Please enter a class name.")
                elif name in [cf["class_name"] for cf in class_fees]:
                    st.error(f"Class '{name}' already exists.")
                elif name.lower() in [cf["class_name"].lower() for cf in class_fees]:
                    existing = next(
                        cf["class_name"] for cf in class_fees
                        if cf["class_name"].lower() == name.lower()
                    )
                    st.error(
                        f"Class '{name}' already exists as '{existing}'. "
                        f"Class names are case-insensitive."
                    )
                else:
                    update_class_fee(name, new_class_fee)
                    st.success(f"Created class: {name}")
                    st.rerun()

    # =====================================================
    # TAB 3 — CHANGE PASSWORD
    # =====================================================
    with tab_account:
        user = st.session_state.user

        st.markdown(
            f"""
            <div class="user-card" style="max-width: 380px;">
                <div class="user-avatar">{"".join([p[0] for p in user['full_name'].split()[:2]]).upper()}</div>
                <div class="user-info">
                    <div class="user-name">{user['full_name']}</div>
                    <div class="user-role">{user['email']}</div>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        st.markdown(
            "<div class='section-heading'>Change your password</div>",
            unsafe_allow_html=True,
        )

        with st.form("change_password_form", clear_on_submit=True):
            current = st.text_input("Current password", type="password")
            new1 = st.text_input("New password", type="password")
            new2 = st.text_input("Confirm new password", type="password")

            submit = st.form_submit_button("Update password", use_container_width=True)

            if submit:
                if new1 != new2:
                    st.error("New passwords don't match.")
                elif len(new1) < 6:
                    st.error("Password must be at least 6 characters.")
                else:
                    ok, msg = change_user_password(user["id"], current, new1)
                    if ok:
                        st.success(msg)
                    else:
                        st.error(msg)