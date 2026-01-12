import streamlit as st
from utils.api import api_get, api_post
from core.db import get_conn
from core.leave_engine import run_leave_engine
from utils.pdf_preview import preview_pdf

# EMAIL
from utils.emailer import send_email
from utils.email_templates import leave_status_email

# ======================================================
# PAGE CONFIG + STYLE
# ======================================================
st.set_page_config(page_title="Manager Dashboard", layout="wide")
st.markdown("""
<style>
section[data-testid="stSidebar"] { display: none; }
.card {
    background-color: #0e1117;
    border: 1px solid #2a2e35;
    border-radius: 14px;
    padding: 18px;
    margin-bottom: 18px;
}
.profile-card {
    border:1px solid #e5e7eb;
    border-radius:14px;
    padding:18px;
    margin-bottom:24px;
    background:#fafafa;
}
.badge {
    padding: 4px 10px;
    border-radius: 12px;
    font-size: 12px;
    font-weight: bold;
}
.badge-pending { background: #facc15; color: #000; }
.meta {
    color: #6b7280;
    font-size: 13px;
    margin-top: 4px;
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

manager_id = user.get("id") or user.get("user_id") or user.get("uid")
if not manager_id:
    st.error("Invalid session")
    st.stop()

# ======================================================
# ENGINE + DB
# ======================================================
run_leave_engine()
conn = get_conn()

# ======================================================
# FETCH MANAGER PROFILE (SAFE, READ ONLY)
# ======================================================
profile = conn.execute("""
    SELECT
        nik,
        name,
        email,
        role,
        division,
        join_date,
        permanent_date
    FROM users
    WHERE id = ?
""", (manager_id,)).fetchone()

(
    nik,
    name,
    email,
    role,
    division,
    join_date,
    permanent_date
) = profile

# ======================================================
# HEADER
# ======================================================
st.title("👔 Manager Dashboard")

if st.button("Logout"):
    api_post("/logout")
    st.switch_page("app.py")

# ======================================================
# MANAGER PROFILE CARD (NEW, SAFE)
# ======================================================
st.markdown(f"""
<div class="profile-card">
    <h4>👤 {name}</h4>
    <div class="meta">
        {role.upper()} • {division or '-'} • NIK {nik}
    </div>
    <div style="margin-top:8px;">
        📧 {email}<br>
        📅 Join Date: {join_date or '-'}<br>
        🏁 Permanent Date: {permanent_date or '-'}
    </div>
</div>
""", unsafe_allow_html=True)

# ======================================================
# SUMMARY METRICS
# ======================================================
team_count = conn.execute(
    "SELECT COUNT(*) FROM users WHERE manager_id=?",
    (manager_id,)
).fetchone()[0]

pending_count = conn.execute("""
    SELECT COUNT(*) FROM leave_requests lr
    JOIN users u ON u.id = lr.user_id
    WHERE u.manager_id=? AND lr.status='submitted'
""", (manager_id,)).fetchone()[0]

approved_month = conn.execute("""
    SELECT COUNT(*) FROM leave_requests
    WHERE approved_by=? AND status='manager_approved'
      AND strftime('%Y-%m', approved_at)=strftime('%Y-%m','now')
""", (manager_id,)).fetchone()[0]

c1, c2, c3 = st.columns(3)
c1.metric("👥 Team Members", team_count)
c2.metric("⏳ Pending Approvals", pending_count)
c3.metric("✅ Approved This Month", approved_month)

st.divider()

# ======================================================
# MY TEAM
# ======================================================
st.subheader("👥 My Team")

team = conn.execute("""
    SELECT u.name,
           COUNT(lr.id) AS pending
    FROM users u
    LEFT JOIN leave_requests lr
        ON lr.user_id=u.id AND lr.status='submitted'
    WHERE u.manager_id=?
    GROUP BY u.id
    ORDER BY u.name
""", (manager_id,)).fetchall()

if not team:
    st.info("No team members assigned.")
else:
    for name, pending in team:
        col1, col2, col3 = st.columns([4, 2, 1])
        col1.write(f"👤 {name}")
        col2.write(f"Pending: {pending}")
        col3.write("🟢" if pending == 0 else "🔴")

st.divider()

# ======================================================
# MENU
# ======================================================
MENU = st.radio(
    "Menu",
    ["⏳ Pending Approval", "📜 Approval History"],
    horizontal=True
)

# ======================================================
# ⏳ PENDING APPROVAL
# ======================================================
if MENU == "⏳ Pending Approval":

    TAB = st.radio(
        "Approval Type",
        ["📝 Leave Requests", "📦 Change Off Claims"],
        horizontal=True
    )

    # ==================================================
    # LEAVE REQUESTS
    # ==================================================
    if TAB == "📝 Leave Requests":

        rows = conn.execute("""
            SELECT
                lr.id,
                u.name,
                u.email,
                lr.leave_type,
                lr.start_date,
                lr.end_date,
                lr.total_days,
                lr.reason
            FROM leave_requests lr
            JOIN users u ON u.id = lr.user_id
            WHERE lr.status='submitted'
              AND u.manager_id=?
            ORDER BY lr.created_at
        """, (manager_id,)).fetchall()

        if not rows:
            st.success("🎉 All clear! No pending leave requests.")
        else:
            for lr_id, emp, emp_email, typ, s, e, days, reason in rows:
                st.markdown(f"""
                <div class="card">
                    <b>👤 {emp}</b>
                    <div class="meta">{typ}</div>
                    <div class="meta">📅 {s} → {e} • {days} day(s)</div>
                    <p>{reason or '-'}</p>
                </div>
                """, unsafe_allow_html=True)

                c1, c2 = st.columns(2)

                # APPROVE
                if c1.button("✅ Approve", key=f"a{lr_id}"):
                    conn.execute("""
                        UPDATE leave_requests
                        SET status='manager_approved',
                            approved_by=?,
                            approved_at=CURRENT_TIMESTAMP
                        WHERE id=?
                    """, (manager_id, lr_id))
                    conn.commit()

                    try:
                        send_email(
                            to=emp_email,
                            subject="Leave Request Approved by Manager",
                            html=leave_status_email(
                                emp, typ, "APPROVED by Manager"
                            )
                        )
                    except Exception:
                        pass

                    st.rerun()

                # REJECT
                if c2.button("❌ Reject", key=f"r{lr_id}"):
                    conn.execute("""
                        UPDATE leave_requests
                        SET status='manager_rejected',
                            approved_by=?,
                            approved_at=CURRENT_TIMESTAMP
                        WHERE id=?
                    """, (manager_id, lr_id))
                    conn.commit()

                    try:
                        send_email(
                            to=emp_email,
                            subject="Leave Request Rejected by Manager",
                            html=leave_status_email(
                                emp, typ, "REJECTED by Manager"
                            )
                        )
                    except Exception:
                        pass

                    st.rerun()

    # ==================================================
    # CHANGE OFF CLAIMS
    # ==================================================
    if TAB == "📦 Change Off Claims":

        rows = conn.execute("""
            SELECT
                c.id,
                u.name,
                u.email,
                c.co_days,
                c.work_date,
                c.start_date,
                c.end_date,
                c.description,
                c.attachment
            FROM change_off_claims c
            JOIN users u ON u.id = c.user_id
            WHERE c.status='submitted'
              AND u.manager_id=?
            ORDER BY c.created_at
        """, (manager_id,)).fetchall()

        if not rows:
            st.success("🎉 No pending change off claims.")
        else:
            for cid, name, email, days, wdate, sdate, edate, desc, attach in rows:
                period = wdate or f"{sdate} → {edate}"

                st.markdown(f"""
                <div class="card">
                    <b>👤 {name}</b>
                    <div class="meta">📅 {period}</div>
                    <div class="meta">📦 CO: {days} day(s)</div>
                    <p>{desc or '-'}</p>
                </div>
                """, unsafe_allow_html=True)

                if attach:
                    if st.checkbox("Preview Attachment", key=f"pv{cid}"):
                        preview_pdf(attach)

                c1, c2 = st.columns(2)

                if c1.button("✅ Approve", key=f"co_a{cid}"):
                    conn.execute("""
                        UPDATE change_off_claims
                        SET status='manager_approved',
                            approved_by=?,
                            approved_at=CURRENT_TIMESTAMP
                        WHERE id=?
                    """, (manager_id, cid))
                    conn.commit()
                    st.rerun()

                if c2.button("❌ Reject", key=f"co_r{cid}"):
                    conn.execute("""
                        UPDATE change_off_claims
                        SET status='manager_rejected',
                            approved_by=?,
                            approved_at=CURRENT_TIMESTAMP
                        WHERE id=?
                    """, (manager_id, cid))
                    conn.commit()
                    st.rerun()

# ======================================================
# 📜 APPROVAL HISTORY
# ======================================================
else:
    st.subheader("📜 Approval History")

    rows = conn.execute("""
        SELECT u.name, lr.leave_type, lr.start_date,
               lr.end_date, lr.total_days,
               lr.status, lr.approved_at
        FROM leave_requests lr
        JOIN users u ON u.id = lr.user_id
        WHERE lr.approved_by=?
        ORDER BY lr.approved_at DESC
    """, (manager_id,)).fetchall()

    st.dataframe(rows, width="stretch")

conn.close()
