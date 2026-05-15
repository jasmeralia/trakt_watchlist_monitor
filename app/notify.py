import smtplib
from email.message import EmailMessage

from config import settings


def send_alert(title: str, body: str) -> None:
    message = EmailMessage()
    message["From"] = settings.smtp_from
    message["To"] = settings.smtp_to
    message["Subject"] = title
    message.set_content(body)

    with smtplib.SMTP(settings.smtp_host, settings.smtp_port) as smtp:
        smtp.starttls()
        smtp.login(settings.smtp_username, settings.smtp_password)
        smtp.sendmail(settings.smtp_from, settings.smtp_to, message.as_string())
