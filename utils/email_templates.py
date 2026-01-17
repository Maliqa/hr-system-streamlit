def leave_request_email(emp_name, type, start, end, days):
    return f"""
    <html>
    <body>
        <h3>📩 Leave Request Pending Approval</h3>

        <p>
            <strong>{emp_name}</strong> has submitted a leave request:
        </p>

        <ul>
            <li><b>Type:</b> {type}</li>
            <li><b>Period:</b> {start} → {end}</li>
            <li><b>Total Days:</b> {days}</li>
        </ul>

        <p>Please login to the system to approve or reject.</p>

        <br>
        <small>HR System</small>
    </body>
    </html>
    """


def leave_status_email(name, typ, status, note=None):
    note_html = f"<p><b>Note:</b> {note}</p>" if note else ""
    return f"""
    <h3>Leave Request Update</h3>
    <p>Hi <b>{name}</b>,</p>
    <p>Your leave request ({typ}) has been <b>{status}</b>.</p>
    {note_html}
    <p>— HR System</p>
    """

def change_off_request_email(
    emp_name,
    work_type,
    period,
    co_days,
    day_type
):
    return f"""
    <html>
    <body style="font-family:Arial, sans-serif;">
        <h3>📦 Change Off Claim Pending Approval</h3>

        <p><strong>Employee:</strong> {emp_name}</p>
        <p><strong>Work Type:</strong> {work_type.upper()}</p>
        <p><strong>Period:</strong> {period}</p>
        <p><strong>Day Type:</strong> {day_type.upper()}</p>
        <p><strong>Change Off:</strong> {co_days} day(s)</p>

        <hr>
        <p style="font-size:12px;color:#6b7280;">
            This is an automated notification. Please review in HR System.
        </p>
    </body>
    </html>
    """

def approval_result_email(
    emp_name: str,
    request_type: str,
    status: str,
    note: str = None
):
    color = "#16a34a" if status == "APPROVED" else "#dc2626"

    note_html = ""
    if note:
        note_html = f"""
        <p><b>Reason:</b><br>
        {note}</p>
        """

    return f"""
    <html>
    <body style="font-family:Arial,sans-serif">
        <h3 style="color:{color};">
            {request_type} {status}
        </h3>

        <p>Hello <b>{emp_name}</b>,</p>

        <p>
            Your <b>{request_type}</b> request has been
            <b>{status.lower()}</b> by your manager.
        </p>

        {note_html}

        <br>
        <p style="font-size:12px;color:#6b7280">
            This is an automated notification. Please do not reply.
        </p>
    </body>
    </html>
    """
