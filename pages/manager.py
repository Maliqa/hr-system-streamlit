import streamlit as st
from utils.api import api_get, api_post
from core.db import get_conn
from core.leave_engine import run_leave_engine
from utils.pdf_preview import preview_pdf

# ======================================================
# PAGE CONFIG
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
.card h4 {
    margin: 0;
}
.badge {
    padding: 4px 10px;
    border-radius: 12px;
    font-size: 12px;
    font-weight: bold;
}
.badge-pending { background: #facc15; color: #000; }
.badge-approved { background: #22c55e; color: #000; }
.badge-rejected { background: #ef4444; color: #fff; }
.meta {
    color: #9ca3af;
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
if user.get("role") != "manager":
    st.error("❌ Access denied")
    st.stop()

manager_id = user.get("id")

# ======================================================
# ENGINE
# ======================================================
run_leave_engine()
conn = get_conn()

# ======================================================
# HEADER
# ======================================================
st.title("👔 Manager Dashboard")
if st.button("Logout"):
    api_post("/logout")
    st.switch_page("app.py")

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

    # ============================
    # LEAVE REQUESTS
    # ============================
    if TAB == "📝 Leave Requests":

        rows = conn.execute("""
            SELECT lr.id, u.name, lr.leave_type,
                   lr.start_date, lr.end_date,
                   lr.total_days, lr.reason
            FROM leave_requests lr
            JOIN users u ON u.id = lr.user_id
            WHERE lr.status='submitted'
            ORDER BY lr.created_at
        """).fetchall()

        if not rows:
            st.info("🎉 No pending leave requests.")
        else:
            for r in rows:
                leave_id, emp, typ, s, e, days, reason = r

                st.markdown(f"""
                <div class="card">
                    <h4>👤 {emp} <span class="badge badge-pending">PENDING</span></h4>
                    <div class="meta">{typ}</div>
                    <div class="meta">📅 {s} → {e} • <b>{days} day(s)</b></div>
                    <p>{reason or "-"}</p>
                </div>
                """, unsafe_allow_html=True)

                col1, col2 = st.columns(2)

                with col1:
                    if st.button("✅ Approve", key=f"leave_ok_{leave_id}"):
                        conn.execute("""
                            UPDATE leave_requests
                            SET status='manager_approved',
                                approved_by=?,
                                approved_at=CURRENT_TIMESTAMP
                            WHERE id=?
                        """, (manager_id, leave_id))
                        conn.commit()
                        st.success("Approved")
                        st.rerun()

                with col2:
                    if st.button("❌ Reject", key=f"leave_no_{leave_id}"):
                        conn.execute("""
                            UPDATE leave_requests
                            SET status='manager_rejected',
                                approved_by=?,
                                approved_at=CURRENT_TIMESTAMP
                            WHERE id=?
                        """, (manager_id, leave_id))
                        conn.commit()
                        st.warning("Rejected")
                        st.rerun()

    # ============================
    # CHANGE OFF CLAIMS
    # ============================
    if TAB == "📦 Change Off Claims":

        rows = conn.execute("""
            SELECT c.id, u.name, c.category, c.work_type,
                   c.work_date, c.start_date, c.end_date,
                   c.daily_hours, c.co_days,
                   c.description, c.attachment
            FROM change_off_claims c
            JOIN users u ON u.id = c.user_id
            WHERE c.status='submitted'
            ORDER BY c.created_at
        """).fetchall()

        if not rows:
            st.info("🎉 No pending change off claims.")
        else:
            for r in rows:
                (
                    cid, name, category, work_type,
                    work_date, start_date, end_date,
                    hours, co_days, desc, attachment
                ) = r

                period = work_date or f"{start_date} → {end_date}"

                st.markdown(f"""
                <div class="card">
                    <h4>👤 {name} <span class="badge badge-pending">PENDING</span></h4>
                    <div class="meta">{category} • {work_type}</div>
                    <div class="meta">📅 {period}</div>
                    <div class="meta">⏱ {hours or '-'} hour(s)</div>
                    <div class="meta">📦 CO: <b>{co_days} day(s)</b></div>
                    <p>{desc or "-"}</p>
                </div>
                """, unsafe_allow_html=True)

                if attachment:
                    if st.checkbox("👀 Preview Attachment", key=f"pv_{cid}"):
                        preview_pdf(attachment)

                col1, col2 = st.columns(2)

                with col1:
                    if st.button("✅ Approve", key=f"co_ok_{cid}"):
                        conn.execute("""
                            UPDATE change_off_claims
                            SET status='manager_approved',
                                approved_by=?,
                                approved_at=CURRENT_TIMESTAMP
                            WHERE id=?
                        """, (manager_id, cid))
                        conn.commit()
                        st.success("Approved")
                        st.rerun()

                with col2:
                    if st.button("❌ Reject", key=f"co_no_{cid}"):
                        conn.execute("""
                            UPDATE change_off_claims
                            SET status='manager_rejected',
                                approved_by=?,
                                approved_at=CURRENT_TIMESTAMP
                            WHERE id=?
                        """, (manager_id, cid))
                        conn.commit()
                        st.warning("Rejected")
                        st.rerun()

# ======================================================
# 📜 APPROVAL HISTORY
# ======================================================
else:
    st.subheader("📝 Leave Approval History")

    rows = conn.execute("""
        SELECT u.name, lr.leave_type, lr.start_date,
               lr.end_date, lr.total_days,
               lr.status, lr.approved_at
        FROM leave_requests lr
        JOIN users u ON u.id = lr.user_id
        WHERE lr.status LIKE 'manager_%' OR lr.status LIKE 'hr_%'
        ORDER BY lr.approved_at DESC
    """).fetchall()

    st.dataframe(rows, use_container_width=True)

    st.subheader("📦 Change Off Approval History")

    rows = conn.execute("""
        SELECT u.name, c.work_date, c.co_days,
               c.status, c.approved_at
        FROM change_off_claims c
        JOIN users u ON u.id = c.user_id
        WHERE c.status LIKE 'manager_%' OR c.status LIKE 'hr_%'
        ORDER BY c.approved_at DESC
    """).fetchall()

    st.dataframe(rows, use_container_width=True)

conn.close()
