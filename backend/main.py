from fastapi import FastAPI, Depends, Response, Cookie, Request
import sqlite3
from backend.auth import create_token, verify_token
from passlib.hash import bcrypt

app = FastAPI()

DB = "data/hr.db"

# ======================================================
# DB HELPERS
# ======================================================
def get_conn():
    return sqlite3.connect(DB)

def get_user(email):
    conn = get_conn()
    c = conn.cursor()
    c.execute(
        "SELECT id, email, role, password_hash FROM users WHERE email=?",
        (email,)
    )
    row = c.fetchone()
    conn.close()
    return row

def log_auth_action(
    user_id=None,
    email=None,
    role=None,
    action="login",
    request: Request | None = None
):
    conn = get_conn()
    c = conn.cursor()
    c.execute("""
        INSERT INTO auth_logs
        (user_id, email, role, action, ip_address, user_agent)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (
        user_id,
        email,
        role,
        action,
        request.client.host if request and request.client else None,
        request.headers.get("user-agent") if request else None
    ))
    conn.commit()
    conn.close()

# ======================================================
# AUTH ENDPOINTS
# ======================================================
@app.post("/login")
def login(email: str, password: str, response: Response, request: Request):
    user = get_user(email)

    # ❌ USER TIDAK ADA
    if not user:
        log_auth_action(
            email=email,
            action="failed_login",
            request=request
        )
        return {"error": "invalid"}

    user_id, user_email, role, password_hash = user

    # ❌ PASSWORD SALAH
    if not bcrypt.verify(password, password_hash):
        log_auth_action(
            user_id=user_id,
            email=user_email,
            role=role,
            action="failed_login",
            request=request
        )
        return {"error": "invalid"}

    # ✅ LOGIN BERHASIL
    token = create_token({"user_id": user_id, "role": role})
    response.set_cookie(
        key="access_token",
        value=token,
        httponly=True,
        samesite="lax"
    )

    log_auth_action(
        user_id=user_id,
        email=user_email,
        role=role,
        action="login",
        request=request
    )

    return {"status": "ok", "role": role}

@app.get("/me")
def me(access_token: str | None = Cookie(default=None)):
    if not access_token:
        return None
    return verify_token(access_token)

@app.post("/logout")
def logout(
    response: Response,
    request: Request,
    access_token: str | None = Cookie(default=None)
):
    user = verify_token(access_token) if access_token else None

    if isinstance(user, dict):
        log_auth_action(
            user_id=user.get("user_id"),
            email=user.get("email"),
            role=user.get("role"),
            action="logout",
            request=request
        )

    response.delete_cookie("access_token")
    return {"status": "logged_out"}
