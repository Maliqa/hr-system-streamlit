import streamlit as st
import time
from utils.api import api_get, api_post
from core.db import get_conn
from core.leave_engine import run_leave_engine
from utils.ui import load_css
from utils.notifications import notify_leave_event



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
# ENGINE + DB
# ======================================================
run_leave_engine()
conn = get_conn()

# ======================================================
# MANAGER PROFILE
# ======================================================
profile = conn.execute("""
    SELECT nik,name,email,role,division,join_date
    FROM users WHERE id=?
""",(manager_id,)).fetchone()

nik,name,email,role,division,join_date = profile

col1, col2 = st.columns([7, 3], vertical_alignment="center")

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
# SUMMARY
# ======================================================
team_count = conn.execute(
    "SELECT COUNT(*) FROM users WHERE manager_id=?",(manager_id,)
).fetchone()[0]

pending_total = conn.execute("""
    SELECT COUNT(*) FROM leave_requests lr
    JOIN users u ON u.id=lr.user_id
    WHERE u.manager_id=? AND lr.status='submitted'
""",(manager_id,)).fetchone()[0]

# ======================================================
# MY TEAM — DATAFRAME VIEW
# ======================================================
st.subheader("👥 My Team")

team_rows = conn.execute("""
    SELECT 
        u.name,
        u.email,
        COUNT(lr.id) AS pending
    FROM users u
    LEFT JOIN leave_requests lr
        ON lr.user_id=u.id AND lr.status='submitted'
    WHERE u.manager_id=?
    GROUP BY u.id
    ORDER BY u.name
""",(manager_id,)).fetchall()

st.dataframe(
    [{
        "Name": r[0],
        "Email": r[1],
        "Pending Requests": r[2],
        "Status": "🔴 Action Needed" if r[2] > 0 else "🟢 Clear"
    } for r in team_rows],
    width="stretch"
)

st.divider()

# ======================================================
# ACTION-FIRST — NEED YOUR ACTION
# ======================================================
st.subheader("⏳ Awaiting Your Review")

urgent = conn.execute("""
    SELECT u.id,u.name,COUNT(lr.id) pending
    FROM users u
    JOIN leave_requests lr
      ON lr.user_id=u.id AND lr.status='submitted'
    WHERE u.manager_id=?
    GROUP BY u.id
    ORDER BY pending DESC
""",(manager_id,)).fetchall()

if not urgent:
    st.success("🎉 All clear. Nothing to approve.")
else:
    cols = st.columns(4)
    for i,(uid,uname,pending) in enumerate(urgent):
        with cols[i % 4]:
            if st.button(
                f"👤 {uname}\n🔴 {pending} Pending",
                key=f"focus_{uid}",
                use_container_width=True
            ):
                with st.spinner("Loading requests..."):
                    time.sleep(1)  # ⏳ SIMULATED LOADING
                st.session_state["focus_user"] = uid
                st.rerun()

# ======================================================
# PENDING REQUEST DETAIL
# ======================================================
focus_user = st.session_state.get("focus_user")

if focus_user:
    st.divider()
    st.subheader("📝 Pending Requests")

    rows = conn.execute("""
        SELECT lr.id,u.name,lr.leave_type,
               lr.start_date,lr.end_date,
               lr.total_days,lr.reason
        FROM leave_requests lr
        JOIN users u ON u.id=lr.user_id
        WHERE lr.status='submitted'
          AND u.id=?
        ORDER BY lr.created_at
    """,(focus_user,)).fetchall()

    for lr_id,emp,typ,s,e,days,reason in rows:

        with st.expander(
            f"👤 {emp} | {typ} | {s} → {e} ({days} day)",
            expanded=True
        ):
            st.write(f"**Reason:** {reason or '-'}")

            c1, c2 = st.columns(2)

            # APPROVE
            if c1.button("✅ Approve", key=f"ok_{lr_id}"):
                conn.execute("""
                    UPDATE leave_requests
                    SET status='manager_approved',
                        approved_by=?,
                        approved_at=CURRENT_TIMESTAMP
                    WHERE id=?
                """, (manager_id, lr_id))
                conn.commit()
                st.session_state.pop("focus_user", None)
                st.rerun()

            # REJECT
            if c2.button("❌ Reject", key=f"rej_{lr_id}"):
                st.session_state[f"reject_{lr_id}"] = True
                st.rerun()

            # REJECT FORM
            if st.session_state.get(f"reject_{lr_id}"):

                reject_reason = st.text_area(
                    "Reject Reason",
                    key=f"note_{lr_id}",
                    placeholder="Contoh: Bentrok jadwal tim / operasional"
                )

                rc1, rc2 = st.columns(2)

                if rc1.button("🚫 Confirm Reject", key=f"conf_{lr_id}"):
                    if not reject_reason.strip():
                        st.error("Reject reason wajib diisi")
                        st.stop()

                    conn.execute("""
                        UPDATE leave_requests
                        SET status='manager_rejected',
                            approved_by=?,
                            approved_at=CURRENT_TIMESTAMP,
                            manager_note=?
                        WHERE id=?
                    """, (manager_id, reject_reason, lr_id))
                    conn.commit()

                    del st.session_state[f"reject_{lr_id}"]
                    st.session_state.pop("focus_user", None)
                    st.rerun()

                if rc2.button("↩ Cancel", key=f"cancel_{lr_id}"):
                    del st.session_state[f"reject_{lr_id}"]
                    st.rerun()


conn.close()
