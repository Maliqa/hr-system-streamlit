import streamlit as st
import time
from utils.api import api_get, api_post
from core.db import get_conn
from core.leave_engine import run_leave_engine
from utils.ui import load_css

# ======================================================
# PAGE CONFIG + STYLE
# ======================================================
st.set_page_config(page_title="Manager Dashboard", layout="wide")
load_css("assets/styles/global.css")

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

.meta {
    color:#6b7280;
    font-size:13px;
    margin-top:4px;
}

/* My Team email buttons */
button[kind="secondary"] {
    max-width: 420px;
    text-align: left;
}

/* Optional: hover effect biar cakep */
button[kind="secondary"]:hover {
    background-color: #e5e7eb;
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
# MY TEAM (CLICKABLE EMAIL LIST)
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

for uid, email, pending_leave, pending_co in team_rows:
    total_pending = pending_leave + pending_co
    icon = "✉️" if total_pending > 0 else "📭"

    if st.button(
        f"{icon} {email}",
        key=f"team_{uid}",
        use_container_width=True
    ):
        st.session_state["focus_user"] = uid
        st.rerun()

# ======================================================
# PENDING APPROVALS (PER USER)
# ======================================================
focus_user = st.session_state.get("focus_user")

if focus_user:
    emp = conn.execute(
        "SELECT name, email FROM users WHERE id=?",
        (focus_user,)
    ).fetchone()

    if emp:
        st.divider()
        st.subheader(f"⏳ Pending Approvals — {emp[1]}")

        # ---------------- LEAVE REQUESTS ----------------
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

                    if c1.button("✅ Approve", key=f"leave_ok_{lr_id}"):
                        conn.execute("""
                            UPDATE leave_requests
                            SET status='manager_approved',
                                approved_by=?,
                                approved_at=CURRENT_TIMESTAMP
                            WHERE id=?
                        """, (manager_id, lr_id))
                        conn.commit()
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
                        st.rerun()
        else:
            st.info("No pending Leave Requests.")

        # ---------------- CHANGE OFF CLAIMS ----------------
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

                    if c1.button("✅ Approve", key=f"co_ok_{cid}"):
                        conn.execute("""
                            UPDATE change_off_claims
                            SET status='manager_approved',
                                approved_by=?,
                                approved_at=CURRENT_TIMESTAMP
                            WHERE id=?
                        """, (manager_id, cid))
                        conn.commit()
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
                        st.rerun()
        else:
            st.info("No pending Change Off Claims.")

conn.close()
