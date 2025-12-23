import streamlit as st
from utils.api import api_get, api_post
from core.db import get_conn
from core.leave_engine import run_leave_engine
from datetime import date

st.set_page_config(page_title="Manager Dashboard", layout="wide")
st.markdown("""
<style>
section[data-testid="stSidebar"] { display: none; }
</style>
""", unsafe_allow_html=True)

# AUTH
me = api_get("/me", timeout=5)
if not (me.status_code == 200 and me.json()):
    st.switch_page("app.py")

payload = me.json()
if payload["role"] != "manager":
    st.error("Unauthorized")
    st.stop()

manager_id = payload["user_id"]

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

conn.close()
