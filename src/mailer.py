import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart


def parse_recipients(value: str | list[str]) -> list[str]:
    """将单个邮箱、逗号分隔字符串或列表统一解析为收件人列表。"""
    if isinstance(value, list):
        return [addr.strip() for addr in value if addr and str(addr).strip()]
    return [addr.strip() for addr in str(value).split(",") if addr.strip()]


def send_email(html_content: str, subject: str, email_config: dict) -> bool:
    recipients = parse_recipients(
        email_config.get("recipients") or email_config["recipient"]
    )

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = email_config["smtp_user"]
    msg["To"] = ", ".join(recipients)

    msg.attach(MIMEText(html_content, "html", "utf-8"))

    host = email_config["smtp_host"]
    port = email_config["smtp_port"]
    timeout = email_config.get("smtp_timeout", 30)

    use_ssl = email_config.get("smtp_use_ssl", port == 465)
    if use_ssl:
        with smtplib.SMTP_SSL(host, port, timeout=timeout) as server:
            server.login(email_config["smtp_user"], email_config["smtp_pass"])
            server.sendmail(
                email_config["smtp_user"],
                recipients,
                msg.as_string()
            )
    else:
        with smtplib.SMTP(host, port, timeout=timeout) as server:
            server.starttls()
            server.login(email_config["smtp_user"], email_config["smtp_pass"])
            server.sendmail(
                email_config["smtp_user"],
                recipients,
                msg.as_string()
            )

    return True
