import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import os

def send_invite_email(to_email: str, invite_token: str):
    sender_email = os.getenv("EMAIL_HOST_USER")
    sender_password = os.getenv("EMAIL_HOST_PASSWORD")
    smtp_host = os.getenv("EMAIL_HOST", "smtp.gmail.com")
    smtp_port = int(os.getenv("EMAIL_PORT", "465"))

    invite_link = f"http://localhost:3000/register?token={invite_token}"

    message = MIMEMultipart("alternative")
    message["Subject"] = "You're invited!"
    message["From"] = sender_email
    message["To"] = to_email

    text = f"You've been invited to join the calendar app!\nRegister here: {invite_link}"
    html = f"""
    <html>
      <body>
        <p>You've been invited to join the calendar app!<br>
           Click the link below to register:<br>
           <a href="{invite_link}">Accept Invitation</a>
        </p>
      </body>
    </html>
    """

    message.attach(MIMEText(text, "plain"))
    message.attach(MIMEText(html, "html"))

    try:
        with smtplib.SMTP_SSL(smtp_host, smtp_port) as server:
            server.login(sender_email, sender_password)
            server.sendmail(sender_email, to_email, message.as_string())
        print(f"Invite email sent to {to_email}")
    except Exception as e:
        print(f"Error sending invite email to {to_email}: {e}")

def send_event_cancel_email(
    to_emails: list[str],
    event_title: str,
    start_time,
    end_time,
    cancelled_by: str,
):
    sender_email = os.getenv("EMAIL_HOST_USER")
    sender_password = os.getenv("EMAIL_HOST_PASSWORD")
    smtp_host = os.getenv("EMAIL_HOST", "smtp.gmail.com")
    smtp_port = int(os.getenv("EMAIL_PORT", "465"))

    subject = f"Event Cancelled: {event_title}"

    body = f"""
    The following event has been cancelled:

    Title: {event_title}
    Time: {start_time} - {end_time}
    Cancelled by: {cancelled_by}
    """

    for to_email in to_emails:
        message = MIMEText(body)
        message["Subject"] = subject
        message["From"] = sender_email
        message["To"] = to_email

        with smtplib.SMTP_SSL(smtp_host, smtp_port) as server:
            server.login(sender_email, sender_password)
            server.sendmail(sender_email, to_email, message.as_string())

