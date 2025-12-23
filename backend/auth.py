from datetime import datetime, timedelta
from jose import jwt, JWTError
from passlib.hash import bcrypt

SECRET_KEY = "SUPER_SECRET_KEY_GANTI"
ALGORITHM = "HS256"
EXPIRE_MINUTES = 60 * 8  # 8 jam

def create_token(data: dict):
    payload = data.copy()
    payload["exp"] = datetime.utcnow() + timedelta(minutes=EXPIRE_MINUTES)
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)

def verify_token(token: str):
    try:
        return jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
    except JWTError:
        return None
