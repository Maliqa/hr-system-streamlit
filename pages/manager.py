import streamlit as st
import pandas as pd
from datetime import datetime

from utils.api import api_get, api_post
from utils.emailer import send_email
from utils.ui import load_css

from core.db import get_conn
from core.leave_engine import run_leave_engine


# ======================================================
# PAGE CONFIG
# ======================================================
st.set_page_config(page_title="Manager Dashboard", layout="wide")
load_css("assets/styles/global.css")

st.markdown("""
<style>
section[data-testid="stSidebar"] { display: none; }

.profile-card {
    border:1px solid #e5e7eb;
    border-radius:14px;
    padding:18px;
    margin-bottom:24px;
    background:#fafafa;
}

.meta {
    color:#6b7280;
    font-size:13px;
    margin-top:4px;
}

.small-btn button {
    padding: 0.25rem 0.6rem;
    font-size: 14px;
}
</style>
""", unsafe_allow_html=True)


# ======================================================
# AUTH
# ======================================================
me = api_get("/me")
if me.status_code != 200:
    st.session_state.clear()
    st.switch_page("app.py")
    st.stop()

user = me.json()
if not user or user.get("role") != "manager":
    st.session_state.clear()
    st.switch_page("app.py")
    st.stop()

manager_id = user.get("id") or user.get("user_id")
if not manager_id:
    st.error("Invalid session")
    st.stop()


# ======================================================
# DB
# ======================================================
run_leave_engine()
conn = get_conn()


# ======================================================
# HELPER
# ======================================================
def get_hr_emails(conn):
    rows = conn.execute(
        "SELECT email FROM users WHERE role='hr'"
    ).fetchall()
    return [r[0] for r in rows]


# ======================================================
# MANAGER PROFILE
# ======================================================
profile = conn.execute("""
    SELECT nik, name, email, role, division, join_date
    FROM users WHERE id=?
""", (manager_id,)).fetchone()

nik, name, email, role, division, join_date = profile

col1, col2 = st.columns([7, 3])

with col1:
    st.title("👔 Manager Dashboard")
    if st.button("Logout"):
        api_post("/logout")
        st.switch_page("app.py")

with col2:
    st.image("assets/cistech.png", width=220)

st.markdown(f"""
<div class="profile-card">
    <h4>👤 {name}</h4>
    <div class="meta">{role.upper()} • {division} • NIK {nik}</div>
    <div class="meta">📧 {email}</div>
    <div class="meta">📅 Join Date: {join_date}</div>
</div>
""", unsafe_allow_html=True)


# ======================================================
# MY TEAM
# ======================================================
st.subheader("👥 My Team")

team_rows = conn.execute("""
    SELECT 
        u.id,
        u.email,
        COUNT(DISTINCT lr.id) AS pending_leave,
        COUNT(DISTINCT co.id) AS pending_co
    FROM users u
    LEFT JOIN leave_requests lr
        ON lr.user_id=u.id AND lr.status='submitted'
    LEFT JOIN change_off_claims co
        ON co.user_id=u.id AND co.status='submitted'
    WHERE u.manager_id=?
    GROUP BY u.id
    ORDER BY u.email
""", (manager_id,)).fetchall()

if not team_rows:
    st.info("No team members.")
else:
    df_team = pd.DataFrame(
        team_rows,
        columns=["user_id", "email", "pending_leave", "pending_co"]
    )

    df_team["total_pending"] = (
        df_team["pending_leave"] + df_team["pending_co"]
    )

    df_team["status"] = df_team["total_pending"].apply(
        lambda x: "🔴" if x > 0 else "🟢"
    )

    st.dataframe(
        df_team[["email", "status", "total_pending"]]
        .rename(columns={
            "email": "Email",
            "status": "Status",
            "total_pending": "Pending"
        }),
        hide_index=True,
        width="stretch"
    )

    selectable = df_team[df_team["total_pending"] > 0]

    if not selectable.empty:
        selected_email = st.selectbox(
            "📨 View Pending Requests for:",
            selectable["email"]
        )

        selected_user = selectable[
            selectable["email"] == selected_email
        ].iloc[0]

        if st.button("🔍 Open Pending Approvals"):
            st.session_state["focus_user"] = int(selected_user["user_id"])
            st.rerun()


# ======================================================
# PENDING APPROVALS
# ======================================================
focus_user = st.session_state.get("focus_user")

if focus_user:
    emp = conn.execute(
        "SELECT name, email FROM users WHERE id=?",
        (focus_user,)
    ).fetchone()

    if emp:
        emp_name, emp_email = emp
        hr_emails = get_hr_emails(conn)

        st.divider()
        st.subheader(f"📨 Pending Approvals — {emp_email}")

        # ================= LEAVE REQUEST =================
        leave_rows = conn.execute("""
            SELECT id, leave_type, start_date, end_date, total_days, reason
            FROM leave_requests
            WHERE user_id=? AND status='submitted'
            ORDER BY created_at
        """, (focus_user,)).fetchall()

        if leave_rows:
            st.markdown("### ✏️ Leave Requests")
            for lr_id, typ, s, e, days, reason in leave_rows:
                with st.expander(
                    f"{typ} | {s} → {e} ({days} day)",
                    expanded=True
                ):
                    st.write(reason or "-")
                    c1, c2 = st.columns(2)

                    recipients = [emp_email] + hr_emails

                    if c1.button("✅ Approve", key=f"leave_ok_{lr_id}"):
                        conn.execute("""
                            UPDATE leave_requests
                            SET status='manager_approved',
                                approved_by=?,
                                approved_at=CURRENT_TIMESTAMP
                            WHERE id=?
                        """, (manager_id, lr_id))
                        conn.commit()

                        send_email(
                            to_email=recipients,
                            subject="Leave Request Approved",
                            body=f"""
Hi {emp_name},

Your leave request has been APPROVED.

Leave Type : {typ}
Period     : {s} to {e}
Total Days : {days}

Regards,
HR System
"""
                        )
                        st.success("Leave approved & notification sent")
                        st.rerun()

                    if c2.button("❌ Reject", key=f"leave_rej_{lr_id}"):
                        conn.execute("""
                            UPDATE leave_requests
                            SET status='manager_rejected',
                                approved_by=?,
                                approved_at=CURRENT_TIMESTAMP
                            WHERE id=?
                        """, (manager_id, lr_id))
                        conn.commit()

                        send_email(
                            to_email=recipients,
                            subject="Leave Request Rejected",
                            body=f"""
Hi {emp_name},

Your leave request has been REJECTED.

Leave Type : {typ}
Period     : {s} to {e}

Please contact your manager or HR.

Regards,
HR System
"""
                        )
                        st.warning("Leave rejected & notification sent")
                        st.rerun()
        else:
            st.info("No pending Leave Requests.")

        # ================= CHANGE OFF =================
        co_rows = conn.execute("""
            SELECT id, work_type, work_date, co_days, description
            FROM change_off_claims
            WHERE user_id=? AND status='submitted'
            ORDER BY created_at
        """, (focus_user,)).fetchall()

        if co_rows:
            st.markdown("### 📦 Change Off Claims")
            for cid, wt, d, co, desc in co_rows:
                with st.expander(
                    f"{wt.upper()} | {co} day(s)",
                    expanded=True
                ):
                    st.write(f"📅 Date: {d}")
                    st.write(f"📝 {desc or '-'}")
                    c1, c2 = st.columns(2)

                    recipients = [emp_email] + hr_emails

                    if c1.button("✅ Approve", key=f"co_ok_{cid}"):
                        conn.execute("""
                            UPDATE change_off_claims
                            SET status='manager_approved',
                                approved_by=?,
                                approved_at=CURRENT_TIMESTAMP
                            WHERE id=?
                        """, (manager_id, cid))
                        conn.commit()

                        send_email(
                            to_email=recipients,
                            subject="Change Off Claim Approved",
                            body=f"""
Hi {emp_name},

Your Change Off claim has been APPROVED.

Work Type : {wt}
Date      : {d}
CO Days   : {co}

Regards,
HR System
"""
                        )
                        st.success("Change Off approved & notification sent")
                        st.rerun()

                    if c2.button("❌ Reject", key=f"co_rej_{cid}"):
                        conn.execute("""
                            UPDATE change_off_claims
                            SET status='manager_rejected',
                                approved_by=?,
                                approved_at=CURRENT_TIMESTAMP
                            WHERE id=?
                        """, (manager_id, cid))
                        conn.commit()

                        send_email(
                            to_email=recipients,
                            subject="Change Off Claim Rejected",
                            body=f"""
Hi {emp_name},

Your Change Off claim has been REJECTED.

Work Type : {wt}
Date      : {d}

Please contact your manager or HR.

Regards,
HR System
"""
                        )
                        st.warning("Change Off rejected & notification sent")
                        st.rerun()
        else:
            st.info("No pending Change Off Claims.")

conn.close()
