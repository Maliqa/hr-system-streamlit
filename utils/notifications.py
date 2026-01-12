# utils/notifications.py
from utils.emailer import send_email


def notify_leave_event(
    *,
    to_email: str,
    emp_name: str,
    event: str,
    leave_type: str,
    start_date: str,
    end_date: str,
    note: str | None = None
):
    subject_map = {
        "submitted": "📩 Leave Request Submitted",
        "manager_approved": "✅ Leave Approved by Manager",
        "manager_rejected": "❌ Leave Rejected by Manager",
        "hr_approved": "🎉 Leave Approved by HR",
        "hr_rejected": "❌ Leave Rejected by HR",
    }

    subject = subject_map.get(event, "Leave Notification")

    body = f"""
Halo {emp_name},

Status pengajuan cuti Anda:

• Tipe   : {leave_type}
• Periode: {start_date} s/d {end_date}
• Status : {event.replace('_', ' ').title()}

"""

    if note:
        body += f"Catatan:\n{note}\n\n"

    body += "Email ini dikirim otomatis oleh HR System.\nMohon tidak membalas."

    send_email(
        to_email=to_email,
        subject=subject,
        body=body
    )




def leave_request_email(emp_name, manager_name, leave_type, start, end, days):
    return f"""
    <html>
    <body style="font-family: Inter, Segoe UI, Arial, sans-serif; background:#f9fafb; padding:24px;">
        <div style="max-width:600px; margin:auto; background:#ffffff; border-radius:8px; border:1px solid #e5e7eb;">

            <div style="padding:20px; border-bottom:1px solid #e5e7eb;">
                <h2 style="margin:0; color:#111827;">📩 Leave Request Pending Approval</h2>
            </div>

            <div style="padding:20px; color:#111827;">
                <p>Dear <b>{manager_name}</b>,</p>

                <p>
                    <b>{emp_name}</b> has submitted a leave request with the following details:
                </p>

                <table style="width:100%; border-collapse:collapse; margin-top:12px;">
                    <tr>
                        <td style="padding:8px; background:#f3f4f6;">Type</td>
                        <td style="padding:8px;">{leave_type}</td>
                    </tr>
                    <tr>
                        <td style="padding:8px; background:#f3f4f6;">Period</td>
                        <td style="padding:8px;">{start} → {end}</td>
                    </tr>
                    <tr>
                        <td style="padding:8px; background:#f3f4f6;">Total Days</td>
                        <td style="padding:8px;"><b>{days}</b></td>
                    </tr>
                </table>

                <p style="margin-top:16px;">
                    Please login to the HR System to approve or reject this request.
                </p>

                <p style="margin-top:24px;">
                    Regards,<br>
                    <b>HR System</b>
                </p>
            </div>

            <div style="padding:12px; background:#f9fafb; color:#6b7280; font-size:12px; text-align:center;">
                This is an automated notification. Please do not reply.
            </div>

        </div>
    </body>
    </html>
    """
