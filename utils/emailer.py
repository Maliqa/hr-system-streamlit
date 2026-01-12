import smtplib
from email.message import EmailMessage
import os
from dotenv import load_dotenv

load_dotenv()

SMTP_SERVER = os.getenv("SMTP_SERVER")
SMTP_PORT = int(os.getenv("SMTP_PORT", 587))
EMAIL_SENDER = os.getenv("EMAIL_SENDER")
EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD")


def send_email(to_email, subject, body, html=False):
    if not EMAIL_SENDER or not EMAIL_PASSWORD:
        raise RuntimeError("Email sender belum diset di environment")

    msg = EmailMessage()
    msg["From"] = f"HR System <{EMAIL_SENDER}>"
    msg["To"] = to_email
    msg["Subject"] = subject

    if html:
        msg.set_content("Your email client does not support HTML.")
        msg.add_alternative(body, subtype="html")
    else:
        msg.set_content(body)

    with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
        server.starttls()  # WAJIB
        server.login(EMAIL_SENDER, EMAIL_PASSWORD)
        server.send_message(msg)
