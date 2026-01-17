import streamlit as st
from utils.api import api_get, api_post
from core.db import get_conn
from core.leave_engine import run_leave_engine
from utils.ui import load_css
import pandas as pd

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
# MY TEAM (DATAFRAME-LIKE, CLICKABLE)
# ======================================================
# ======================================================
# MY TEAM (COMPACT DATAFRAME)
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

    # ====== DATAFRAME VIEW ======
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

    st.caption("🔴 = Ada pending approval | 🟢 = Tidak ada pending")

    # ====== SELECT EMPLOYEE ======
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

            st.markdown('</div>', unsafe_allow_html=True)

# ======================================================
# PENDING APPROVALS PER EMPLOYEE
# ======================================================
focus_user = st.session_state.get("focus_user")

if focus_user:
    emp = conn.execute(
        "SELECT name, email FROM users WHERE id=?",
        (focus_user,)
    ).fetchone()

    if emp:
        st.divider()
        st.subheader(f"📨 Pending Approvals — {emp[1]}")

        # ---------- LEAVE REQUESTS ----------
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

        # ---------- CHANGE OFF CLAIMS ----------
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
