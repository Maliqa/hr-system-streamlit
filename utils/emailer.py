import smtplib
from email.message import EmailMessage
import os

SMTP_SERVER = "server.modulindo.com"
SMTP_PORT = 587

EMAIL_SENDER = os.getenv("it.technical@ptcai.com")
EMAIL_PASSWORD = os.getenv("e23bfdc61cb10f75b58130ad03c0c360")

def send_email(to_email, subject, body):
    if not EMAIL_SENDER or not EMAIL_PASSWORD:
        raise RuntimeError("Email sender belum diset di environment")

    msg = EmailMessage()
    msg["From"] = f"HR System <{EMAIL_SENDER}>"
    msg["To"] = to_email
    msg["Subject"] = subject
    msg.set_content(body)

    with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
        server.starttls()
        server.login(EMAIL_SENDER, EMAIL_PASSWORD)
        server.send_message(msg)
