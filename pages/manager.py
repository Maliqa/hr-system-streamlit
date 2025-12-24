import streamlit as st
from utils.api import api_get, api_post
from core.db import get_conn
from core.leave_engine import run_leave_engine
from datetime import date
from utils.pdf_preview import preview_pdf
from utils.api import api_get, api_post
st.set_page_config(page_title="Manager Dashboard", layout="wide")
st.markdown("""
<style>
section[data-testid="stSidebar"] { display: none; }
</style>
""", unsafe_allow_html=True)

me = api_get("/me")

if me.status_code != 200:
    st.warning("Session expired. Please login again.")
    st.session_state.clear()
    st.switch_page("app.py")
    st.stop()

user = me.json()

if not isinstance(user, dict):
    st.warning("Invalid session data. Please login again.")
    st.session_state.clear()
    st.switch_page("app.py")
    st.stop()

user_id = user.get("id") or user.get("user_id") or user.get("uid")

if not user_id:
    st.error("User ID missing")
    st.stop()

role = user.get("role")


# AUTO ENGINE
run_leave_engine()

conn = get_conn()

st.title("👔 Manager Dashboard")
if st.button("Logout"):
    api_post("/logout")
    st.switch_page("app.py")

menu = st.radio("Menu", ["⏳ Pending Approval", "📜 Approval History"], horizontal=True)

# PENDING
if menu == "⏳ Pending Approval":
    rows = conn.execute("""
        SELECT lr.id, u.name, lr.leave_type, lr.start_date, lr.end_date, lr.total_days, lr.reason
        FROM leave_requests lr
        JOIN users u ON u.id = lr.user_id
        WHERE lr.status='submitted'
        ORDER BY lr.created_at
    """).fetchall()

    if not rows:
        st.info("No pending leave")
    else:
        for r in rows:
            leave_id, emp, typ, s, e, d, reason = r
            with st.expander(f"{emp} | {typ} | {d} day(s)"):
                st.write(f"{s} → {e}")
                st.write(reason or "-")

                action = st.radio("Action", ["Approve", "Reject"], key=f"a_{leave_id}", horizontal=True)
                reject_reason = st.text_area("Reject reason", key=f"r_{leave_id}") if action == "Reject" else None

                if st.button("Submit", key=f"s_{leave_id}"):
                    if action == "Approve":
                        conn.execute("""
                            UPDATE leave_requests
                            SET status='manager_approved', manager_id=?, manager_approved_at=DATE('now')
                            WHERE id=?
                        """, (manager_id, leave_id))
                    else:
                        conn.execute("""
                            UPDATE leave_requests
                            SET status='manager_rejected', manager_id=?, manager_approved_at=DATE('now'), reason=?
                            WHERE id=?
                        """, (manager_id, reject_reason, leave_id))
                    conn.commit()
                    st.success("Decision saved")
                    st.rerun()

# HISTORY
else:
    rows = conn.execute("""
        SELECT u.name, lr.leave_type, lr.start_date, lr.end_date, lr.total_days, lr.status, lr.manager_approved_at
        FROM leave_requests lr
        JOIN users u ON u.id = lr.user_id
        WHERE lr.status IN ('manager_approved','manager_rejected','hr_approved','hr_rejected')
        ORDER BY lr.manager_approved_at DESC
    """).fetchall()

    st.dataframe(
        rows,
        width="stretch",
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


rows = conn.execute("""
    SELECT id, user_id, work_date, hours, description, attachment_path
    FROM change_off_requests
    WHERE status='submitted'
    ORDER BY created_at DESC
""").fetchall()

for r in rows:
    req_id, uid, wdate, hours, desc, path = r

    with st.expander(f"👤 User {uid} | {wdate} | {hours} hours"):
        st.write(desc)

        if st.checkbox("👀 Preview PDF", key=f"pv_{req_id}"):
            preview_pdf(path)

        col1, col2 = st.columns(2)

        with col1:
            if st.button("✅ Approve", key=f"ok_{req_id}"):
                conn.execute("""
                    UPDATE change_off_requests
                    SET status='approved'
                    WHERE id=?
                """, (req_id,))
                conn.commit()
                st.success("Approved")
                st.rerun()

        with col2:
            if st.button("❌ Reject", key=f"no_{req_id}"):
                conn.execute("""
                    UPDATE change_off_requests
                    SET status='rejected'
                    WHERE id=?
                """, (req_id,))
                conn.commit()
                st.warning("Rejected")
                st.rerun()


conn.close()
