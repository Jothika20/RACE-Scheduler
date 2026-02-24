import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import os

# Helper function to get SMTP and frontend config
def get_smtp_config():
    return {
        "sender_email": os.getenv("EMAIL_HOST_USER"),
        "sender_password": os.getenv("EMAIL_HOST_PASSWORD"),
        "smtp_host": os.getenv("EMAIL_HOST", "smtp.gmail.com"),
        "smtp_port": int(os.getenv("EMAIL_PORT", 465)),
        # FRONTEND_URL should match your allowed origins in CORS
        "frontend_url": os.getenv("FRONTEND_URL", "http://localhost:3000"),
    }

def send_invite_email(to_email: str, invite_token: str):
    config = get_smtp_config()
    invite_link = f"{config['frontend_url']}/register?token={invite_token}"

    message = MIMEMultipart("alternative")
    message["Subject"] = "You're invited!"
    message["From"] = config["sender_email"]
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
        with smtplib.SMTP_SSL(config["smtp_host"], config["smtp_port"]) as server:
            server.login(config["sender_email"], config["sender_password"])
            server.sendmail(config["sender_email"], to_email, message.as_string())
        print(f"Invite email sent to {to_email}")
    except Exception as e:
        print(f"Error sending invite email to {to_email}: {e}")


def send_event_cancel_email(to_emails: list[str], event_title: str, start_time, end_time, cancelled_by: str):
    config = get_smtp_config()
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
        message["From"] = config["sender_email"]
        message["To"] = to_email

        try:
            with smtplib.SMTP_SSL(config["smtp_host"], config["smtp_port"]) as server:
                server.login(config["sender_email"], config["sender_password"])
                server.sendmail(config["sender_email"], to_email, message.as_string())
            print(f"Event cancellation email sent to {to_email}")
        except Exception as e:
            print(f"Error sending event cancellation email to {to_email}: {e}")


def send_password_reset_email(to_email: str, reset_token: str):
    config = get_smtp_config()
    reset_link = f"{config['frontend_url']}/reset-password?token={reset_token}"

    message = MIMEMultipart("alternative")
    message["Subject"] = "Password Reset Request"
    message["From"] = config["sender_email"]
    message["To"] = to_email

    text = f"""You requested to reset your password. 
Click the link below to reset it:
{reset_link}

This link will expire in 1 hour.
If you didn't request this, please ignore this email."""

    html = f"""
    <html>
      <body>
        <p>You requested to reset your password.<br>
           Click the link below to reset it:<br>
           <a href="{reset_link}">Reset Password</a>
        </p>
        <p>This link will expire in 1 hour.</p>
        <p>If you didn't request this, please ignore this email.</p>
      </body>
    </html>
    """

    message.attach(MIMEText(text, "plain"))
    message.attach(MIMEText(html, "html"))

    try:
        with smtplib.SMTP_SSL(config["smtp_host"], config["smtp_port"]) as server:
            server.login(config["sender_email"], config["sender_password"])
            server.sendmail(config["sender_email"], to_email, message.as_string())
        print(f"Password reset email sent to {to_email}")
    except Exception as e:
        print(f"Error sending password reset email to {to_email}: {e}")