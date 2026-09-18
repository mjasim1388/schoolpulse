import streamlit as st
import pandas as pd
import plotly.express as px

from fees import current_month_str
from dashboard import (
    get_dashboard_snapshot,
    get_6month_trend,
    get_students_per_class,
    get_top_defaulters,
    get_recent_payments,
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


def stat_card(label, value, accent="#4338ca", hint=""):
    hint_html = (
        f'<div style="color:#94a3b8; font-size:12px; margin-top:4px;">{hint}</div>'
        if hint else ""
    )
    st.markdown(
        f"""
        <div class="kpi-card">
            <div class="kpi-label">{label}</div>
            <div class="kpi-value" style="color:{accent};">{value}</div>
            {hint_html}
        </div>
        """,
        unsafe_allow_html=True,
    )


def format_month_label(m):
    names = ["January", "February", "March", "April", "May", "June",
             "July", "August", "September", "October", "November", "December"]
    y, mo = m.split("-")
    return f"{names[int(mo)-1]} {y}"


def render():
    user = st.session_state.user
    first_name = user["full_name"].split()[0] if user.get("full_name") else "there"

    # Try to get school name for the greeting
    try:
        from settings import get_school_profile
        school_name = get_school_profile().get("school_name") or ""
    except Exception:
        school_name = ""

    subtitle = (
        f"Here's how {school_name} is doing today."
        if school_name and school_name != "My School"
        else "Here's how your school is doing today."
    )

    page_header(f"Welcome back, {first_name}", subtitle)

    # ============================================================
    # TOP KPI ROW — one DB round-trip
    # ============================================================
    month = current_month_str()
    month_label = format_month_label(month)
    snap = get_dashboard_snapshot(month)

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        stat_card(
            "Total Students",
            f"{snap['total_students']:,}",
            "#4338ca",
            f"across {snap['total_classes']} classes",
        )
    with c2:
        stat_card(
            "Collected this month",
            f"Rs {snap['collected']:,.0f}",
            "#059669",
            month_label,
        )
    with c3:
        stat_card(
            "Pending",
            f"Rs {snap['pending']:,.0f}",
            "#dc2626" if snap["pending"] > 0 else "#059669",
            f"{snap['unpaid_count']} students unpaid",
        )
    with c4:
        stat_card(
            "Monthly Fee Roll",
            f"Rs {snap['monthly_fee_roll']:,.0f}",
            "#475569",
            "if everyone paid",
        )

    st.markdown("<div style='height: 24px;'></div>", unsafe_allow_html=True)

    # ============================================================
    # ROW 2 — CHART + CLASS BREAKDOWN
    # ============================================================
    left, right = st.columns([2, 1], gap="large")

    with left:
        st.markdown("<div class='section-heading'>Fee collection — last 6 months</div>",
                    unsafe_allow_html=True)
        trend = get_6month_trend()

        if all(t["collected"] == 0 for t in trend):
            st.info("No payments recorded in the last 6 months yet.")
        else:
            df = pd.DataFrame(trend)
            fig = px.bar(
                df,
                x="label",
                y="collected",
                labels={"label": "", "collected": "Collected (Rs)"},
                color_discrete_sequence=["#4338ca"],
            )
            fig.update_layout(
                plot_bgcolor="white",
                paper_bgcolor="white",
                margin=dict(l=10, r=10, t=10, b=10),
                height=300,
                showlegend=False,
                xaxis=dict(showgrid=False),
                yaxis=dict(gridcolor="#f1f5f9"),
            )
            st.plotly_chart(fig, use_container_width=True)

    with right:
        st.markdown("<div class='section-heading'>Students per class</div>",
                    unsafe_allow_html=True)
        class_data = get_students_per_class()

        if not class_data:
            st.info("No students yet.")
        else:
            df_cls = pd.DataFrame(class_data)
            df_cls = df_cls.sort_values("count", ascending=True)

            fig2 = px.bar(
                df_cls,
                x="count",
                y="class_name",
                orientation="h",
                labels={"count": "Students", "class_name": ""},
                color_discrete_sequence=["#6366f1"],
            )
            fig2.update_layout(
                plot_bgcolor="white",
                paper_bgcolor="white",
                margin=dict(l=10, r=10, t=10, b=10),
                height=300,
                showlegend=False,
                xaxis=dict(gridcolor="#f1f5f9"),
                yaxis=dict(showgrid=False),
            )
            st.plotly_chart(fig2, use_container_width=True)

    st.markdown("<div style='height: 8px;'></div>", unsafe_allow_html=True)

    # ============================================================
    # ROW 3 — DEFAULTERS + RECENT PAYMENTS
    # ============================================================
    left2, right2 = st.columns([1, 1], gap="large")

    with left2:
        st.markdown(
            f"<div class='section-heading'>Top defaulters — {month_label}</div>",
            unsafe_allow_html=True,
        )
        defaulters = get_top_defaulters(month, limit=5)

        if not defaulters:
            st.success(f"Every student has paid for {month_label}.")
        else:
            df_d = pd.DataFrame(defaulters)
            df_d = df_d.rename(columns={
                "full_name": "Name",
                "class_name": "Class",
                "section": "Section",
                "parent_phone": "Contact",
                "monthly_fee": "Fee (Rs)",
            })
            st.dataframe(
                df_d,
                use_container_width=True,
                hide_index=True,
                column_config={"Fee (Rs)": st.column_config.NumberColumn(format="%d")},
            )

    with right2:
        st.markdown("<div class='section-heading'>Recent payments</div>",
                    unsafe_allow_html=True)
        recent = get_recent_payments(limit=8)

        if not recent:
            st.info("No payments recorded yet.")
        else:
            df_r = pd.DataFrame(recent)
            df_r["paid_on"] = pd.to_datetime(df_r["paid_on"]).dt.strftime("%d %b %Y")
            df_r = df_r.rename(columns={
                "full_name": "Student",
                "class_name": "Class",
                "section": "Section",
                "amount": "Amount (Rs)",
                "paid_on": "Date",
                "month": "Month",
                "method": "Method",
            })
            df_r = df_r[["Student", "Class", "Section", "Amount (Rs)", "Date", "Method"]]
            st.dataframe(
                df_r,
                use_container_width=True,
                hide_index=True,
                column_config={"Amount (Rs)": st.column_config.NumberColumn(format="%d")},
            )