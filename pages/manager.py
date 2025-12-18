import streamlit as st
import pandas as pd
from datetime import datetime
from core.db import get_conn
from core.auth import require_role, logout

# =========================
# AUTH
# =========================
require_role("manager")

st.title("👔 Manager Dashboard")

# Logout
col1, col2 = st.columns([8, 2])
with col2:
    if st.button("🚪 Logout"):
        logout()

conn = get_conn()
manager_id = st.session_state["user_id"]

# =========================
# MENU
# =========================
menu = st.radio(
    "Menu",
    ["⏳ Pending Leave Approval", "📜 Approval History"],
    horizontal=True
)

# ======================================================
# PENDING APPROVAL
# ======================================================
if menu == "⏳ Pending Leave Approval":
    st.subheader("⏳ Pending Leave Approval")

    df = pd.read_sql("""
        SELECT
            lr.id,
            u.name AS employee_name,
            lr.leave_type,
            lr.start_date,
            lr.end_date,
            lr.total_days,
            lr.reason
        FROM leave_requests lr
        JOIN users u ON lr.user_id = u.id
        WHERE lr.status = 'pending'
        ORDER BY lr.created_at
    """, conn)

    if df.empty:
        st.info("Tidak ada leave request yang menunggu approval")
    else:
        st.dataframe(df, width="stretch")

        selected_id = st.selectbox(
            "Pilih Leave Request",
            df["id"].tolist()
        )

        action = st.radio(
            "Action",
            ["Approve", "Reject"],
            horizontal=True
        )

        reject_reason = None
        if action == "Reject":
            reject_reason = st.text_area("Alasan Reject (wajib)")

        if st.button("Submit Decision"):
            # Fetch leave request
            lr = conn.execute("""
                SELECT user_id, leave_type, total_days
                FROM leave_requests
                WHERE id=?
            """, (selected_id,)).fetchone()

            user_id, leave_type, total_days = lr

            # Fetch saldo
            saldo = conn.execute("""
                SELECT last_year, current_year, change_off, sick_no_doc
                FROM leave_balance
                WHERE user_id=?
            """, (user_id,)).fetchone()

            last_year, current_year, change_off, sick_no_doc = saldo

            if action == "Approve":
                # =========================
                # POTONG SALDO
                # =========================
                if leave_type == "Annual Leave":
                    if total_days <= last_year:
                        last_year -= total_days
                    else:
                        remaining = total_days - last_year
                        last_year = 0
                        current_year -= remaining

                elif leave_type == "Change Off":
                    change_off -= total_days

                elif leave_type == "Sick (No Doc)":
                    sick_no_doc += total_days

                # Update saldo
                conn.execute("""
                    UPDATE leave_balance
                    SET last_year=?, current_year=?, change_off=?, sick_no_doc=?, updated_at=DATE('now')
                    WHERE user_id=?
                """, (
                    last_year,
                    current_year,
                    change_off,
                    sick_no_doc,
                    user_id
                ))

                # Update leave request
                conn.execute("""
                    UPDATE leave_requests
                    SET status='approved', approved_by=?, approved_at=DATETIME('now')
                    WHERE id=?
                """, (manager_id, selected_id))

                conn.commit()
                st.success("Leave berhasil di-APPROVE dan saldo dipotong")
                st.rerun()

            else:  # Reject
                if not reject_reason:
                    st.error("Alasan reject wajib diisi")
                    st.stop()

                conn.execute("""
                    UPDATE leave_requests
                    SET status='rejected', approved_by=?, approved_at=DATETIME('now'), reason=?
                    WHERE id=?
                """, (
                    manager_id,
                    reject_reason,
                    selected_id
                ))

                conn.commit()
                st.success("Leave berhasil di-REJECT")
                st.rerun()

# ======================================================
# APPROVAL HISTORY
# ======================================================
elif menu == "📜 Approval History":
    st.subheader("📜 Approval History")

    df = pd.read_sql("""
        SELECT
            u.name AS employee_name,
            lr.leave_type,
            lr.start_date,
            lr.end_date,
            lr.total_days,
            lr.status,
            lr.approved_at
        FROM leave_requests lr
        JOIN users u ON lr.user_id = u.id
        WHERE lr.status IN ('approved', 'rejected')
        ORDER BY lr.approved_at DESC
    """, conn)

    if df.empty:
        st.info("Belum ada history approval")
    else:
        st.dataframe(df, width="stretch")
