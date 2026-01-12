
def leave_request_email(emp, manager, typ, start, end, days):
    return f"""
    <h3>📩 Leave Request Pending Approval</h3>
    <p>Dear {manager},</p>

    <p><b>{emp}</b> has submitted a leave request:</p>

    <ul>
        <li><b>Type:</b> {typ}</li>
        <li><b>Period:</b> {start} → {end}</li>
        <li><b>Total Days:</b> {days}</li>
    </ul>

    <p>Please login to the system to approve or reject.</p>
    <br>
    <p>HR System</p>
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


