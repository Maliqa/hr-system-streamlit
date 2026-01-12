import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(__file__)))
from utils.emailer import send_email

send_email(
    "Maliqaaziz11@gmail.com",
    "Test HR System Email",
    "<b>Email berhasil!</b>"
)

print("OK")
