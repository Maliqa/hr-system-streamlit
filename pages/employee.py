import streamlit as st
import pandas as pd
from datetime import timedelta
from core.db import get_conn
from core.auth import require_role, logout

# =========================
# AUTH
# =========================
require_role("employee")

st.title("👤 Employee Dashboard")

# Logout
col1, col2 = st.columns([8, 2])
with col2:
    if st.button("🚪 Logout"):
        logout()

conn = get_conn()
user_id = st.session_state["user_id"]

# =========================
# MENU
# =========================
menu = st.radio(
    "Menu",
    ["📄 Profile & Saldo", "➕ Submit Leave", "📜 Leave History"],
    horizontal=True
)

# =========================
# FETCH PROFILE
# =========================
profile = conn.execute("""
    SELECT nik, name, email, role, join_date, permanent_date
    FROM users
    WHERE id=?
""", (user_id,)).fetchone()

# =========================
# FETCH SALDO (SAFE)
# =========================
saldo = conn.execute("""
    SELECT last_year, current_year, change_off, sick_no_doc
    FROM leave_balance
    WHERE user_id=?
""", (user_id,)).fetchone()

# Auto-create saldo jika belum ada
if saldo is None:
    conn.execute("""
        INSERT INTO leave_balance (user_id, last_year, current_year, change_off, sick_no_doc)
        VALUES (?, 0, 0, 0, 0)
    """, (user_id,))
    conn.commit()
    saldo = (0, 0, 0, 0)

last_year, current_year, change_off, sick_no_doc = saldo

# ======================================================
# PROFILE & SALDO
# ======================================================
if menu == "📄 Profile & Saldo":
    st.subheader("👤 Profile")

    col1, col2 = st.columns(2)
    with col1:
        st.text_input("NIK", profile[0], disabled=True)
        st.text_input("Name", profile[1], disabled=True)
        st.text_input("Email", profile[2], disabled=True)
    with col2:
        st.text_input("Role", profile[3], disabled=True)
        st.text_input("Join Date", profile[4], disabled=True)
        st.text_input(
            "Permanent Date",
            profile[5] if profile[5] else "-",
            disabled=True
        )

    st.subheader("🧮 Leave Balance")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Last Year", last_year)
    c2.metric("Current Year", current_year)
    c3.metric("Change Off", change_off)
    c4.metric("Sick (No Doc)", sick_no_doc)

    st.info(
        "Saldo cuti otomatis digunakan dari Last Year terlebih dahulu, "
        "kemudian Current Year. Jika saldo habis, gunakan Change Off."
    )

# ======================================================
# SUBMIT LEAVE
# ======================================================
elif menu == "➕ Submit Leave":
    st.subheader("➕ Submit Leave")

    leave_type = st.selectbox(
        "Jenis Cuti",
        ["Annual Leave", "Change Off", "Sick (No Doc)"]
    )

    col1, col2 = st.columns(2)
    with col1:
        start_date = st.date_input("Tanggal Mulai")
    with col2:
        end_date = st.date_input("Tanggal Selesai")

    reason = st.text_area("Alasan")

    # Validasi tanggal
    if end_date < start_date:
        st.error("Tanggal selesai tidak boleh lebih kecil dari tanggal mulai")
        st.stop()

    # Hitung hari kerja (exclude weekend)
    total_days = 0
    current = start_date
    while current <= end_date:
        if current.weekday() < 5:  # Senin - Jumat
            total_days += 1
        current += timedelta(days=1)

    st.info(f"Total hari kerja yang diajukan: **{total_days} hari**")

    if st.button("Submit Leave"):
        if total_days <= 0:
            st.error("Tidak ada hari kerja yang diajukan")
            st.stop()

        # VALIDASI SALDO
        if leave_type == "Annual Leave":
            if total_days > (last_year + current_year):
                st.error("Saldo cuti tahunan tidak mencukupi")
                st.stop()

        elif leave_type == "Change Off":
            if total_days > change_off:
                st.error("Saldo Change Off tidak mencukupi")
                st.stop()

        elif leave_type == "Sick (No Doc)":
            if sick_no_doc + total_days > 6:
                st.error("Melebihi batas sakit tanpa surat dokter (6 hari)")
                st.stop()

        # INSERT REQUEST (TANPA POTONG SALDO)
        conn.execute("""
            INSERT INTO leave_requests
            (user_id, leave_type, start_date, end_date, total_days, reason, status, created_at)
            VALUES (?, ?, ?, ?, ?, ?, 'pending', datetime('now'))
        """, (
            user_id,
            leave_type,
            start_date.isoformat(),
            end_date.isoformat(),
            total_days,
            reason
        ))
        conn.commit()

        st.success("Leave berhasil diajukan dan menunggu approval")
        st.rerun()

# ======================================================
# LEAVE HISTORY
# ======================================================
elif menu == "📜 Leave History":
    st.subheader("📜 Leave History")

    df = pd.read_sql("""
        SELECT start_date, end_date, leave_type, total_days, status, created_at
        FROM leave_requests
        WHERE user_id=?
        ORDER BY created_at DESC
    """, conn, params=(user_id,))

    if df.empty:
        st.info("Belum ada pengajuan cuti")
    else:
        st.dataframe(df, width="stretch")
