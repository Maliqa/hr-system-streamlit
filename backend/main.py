from fastapi import FastAPI, Depends, Response, Cookie
import sqlite3
from backend.auth import create_token, verify_token
from passlib.hash import bcrypt

app = FastAPI()

DB = "data/hr.db"

def get_user(email):
    conn = sqlite3.connect(DB)
    c = conn.cursor()
    c.execute("SELECT id, role, password_hash FROM users WHERE email=?", (email,))
    row = c.fetchone()
    conn.close()
    return row

@app.post("/login")
def login(email: str, password: str, response: Response):
    user = get_user(email)
    if not user:
        return {"error": "invalid"}

    user_id, role, password_hash = user
    if not bcrypt.verify(password, password_hash):
        return {"error": "invalid"}

    token = create_token({"user_id": user_id, "role": role})
    response.set_cookie(
        key="access_token",
        value=token,
        httponly=True,
        samesite="lax"
    )
    return {"status": "ok", "role": role}

@app.get("/me")
def me(access_token: str | None = Cookie(default=None)):
    if not access_token:
        return None
    return verify_token(access_token)

@app.post("/logout")
def logout(response: Response):
    response.delete_cookie("access_token")
    return {"status": "logged_out"}
