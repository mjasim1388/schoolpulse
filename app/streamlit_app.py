import sys
import textwrap
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

import streamlit as st
from streamlit_option_menu import option_menu

from auth import authenticate
from ui import _html, make_selectboxes_readonly


# ============================================================
# PAGE CONFIG
# ============================================================
st.set_page_config(
    page_title="SchoolPulse — School Management",
    page_icon="🎓",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ============================================================
# LOAD DESIGN SYSTEM CSS
# ============================================================
@st.cache_data(show_spinner=False)
def _read_css():
    css_path = ROOT / ".streamlit" / "style.css"
    if css_path.exists():
        return css_path.read_text(encoding="utf-8")
    return ""


st.markdown(f"<style>{_read_css()}</style>", unsafe_allow_html=True)
make_selectboxes_readonly()


# ============================================================
# SESSION PERSISTENCE VIA QUERY PARAMS
# ============================================================
def _save_session():
    """Store user in the URL so it survives page refreshes."""
    user = st.session_state.get("user")
    if user:
        st.query_params["uid"] = str(user["id"])
        st.query_params["email"] = user["email"]
        st.query_params["name"] = user["full_name"]
        st.query_params["role"] = user["role"]
    else:
        for k in ["uid", "email", "name", "role"]:
            if k in st.query_params:
                del st.query_params[k]


def _restore_session():
    """Restore user from URL if present."""
    if st.session_state.get("user"):
        return
    if "uid" in st.query_params:
        try:
            st.session_state.user = {
                "id": int(st.query_params["uid"]),
                "email": st.query_params.get("email", ""),
                "full_name": st.query_params.get("name", ""),
                "role": st.query_params.get("role", "admin"),
            }
        except Exception:
            st.session_state.user = None


# ============================================================
# SESSION STATE
# ============================================================
if "user" not in st.session_state:
    st.session_state.user = None
if "page" not in st.session_state:
    st.session_state.page = "Dashboard"

_restore_session()


# ============================================================
# SIDEBAR
# ============================================================
def render_sidebar():
    with st.sidebar:
        # ---- School identity in sidebar ----
        try:
            from settings import get_school_profile
            profile = get_school_profile()
            school_name = profile.get("school_name") or "My School"
            logo_b64 = profile.get("logo_base64")
        except Exception:
            school_name = "My School"
            logo_b64 = None

        if logo_b64:
            logo_html = (
                f'<img src="data:image/png;base64,{logo_b64}" '
                f'style="width:38px;height:38px;object-fit:contain;'
                f'border-radius:8px;background:#fff;border:1px solid #e2e8f0;padding:2px;" />'
            )
        else:
            logo_html = (
                '<div class="auth-brand-icon" '
                'style="width:38px;height:38px;font-size:20px;">🎓</div>'
            )

        sidebar_html = _html(f"""
            <div style="padding: 4px 4px 12px 4px;">
                <div class="auth-brand" style="margin-bottom:0; gap:10px;">
                    {logo_html}
                    <div style="font-weight:600; font-size:15px; color:#0f172a;
                                line-height:1.25; overflow:hidden; text-overflow:ellipsis;
                                white-space:nowrap; max-width:150px;">
                        {school_name}
                    </div>
                </div>
                <div style="padding-left:48px; font-size:11px; color:#94a3b8; margin-top:2px;">
                    Powered by SchoolPulse
                </div>
            </div>
        """)
        st.markdown(sidebar_html, unsafe_allow_html=True)

        options = ["Dashboard", "Students", "Import", "Fees",
                   "Exams", "Marks", "Reports", "Settings"]
        icons = ["speedometer2", "people-fill", "upload",
                 "cash-coin", "journal-check", "pencil-square",
                 "file-earmark-bar-graph", "gear"]

        default_idx = 0
        if st.session_state.page in options:
            default_idx = options.index(st.session_state.page)

        selected = option_menu(
            menu_title=None,
            options=options,
            icons=icons,
            default_index=default_idx,
            key="schoolpulse_nav_menu",
            styles={
                "container": {"padding": "0", "background-color": "transparent"},
                "icon": {"color": "#6366f1", "font-size": "15px"},
                "nav-link": {
                    "font-family": "Inter, sans-serif",
                    "font-size": "14px",
                    "font-weight": "500",
                    "color": "#334155",
                    "padding": "10px 14px",
                    "border-radius": "8px",
                    "margin": "2px 0",
                    "--hover-color": "rgba(99,102,241,0.08)",
                },
                "nav-link-selected": {
                    "background": "#4338ca",
                    "color": "#ffffff",
                    "font-weight": "600",
                },
            },
        )
        st.session_state.page = selected

        st.markdown("<div style='height: 20px;'></div>", unsafe_allow_html=True)

        user = st.session_state.user
        initials = "".join([p[0] for p in user["full_name"].split()[:2]]).upper()

        st.markdown(_html(f"""
            <div class="user-card">
                <div class="user-avatar">{initials}</div>
                <div class="user-info">
                    <div class="user-name">{user['full_name']}</div>
                    <div class="user-role">{user['role']}</div>
                </div>
            </div>
        """), unsafe_allow_html=True)

        if st.button("Sign out", key="signout_btn", use_container_width=True):
            st.session_state.user = None
            st.session_state.page = "Dashboard"
            st.session_state.pop("_warmed_up", None)
            _save_session()
            st.rerun()


# ============================================================
# PAGE HEADER HELPER
# ============================================================
def page_header(title, subtitle=""):
    sub = f'<div class="page-subtitle">{subtitle}</div>' if subtitle else ""
    st.markdown(_html(f"""
        <div class="page-header">
            <div class="page-title">{title}</div>
            {sub}
        </div>
    """), unsafe_allow_html=True)


# ============================================================
# PAGES
# ============================================================
def page_dashboard():
    from views.dashboard_page import render as render_dashboard
    render_dashboard()


def page_students():
    from views.students_page import render as render_students
    render_students()


def page_fees():
    from views.fees_page import render as render_fees
    render_fees()


def page_reports():
    from views.reports_page import render as render_reports
    render_reports()


def page_settings():
    from views.settings_page import render as render_settings
    render_settings()


def page_marks():
    from views.marks_page import render as render_marks
    render_marks()


def page_import():
    from views.import_page import render as render_import
    render_import()


PAGES = {
    "Dashboard": page_dashboard,
    "Students": page_students,
    "Import": page_import,
    "Fees": page_fees,
    "Exams": page_reports,
    "Marks": page_marks,
    "Reports": page_reports,
    "Settings": page_settings,
}


def render_app():
    render_sidebar()
    PAGES[st.session_state.page]()


# ============================================================
# LOGIN SCREEN
# ============================================================
def render_login():
    st.markdown("<div style='height: 3vh;'></div>", unsafe_allow_html=True)

    col_left, col_mid, col_right = st.columns([1, 5, 1])

    with col_mid:
        hero_col, form_col = st.columns([1.1, 1], gap="small")

        # ============ LEFT — School hero ============
        with hero_col:
            st.markdown(_html("""
                <div class="login-left">
                    <div>
                        <div class="login-brand">
                            <div class="login-brand-icon">🎓</div>
                            <div class="login-brand-name">School<span>Pulse</span></div>
                        </div>
                        <div class="login-hero-title">
                            Every school deserves <span>better tools</span>.
                        </div>
                        <div class="login-hero-sub">
                            Manage students, collect fees, track exams, and generate report cards — all in one place.
                        </div>
                        <ul class="login-features">
                            <li>Student records with complete parent details</li>
                            <li>Fee collection with automatic defaulter tracking</li>
                            <li>Exam marks and report cards in seconds</li>
                            <li>Monthly collection and class-wise insights</li>
                        </ul>
                    </div>
                    <div class="login-footer">
                        Trusted by schools across Pakistan · © 2026 SchoolPulse
                    </div>
                </div>
            """), unsafe_allow_html=True)

        # ============ RIGHT — Login form ============
        with form_col:
            with st.form("login_form", clear_on_submit=False):
                # Heading inside the form so it sits in the same panel
                st.markdown(_html("""
                    <div class="login-form-title">Welcome back</div>
                    <div class="login-form-sub">Sign in to continue to your dashboard</div>
                """), unsafe_allow_html=True)

                st.markdown(
                    '<label class="login-form-label">Email address</label>',
                    unsafe_allow_html=True,
                )
                email = st.text_input(
                    "Email address",
                    placeholder="you@school.com",
                    key="login_email",
                    label_visibility="collapsed",
                )

                st.markdown(
                    '<label class="login-form-label">Password</label>',
                    unsafe_allow_html=True,
                )
                password = st.text_input(
                    "Password",
                    placeholder="Enter your password",
                    type="password",
                    key="login_password",
                    label_visibility="collapsed",
                )

                st.markdown("<div style='height: 6px;'></div>", unsafe_allow_html=True)

                submitted = st.form_submit_button("Sign in", use_container_width=True)

            st.markdown(_html("""
                <div class="login-help">
                    Having trouble signing in? Contact your school administrator.
                </div>
            """), unsafe_allow_html=True)

            # Suppress browser password manager popups
            st.markdown(_html("""
                <script>
                (function() {
                    function fix() {
                        try {
                            const doc = window.parent.document;
                            doc.querySelectorAll('input').forEach(function(inp) {
                                inp.setAttribute('autocomplete', 'off');
                                inp.setAttribute('autocorrect', 'off');
                                inp.setAttribute('autocapitalize', 'off');
                                inp.setAttribute('spellcheck', 'false');
                                if (inp.type === 'password') {
                                    inp.setAttribute('autocomplete', 'new-password');
                                }
                            });
                        } catch (e) {}
                    }
                    fix();
                    setInterval(fix, 400);
                })();
                </script>
            """), unsafe_allow_html=True)

            if submitted:
                if not email or not password:
                    st.warning("Please enter both email and password.")
                else:
                    user = authenticate(email, password)
                    if user:
                        st.session_state.user = user
                        _save_session()
                        st.rerun()
                    else:
                        st.error("Invalid email or password.")


# ============================================================
# MAIN
# ============================================================
if st.session_state.user is None:
    render_login()
else:
    render_app()