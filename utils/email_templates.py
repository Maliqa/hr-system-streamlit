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


