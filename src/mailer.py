import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart


def send_email(html_content: str, subject: str, email_config: dict) -> bool:
    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = email_config["smtp_user"]
    msg["To"] = email_config["recipient"]

    msg.attach(MIMEText(html_content, "html", "utf-8"))

    with smtplib.SMTP(email_config["smtp_host"], email_config["smtp_port"]) as server:
        server.starttls()
        server.login(email_config["smtp_user"], email_config["smtp_pass"])
        server.sendmail(
            email_config["smtp_user"],
            email_config["recipient"],
            msg.as_string()
        )

    return True
