from datetime import date

import streamlit as st
import pandas as pd
import plotly.express as px

from students import get_all_students
from fees import (
    current_month_str,
    recent_months,
    month_summary,
    get_defaulters,
    get_payments_for_month,
    record_payment,
    has_paid,
    payments_by_month,
    delete_payment,
)
from exports import fees_to_excel
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


def format_month_label(m):
    names = ["January", "February", "March", "April", "May", "June",
             "July", "August", "September", "October", "November", "December"]
    y, mo = m.split("-")
    return f"{names[int(mo)-1]} {y}"


def render():
    page_header("Fees", "Collect payments and track defaulters.")

    months = recent_months(12)
    month_labels = {m: format_month_label(m) for m in months}
    default_index = months.index(current_month_str()) if current_month_str() in months else 0

    c1, c2 = st.columns([1, 3])
    with c1:
        selected_month = st.selectbox(
            "Month",
            months,
            index=default_index,
            format_func=lambda m: month_labels[m],
            key="fees_month",
        )

    s = month_summary(selected_month)
    defaulters_count = len(get_defaulters(selected_month))

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        stat_card("Expected", f"Rs {s['expected']:,.0f}", "#475569")
    with c2:
        stat_card("Collected", f"Rs {s['collected']:,.0f}", "#059669")
    with c3:
        stat_card("Pending", f"Rs {s['pending']:,.0f}", "#dc2626")
    with c4:
        stat_card("Defaulters", f"{defaulters_count}", "#f59e0b")

    st.markdown("<div style='height: 20px;'></div>", unsafe_allow_html=True)

    tab_collect, tab_defaulters, tab_history = st.tabs(
        ["Collect Payment", "Defaulters", "Payment History"]
    )

    # =====================================================
    # TAB 1 — COLLECT
    # =====================================================
    with tab_collect:
        students = get_all_students()
        if not students:
            st.info("No students in the system yet.")
            return

        all_classes = sorted({s["class_name"] for s in students if s.get("class_name")})

        c1, c2 = st.columns([1, 2])
        with c1:
            picked_class = st.selectbox(
                "Class",
                ["All classes"] + all_classes,
                key="collect_class_filter",
            )
        with c2:
            search = st.text_input(
                "Search student",
                placeholder="Type a name or roll number...",
                key="collect_search",
            )

        filtered = students
        if picked_class != "All classes":
            filtered = [s for s in filtered if s["class_name"] == picked_class]
        if search.strip():
            q = search.strip().lower()
            filtered = [
                s for s in filtered
                if q in (s["full_name"] or "").lower()
                or q in str(s.get("roll_number") or "").lower()
            ]

        if not filtered:
            st.warning("No students match your search.")
            return

        def sort_key(s):
            rn = str(s.get("roll_number") or "")
            try:
                rn_key = (0, int(rn))
            except ValueError:
                rn_key = (1, rn)
            return (s["class_name"], rn_key)

        filtered.sort(key=sort_key)

        options = {
            f"{s['full_name']}  ·  Roll {s.get('roll_number') or '-'}": s
            for s in filtered
        }
        picked_label = st.selectbox(
            f"Student ({len(filtered)} shown)",
            list(options.keys()),
            key="collect_student",
        )
        picked = options[picked_label]

        st.markdown("<div style='height: 8px;'></div>", unsafe_allow_html=True)

        already_paid = has_paid(picked["id"], selected_month)

        status_color = "#059669" if already_paid else "#dc2626"
        status_bg = "#ecfdf5" if already_paid else "#fef2f2"
        status_text = "Paid" if already_paid else "Not paid"
        initials = "".join([p[0] for p in picked['full_name'].split()[:2]]).upper()

        st.markdown(_html(f"""
            <div style="background:#ffffff; border:1px solid #e2e8f0; border-radius:10px;
                        padding:18px 20px; display:flex; align-items:center; gap:16px;">
                <div style="width:46px; height:46px; border-radius:50%;
                            background:#4338ca; color:#ffffff; font-weight:700;
                            font-size:15px; display:flex; align-items:center;
                            justify-content:center; flex-shrink:0;">{initials}</div>
                <div style="flex:1;">
                    <div style="font-weight:600; font-size:15px; color:#0f172a;">{picked['full_name']}</div>
                    <div style="font-size:13px; color:#64748b; margin-top:2px;">
                        {picked['class_name']} {picked['section'] or ''}
                        &nbsp;·&nbsp; Roll {picked.get('roll_number') or '-'}
                        &nbsp;·&nbsp; Fee Rs {picked['monthly_fee']:,.0f}
                    </div>
                </div>
                <div style="background:{status_bg}; color:{status_color};
                            font-weight:600; font-size:13px;
                            padding:6px 14px; border-radius:999px;">
                    {status_text} — {month_labels[selected_month]}
                </div>
            </div>
        """), unsafe_allow_html=True)

        st.markdown("<div style='height: 18px;'></div>", unsafe_allow_html=True)

        if already_paid:
            existing = [
                p for p in get_payments_for_month(selected_month)
                if p["student_id"] == picked["id"]
            ]

            for p in existing:
                c_info, c_action = st.columns([4, 1])
                with c_info:
                    note_part = f" &nbsp;·&nbsp; {p['note']}" if p.get('note') else ""
                    st.markdown(_html(f"""
                        <div style="background:#ecfdf5; border-left:4px solid #059669;
                                    border-radius:6px; padding:14px 16px;">
                            <div style="font-weight:600; color:#065f46; font-size:14px;">
                                Paid — Rs {p['amount']:,.0f}
                            </div>
                            <div style="color:#047857; font-size:13px; margin-top:2px;">
                                {p['paid_on']} &nbsp;·&nbsp; {p['method']}{note_part}
                            </div>
                        </div>
                    """), unsafe_allow_html=True)
                with c_action:
                    if st.button("Delete", key=f"del_pay_{p['id']}", use_container_width=True):
                        delete_payment(p["id"])
                        st.rerun()

            st.caption("Wrong amount? Delete the payment and record it again.")

        else:
            with st.form("collect_form", clear_on_submit=True):
                c1, c2 = st.columns([1, 1])
                with c1:
                    amount = st.number_input(
                        "Amount (Rs)",
                        min_value=0.0,
                        step=100.0,
                        value=float(picked["monthly_fee"] or 0),
                        format="%.0f",
                    )
                with c2:
                    method = st.selectbox(
                        "Method",
                        ["Cash", "Bank", "EasyPaisa", "JazzCash", "Other"],
                    )

                submitted = st.form_submit_button(
                    "Record Payment", use_container_width=True
                )

                if submitted:
                    if amount <= 0:
                        st.error("Amount must be greater than 0.")
                    else:
                        record_payment(
                            picked["id"], amount, selected_month,
                            method=method.lower(), note="",
                        )
                        st.success(f"Recorded Rs {amount:,.0f} for {picked['full_name']}.")
                        st.rerun()

    # =====================================================
    # TAB 2 — DEFAULTERS
    # =====================================================
    with tab_defaulters:
        defaulters = get_defaulters(selected_month)

        if not defaulters:
            st.success(f"Everyone has paid for {month_labels[selected_month]}.")
        else:
            df = pd.DataFrame(defaulters)
            df = df.sort_values(["class_name", "full_name"])
            total_pending = df["monthly_fee"].sum()

            st.markdown(
                f"<div style='color:#64748b; font-size:13px; margin-bottom:10px;'>"
                f"<b>{len(defaulters)}</b> students · "
                f"<b>Rs {total_pending:,.0f}</b> pending</div>",
                unsafe_allow_html=True,
            )

            display = df[[
                "full_name", "class_name", "section",
                "parent_name", "parent_phone", "monthly_fee",
            ]].rename(columns={
                "full_name": "Student",
                "class_name": "Class",
                "section": "Section",
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

            with st.expander("Send WhatsApp reminders", expanded=False):
                st.caption(
                    "Click Send next to any student to open WhatsApp "
                    "with a pre-filled reminder. Send as many as you like."
                )

                month_name = month_labels[selected_month]

                for d in defaulters:
                    if not d.get("parent_phone"):
                        continue

                    msg = (
                        f"Assalam-o-Alaikum {d['parent_name']},\n\n"
                        f"This is a reminder that {d['full_name']}'s fee "
                        f"for {month_name} is pending "
                        f"(Rs {d['monthly_fee']:,.0f}).\n\n"
                        f"Please arrange payment at your earliest convenience.\n\n"
                        f"Thank you."
                    )

                    phone_clean = "".join(ch for ch in str(d["parent_phone"]) if ch.isdigit())
                    if phone_clean.startswith("0"):
                        phone_clean = "92" + phone_clean[1:]

                    wa_link = (
                        f"https://wa.me/{phone_clean}"
                        f"?text={msg.replace(' ', '%20').replace(chr(10), '%0A')}"
                    )

                    c1, c2, c3, c4 = st.columns([3, 2, 1.6, 1])

                    with c1:
                        st.markdown(_html(f"""
                            <div style="padding-top:8px; font-size:14px; color:#0f172a;">
                                <b>{d['full_name']}</b>
                            </div>
                        """), unsafe_allow_html=True)

                    with c2:
                        st.markdown(_html(f"""
                            <div style="padding-top:9px; font-size:12px; color:#64748b;">
                                {d['parent_name']} &nbsp;·&nbsp; {d['parent_phone']}
                            </div>
                        """), unsafe_allow_html=True)

                    with c3:
                        st.markdown(_html(f"""
                            <div style="padding-top:8px; font-size:13px; color:#dc2626; font-weight:600;">
                                Rs {d['monthly_fee']:,.0f}
                            </div>
                        """), unsafe_allow_html=True)

                    with c4:
                        st.markdown(
                            f"""
                            <a href="{wa_link}" target="_blank" style="
                                display:inline-block;
                                background:#059669;
                                color:#ffffff;
                                padding:8px 14px;
                                border-radius:6px;
                                font-weight:600;
                                font-size:13px;
                                text-decoration:none;
                                text-align:center;
                                width:100%;
                                box-sizing:border-box;
                            ">Send</a>
                            """,
                            unsafe_allow_html=True,
                        )

                    st.markdown(_html("""
                        <div style="height:1px; background:#f1f5f9; margin:6px 0;"></div>
                    """), unsafe_allow_html=True)

    # =====================================================
    # TAB 3 — HISTORY
    # =====================================================
    with tab_history:
        # ---- Export button ----
        exp_l, exp_r = st.columns([4, 1])
        with exp_r:
            xlsx = fees_to_excel(selected_month, month_labels[selected_month])
            st.download_button(
                "Export to Excel",
                data=xlsx,
                file_name=f"fees_{selected_month}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True,
                key="export_fees_btn",
            )

        chart_data = payments_by_month(recent_months(6))
        if any(row["collected"] > 0 for row in chart_data):
            df_chart = pd.DataFrame(chart_data)
            df_chart["label"] = df_chart["month"].apply(format_month_label)

            fig = px.bar(
                df_chart,
                x="label",
                y="collected",
                labels={"label": "", "collected": "Collected (Rs)"},
                color_discrete_sequence=["#4338ca"],
            )
            fig.update_layout(
                plot_bgcolor="white",
                paper_bgcolor="white",
                margin=dict(l=10, r=10, t=10, b=10),
                height=260,
                showlegend=False,
                xaxis=dict(showgrid=False),
                yaxis=dict(gridcolor="#f1f5f9"),
            )
            st.plotly_chart(fig, use_container_width=True)

        payments = get_payments_for_month(selected_month)

        if not payments:
            st.info(f"No payments recorded for {month_labels[selected_month]}.")
        else:
            df_pay = pd.DataFrame(payments)
            display = df_pay[[
                "full_name", "class_name", "section",
                "amount", "paid_on", "method",
            ]].rename(columns={
                "full_name": "Student",
                "class_name": "Class",
                "section": "Section",
                "amount": "Amount (Rs)",
                "paid_on": "Date",
                "method": "Method",
            })

            st.dataframe(
                display,
                use_container_width=True,
                hide_index=True,
                column_config={"Amount (Rs)": st.column_config.NumberColumn(format="%d")},
            )

            with st.expander("Delete a payment"):
                del_opts = {
                    f"#{p['id']} — {p['full_name']} — Rs {p['amount']:,.0f} ({p['paid_on']})": p["id"]
                    for p in payments
                }
                picked_del = st.selectbox(
                    "Pick a payment",
                    list(del_opts.keys()),
                    key="delete_payment_pick",
                )
                if st.button("Delete", key="delete_payment_btn"):
                    delete_payment(del_opts[picked_del])
                    st.rerun()