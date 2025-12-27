import streamlit as st
from utils.api import api_get, api_post
from core.db import get_conn
from core.leave_engine import run_leave_engine
from utils.pdf_preview import preview_pdf

st.set_page_config(page_title="Manager Dashboard", layout="wide")
st.markdown("""
<style>
section[data-testid="stSidebar"] { display: none; }
</style>
""", unsafe_allow_html=True)

# ================= SESSION =================
me = api_get("/me")
if me.status_code != 200:
    st.session_state.clear()
    st.switch_page("app.py")
    st.stop()

user = me.json()
manager_id = user.get("id")
role = user.get("role")

if role != "manager":
    st.error("Access denied")
    st.stop()

# ================= ENGINE =================
run_leave_engine()

conn = get_conn()

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

    SUB = st.radio(
        "Approval Type",
        ["📝 Leave Requests", "📦 Change Off Claims"],
        horizontal=True
    )

    # ---------- LEAVE ----------
    if SUB == "📝 Leave Requests":
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
            st.info("No pending leave requests.")
        else:
            for r in rows:
                leave_id, emp, typ, s, e, d, reason = r
                with st.expander(f"{emp} | {typ} | {d} day(s)"):
                    st.write(f"{s} → {e}")
                    st.write(reason or "-")

                    action = st.radio(
                        "Action",
                        ["Approve", "Reject"],
                        key=f"act_l_{leave_id}",
                        horizontal=True
                    )
                    reject_reason = (
                        st.text_area("Reject reason", key=f"rej_l_{leave_id}")
                        if action == "Reject" else None
                    )

                    if st.button("Submit", key=f"sub_l_{leave_id}"):
                        if action == "Approve":
                            conn.execute("""
                                UPDATE leave_requests
                                SET status='manager_approved',
                                    manager_id=?,
                                    manager_approved_at=DATE('now')
                                WHERE id=?
                            """, (manager_id, leave_id))
                        else:
                            conn.execute("""
                                UPDATE leave_requests
                                SET status='manager_rejected',
                                    manager_id=?,
                                    manager_approved_at=DATE('now'),
                                    reason=?
                                WHERE id=?
                            """, (manager_id, reject_reason, leave_id))

                        conn.commit()
                        st.success("Decision saved")
                        st.rerun()

    # ---------- CHANGE OFF ----------
    if SUB == "📦 Change Off Claims":
        rows = conn.execute("""
            SELECT c.id, u.name, c.work_date,
                   c.hours, c.description, c.file_path
            FROM change_off_claims c
            JOIN users u ON u.id = c.user_id
            WHERE c.status='submitted'
            ORDER BY c.work_date
        """).fetchall()

        if not rows:
            st.info("No pending change off claims.")
        else:
            for r in rows:
                cid, name, wdate, hours, desc, path = r
                with st.expander(f"{name} | {wdate} | {hours} hours"):
                    st.write(desc)

                    if st.checkbox("👀 Preview PDF", key=f"pv_{cid}"):
                        preview_pdf(path)

                    col1, col2 = st.columns(2)

                    with col1:
                        if st.button("✅ Approve", key=f"ok_{cid}"):
                            conn.execute("""
                                UPDATE change_off_claims
                                SET status='manager_approved'
                                WHERE id=?
                            """, (cid,))
                            conn.commit()
                            st.success("Approved")
                            st.rerun()

                    with col2:
                        if st.button("❌ Reject", key=f"no_{cid}"):
                            conn.execute("""
                                UPDATE change_off_claims
                                SET status='manager_rejected'
                                WHERE id=?
                            """, (cid,))
                            conn.commit()
                            st.warning("Rejected")
                            st.rerun()

# ======================================================
# 📜 APPROVAL HISTORY
# ======================================================
else:
    st.subheader("Leave Approval History")
    rows = conn.execute("""
        SELECT u.name, lr.leave_type, lr.start_date,
               lr.end_date, lr.total_days,
               lr.status, lr.manager_approved_at
        FROM leave_requests lr
        JOIN users u ON u.id = lr.user_id
        WHERE lr.status IN ('manager_approved','manager_rejected','hr_approved','hr_rejected')
        ORDER BY lr.manager_approved_at DESC
    """).fetchall()

    st.dataframe(
        rows,
        use_container_width=True,
        column_config={
            0: "Employee",
            1: "Type",
            2: "Start",
            3: "End",
            4: "Days",
            5: "Status",
            6: "Approved At"
        }
    )

    st.subheader("Change Off Approval History")
    rows = conn.execute("""
        SELECT u.name, c.work_date, c.hours, c.status
        FROM change_off_claims c
        JOIN users u ON u.id = c.user_id
        WHERE c.status IN ('manager_approved','manager_rejected')
        ORDER BY c.work_date DESC
    """).fetchall()

    st.dataframe(rows, use_container_width=True)

conn.close()
