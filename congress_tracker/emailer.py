"""
Optional email delivery of the daily digest.
Set SEND_EMAIL=true and configure SMTP_* env vars to enable.
"""
import logging
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


def send_digest(
    md_path: str,
    to_addr: str,
    smtp_host: str,
    smtp_port: int,
    smtp_user: str,
    smtp_password: str,
    from_addr: Optional[str] = None,
):
    from_addr = from_addr or smtp_user
    subject_date = Path(md_path).stem.replace("digest_", "")
    subject = f"Congress Trading Digest — {subject_date}"

    md_text = Path(md_path).read_text(encoding="utf-8")

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = from_addr
    msg["To"] = to_addr

    msg.attach(MIMEText(md_text, "plain"))

    # Convert markdown to very basic HTML
    try:
        import re
        html = md_text
        html = re.sub(r"^## (.+)$", r"<h2>\1</h2>", html, flags=re.MULTILINE)
        html = re.sub(r"^### (.+)$", r"<h3>\1</h3>", html, flags=re.MULTILINE)
        html = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", html)
        html = re.sub(r"\n", "<br>\n", html)
        html = f"<html><body style='font-family:monospace'>{html}</body></html>"
        msg.attach(MIMEText(html, "html"))
    except Exception:
        pass

    try:
        with smtplib.SMTP(smtp_host, smtp_port) as server:
            server.ehlo()
            server.starttls()
            server.login(smtp_user, smtp_password)
            server.sendmail(from_addr, [to_addr], msg.as_string())
        logger.info("Digest email sent to %s", to_addr)
    except Exception as exc:
        logger.error("Email send failed: %s", exc)
