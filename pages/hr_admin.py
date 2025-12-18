import streamlit as st
import pandas as pd
from core.db import get_conn
from core.auth import require_role, hash_password, logout
from datetime import date
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

# =========================
# CREATE USER
# =========================
if menu == "➕ Create User":
    st.subheader("➕ Create User")

    with st.form("create_user"):
        nik = st.text_input("NIK")
        name = st.text_input("Name")
        email = st.text_input("Email")
        role = st.selectbox("Role", ["employee", "manager", "hr"])

        join_date = st.date_input(
            "Join Date",
            min_value=date(2000, 1, 1),
            max_value=date.today()
        )

        permanent_date = st.date_input(
            "Permanent Date (optional)",
            min_value=date(2000, 1, 1),
            max_value=date.today(),
            value=None
        )

        password = st.text_input("Password", type="password")

        submit = st.form_submit_button("Create User")

    # =========================
    # SUBMIT HANDLER (DI LUAR FORM)
    # =========================
    if submit:
        if not nik or not name or not email or not password:
            st.error("NIK, Name, Email, dan Password wajib diisi")
            st.stop()

        join_date_str = join_date.isoformat()
        permanent_date_str = (
            permanent_date.isoformat() if permanent_date else None
        )

        try:
            conn.execute("""
                INSERT INTO users (
                    nik, name, email, role,
                    join_date, permanent_date,
                    password_hash
                )
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                nik,
                name,
                email,
                role,
                join_date_str,
                permanent_date_str,
                hash_password(password)
            ))

            user_id = conn.execute(
                "SELECT last_insert_rowid()"
            ).fetchone()[0]

            conn.execute("""
                INSERT INTO leave_balance (
                    user_id, last_year, current_year,
                    change_off, sick_no_doc
                )
                VALUES (?, 0, 0, 0, 0)
            """, (user_id,))

            conn.commit()
            st.success("User berhasil dibuat")
            st.rerun()

        except Exception as e:
            st.error("Email atau NIK sudah digunakan")

# ======================================================
# EDIT USER
# ======================================================
elif menu == "✏️ Edit User":
    from datetime import date

    st.subheader("✏️ Edit User")

    # =========================
    # PILIH USER
    # =========================
    selected = st.selectbox("Pilih User", list(user_map.keys()))
    user_id = user_map[selected]

    user = conn.execute("""
        SELECT nik, name, email, role, join_date, permanent_date
        FROM users
        WHERE id=?
    """, (user_id,)).fetchone()

    if not user:
        st.error("User tidak ditemukan")
        st.stop()

    # =========================
    # NORMALISASI DATE (STRING -> date)
    # =========================
    join_date_val = (
        date.fromisoformat(user[4]) if user[4] else date.today()
    )

    permanent_date_val = (
        date.fromisoformat(user[5]) if user[5] else None
    )

    # =========================
    # FORM EDIT USER
    # =========================
    with st.form("edit_user"):
        nik = st.text_input("NIK", user[0])
        name = st.text_input("Name", user[1])
        email = st.text_input("Email", user[2])

        role = st.selectbox(
            "Role",
            ["employee", "manager", "hr"],
            index=["employee", "manager", "hr"].index(user[3])
        )

        join_date = st.date_input(
            "Join Date",
            value=join_date_val,
            min_value=date(2000, 1, 1),
            max_value=date.today()
        )

        permanent_date = st.date_input(
            "Permanent Date",
            value=permanent_date_val,
            min_value=date(2000, 1, 1),
            max_value=date.today()
        )

        submit = st.form_submit_button("Update User")

    # =========================
    # UPDATE USER (ISOFORMAT FIX)
    # =========================
    if submit:
        join_date_str = join_date.isoformat() if join_date else None
        permanent_date_str = (
            permanent_date.isoformat() if permanent_date else None
        )

        conn.execute("""
            UPDATE users
            SET nik=?,
                name=?,
                email=?,
                role=?,
                join_date=?,
                permanent_date=?
            WHERE id=?
        """, (
            nik,
            name,
            email,
            role,
            join_date_str,
            permanent_date_str,
            user_id
        ))

        conn.commit()
        st.success("✅ User berhasil diupdate")
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

    # auto-create saldo kalau belum ada
    if saldo is None:
        conn.execute("""
            INSERT INTO leave_balance 
            (user_id, last_year, current_year, change_off, sick_no_doc)
            VALUES (?, 0, 0, 0, 0)
        """, (user_id,))
        conn.commit()
        saldo = (0, 0, 0, 0)

    with st.form("edit_saldo_cuti"):
        last_year = st.number_input(
            "Saldo Last Year",
            value=int(saldo[0]),
            min_value=0,
            step=1
        )

        current_year = st.number_input(
            "Saldo Current Year",
            value=int(saldo[1]),
            min_value=0,
            step=1
        )

        change_off = st.number_input(
            "Change Off",
            value=float(saldo[2]),
            min_value=0.0,
            step=0.5
        )

        sick = st.number_input(
            "Sakit Tanpa Surat Dokter",
            value=int(saldo[3]),
            min_value=0,
            step=1
        )

        submit = st.form_submit_button("💾 Update Saldo Cuti")

    if submit:
        conn.execute("""
            UPDATE leave_balance
            SET last_year=?,
                current_year=?,
                change_off=?,
                sick_no_doc=?,
                updated_at=DATE('now')
            WHERE user_id=?
        """, (
            last_year,
            current_year,
            change_off,
            sick,
            user_id
        ))
        conn.commit()
        st.success("✅ Saldo cuti berhasil diperbarui")
        st.rerun()

# ======================================================
# USER LIST
# ======================================================
elif menu == "📋 User List":
    st.subheader("📋 User List + Leave Balance")

    rows = conn.execute("""
        SELECT 
            u.id,
            u.nik,
            u.name,
            u.email,
            u.role,
            COALESCE(lb.last_year, 0),
            COALESCE(lb.current_year, 0),
            COALESCE(lb.change_off, 0),
            COALESCE(lb.sick_no_doc, 0)
        FROM users u
        LEFT JOIN leave_balance lb ON lb.user_id = u.id
        ORDER BY u.id
    """).fetchall()

    if not rows:
        st.info("Belum ada user")
    else:
        table_data = []
        for r in rows:
            table_data.append({
                "ID": r[0],
                "NIK": r[1],
                "Name": r[2],
                "Email": r[3],
                "Role": r[4],
                "Last Year": r[5],
                "Current Year": r[6],
                "Change Off": r[7],
                "Sick (No Doc)": r[8],
            })

        st.dataframe(
            table_data,
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
