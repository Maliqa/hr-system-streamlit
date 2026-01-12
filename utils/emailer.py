from email.message import EmailMessage
import smtplib
import os
from dotenv import load_dotenv

load_dotenv()

SMTP_SERVER = os.getenv("SMTP_SERVER")
SMTP_PORT = int(os.getenv("SMTP_PORT", 587))
EMAIL_SENDER = os.getenv("EMAIL_SENDER")
EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD")
FROM_NAME = os.getenv("EMAIL_FROM_NAME", "HR System")


def send_email(
    to_email: str,
    subject: str,
    body: str,
    html: bool = False
):
    if not EMAIL_SENDER or not EMAIL_PASSWORD:
        raise RuntimeError("Email environment belum lengkap")

    msg = EmailMessage()
    msg["From"] = f"{FROM_NAME} <{EMAIL_SENDER}>"
    msg["To"] = to_email
    msg["Subject"] = subject

    if html:
        msg.set_content("Email ini membutuhkan HTML viewer.")
        msg.add_alternative(body, subtype="html")
    else:
        msg.set_content(body)

    with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
        server.starttls()
        server.login(EMAIL_SENDER, EMAIL_PASSWORD)
        server.send_message(msg)
