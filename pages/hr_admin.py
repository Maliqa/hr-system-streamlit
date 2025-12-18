import streamlit as st
import pandas as pd
from core.db import get_conn
from core.auth import require_role, hash_password, logout

# =========================
# AUTH
# =========================
require_role("hr")

st.title("🏢 HR Admin Dashboard")

# Logout button
col1, col2 = st.columns([8, 2])
with col2:
    if st.button("🚪 Logout"):
        logout()

conn = get_conn()

# =========================
# MENU
# =========================
menu = st.radio(
    "Menu",
    [
        "➕ Create User",
        "✏️ Edit User",
        "🔐 Reset Password",
        "🧮 Edit Saldo Cuti",
        "📋 User List",
        "🗑️ Delete User"
    ],
    horizontal=True
)

# =========================
# FETCH USERS
# =========================
users_df = pd.read_sql("""
    SELECT id, nik, name, email, role, join_date, permanent_date
    FROM users
    ORDER BY name
""", conn)

user_map = {
    f"{row['name']} ({row['email']})": row["id"]
    for _, row in users_df.iterrows()
}

# ======================================================
# CREATE USER
# ======================================================
if menu == "➕ Create User":
    st.subheader("➕ Create User")

    with st.form("create_user"):
        nik = st.text_input("NIK")
        name = st.text_input("Name")
        email = st.text_input("Email")
        role = st.selectbox("Role", ["employee", "manager", "hr"])
        join_date = st.date_input("Join Date")
        permanent_date = st.date_input(
            "Permanent Date (optional)",
            value=None
        )
        password = st.text_input("Password", type="password")

        submit = st.form_submit_button("Create User")

        if submit:
            if not all([nik, name, email, password, join_date]):
                st.error("NIK, Name, Email, Password, dan Join Date wajib diisi")
            else:
                try:
                    conn.execute("""
                        INSERT INTO users
                        (nik, name, email, role, password_hash, join_date, permanent_date)
                        VALUES (?, ?, ?, ?, ?, ?, ?)
                    """, (
                        nik,
                        name,
                        email,
                        role,
                        hash_password(password),
                        join_date,
                        permanent_date
                    ))

                    user_id = conn.execute(
                        "SELECT last_insert_rowid()"
                    ).fetchone()[0]

                    conn.execute(
                        "INSERT INTO leave_balance (user_id) VALUES (?)",
                        (user_id,)
                    )

                    conn.commit()
                    st.success("User berhasil dibuat")
                    st.info("Sampaikan email & password ke user")
                    st.rerun()

                except Exception:
                    st.error("Email atau NIK sudah digunakan")

# ======================================================
# EDIT USER
# ======================================================
elif menu == "✏️ Edit User":
    st.subheader("✏️ Edit User")

    selected = st.selectbox("Pilih User", user_map.keys())
    user_id = user_map[selected]

    user = conn.execute("""
        SELECT nik, name, email, role, join_date, permanent_date
        FROM users WHERE id=?
    """, (user_id,)).fetchone()

    with st.form("edit_user"):
        nik = st.text_input("NIK", user[0])
        name = st.text_input("Name", user[1])
        email = st.text_input("Email", user[2])
        role = st.selectbox(
            "Role",
            ["employee", "manager", "hr"],
            index=["employee", "manager", "hr"].index(user[3])
        )
        join_date = st.date_input("Join Date", user[4])
        permanent_date = st.date_input(
            "Permanent Date",
            value=user[5]
        )

        submit = st.form_submit_button("Update User")

        if submit:
            conn.execute("""
                UPDATE users
                SET nik=?, name=?, email=?, role=?, join_date=?, permanent_date=?
                WHERE id=?
            """, (
                nik, name, email, role, join_date, permanent_date, user_id
            ))
            conn.commit()
            st.success("User berhasil diupdate")
            st.rerun()

# ======================================================
# RESET PASSWORD
# ======================================================
elif menu == "🔐 Reset Password":
    st.subheader("🔐 Reset Password")

    selected = st.selectbox("Pilih User", user_map.keys())
    user_id = user_map[selected]

    new_password = st.text_input("Password Baru", type="password")

    if st.button("Reset Password"):
        if not new_password:
            st.error("Password tidak boleh kosong")
        else:
            conn.execute("""
                UPDATE users SET password_hash=?
                WHERE id=?
            """, (hash_password(new_password), user_id))
            conn.commit()
            st.success("Password berhasil direset")

# ======================================================
# EDIT SALDO CUTI
# ======================================================
elif menu == "🧮 Edit Saldo Cuti":
    st.subheader("🧮 Edit Saldo Cuti")

    selected = st.selectbox("Pilih User", user_map.keys())
    user_id = user_map[selected]

    saldo = conn.execute("""
        SELECT last_year, current_year, change_off, sick_no_doc
        FROM leave_balance
        WHERE user_id=?
    """, (user_id,)).fetchone()

# 🔧 AUTO CREATE SALDO JIKA BELUM ADA
    if saldo is None:
        conn.execute("""
            INSERT INTO leave_balance (user_id, last_year, current_year, change_off, sick_no_doc)
            VALUES (?, 0, 0, 0, 0)
        """, (user_id,))
        conn.commit()

        saldo = (0, 0, 0, 0)



    with st.form("edit_saldo"):
        last_year = st.number_input("Saldo Last Year", value=int(saldo[0]), min_value=0)
        current_year = st.number_input("Saldo Current Year", value=int(saldo[1]), min_value=0)
        change_off = st.number_input("Saldo Change Off", value=float(saldo[2]), min_value=0.0)
        sick = st.number_input("Sakit Tanpa Surat Dokter", value=float(saldo[3]), min_value=0, max_value=6)

        submit = st.form_submit_button("Update Saldo")

        if submit:
            conn.execute("""
                UPDATE leave_balance
                SET last_year=?, current_year=?, change_off=?, sick_no_doc=?
                WHERE user_id=?
            """, (
                last_year, current_year, change_off, sick, user_id
            ))
            conn.commit()
            st.success("Saldo berhasil diupdate")

# ======================================================
# USER LIST
# ======================================================
elif menu == "📋 User List":
    st.subheader("📋 User List")

    st.dataframe(
        users_df[["id", "nik", "name", "email", "role"]],
        width="stretch"
    )

# ======================================================
# DELETE USER
# ======================================================
elif menu == "🗑️ Delete User":
    st.subheader("🗑️ Delete User")

    selected = st.selectbox("Pilih User", user_map.keys())
    user_id = user_map[selected]

    if user_id == st.session_state["user_id"]:
        st.warning("❌ Tidak bisa menghapus akun sendiri")
    else:
        confirm = st.checkbox("Saya yakin ingin menghapus user ini")

        if confirm and st.button("DELETE PERMANENTLY"):
            conn.execute("DELETE FROM leave_balance WHERE user_id=?", (user_id,))
            conn.execute("DELETE FROM users WHERE id=?", (user_id,))
            conn.commit()
            st.success("User berhasil dihapus")
            st.rerun()
