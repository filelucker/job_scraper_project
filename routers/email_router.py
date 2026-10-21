import os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.application import MIMEApplication
from typing import Optional, Dict, Any

class EmailRouter:
    """Dispatches customized job application emails with PDF CV attachments via SMTP."""

    def __init__(
        self,
        smtp_host: Optional[str] = None,
        smtp_port: Optional[int] = None,
        smtp_user: Optional[str] = None,
        smtp_password: Optional[str] = None,
        sender_name: Optional[str] = None,
        dry_run: bool = False
    ):
        self.smtp_host = smtp_host or os.getenv("SMTP_HOST", "smtp.gmail.com")
        self.smtp_port = int(smtp_port or os.getenv("SMTP_PORT", "587"))
        self.smtp_user = smtp_user or os.getenv("SMTP_USER", "")
        self.smtp_password = smtp_password or os.getenv("SMTP_PASSWORD", "")
        self.sender_name = sender_name or os.getenv("SENDER_NAME", "Md Moniruzzaman")
        
        env_dry = os.getenv("DRY_RUN", "").lower() in ("true", "1", "yes")
        self.dry_run = dry_run or env_dry

    def send_application(
        self,
        recipient_email: str,
        subject: str,
        body_text: str,
        body_html: str,
        pdf_path: str,
        attachment_filename: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Sends an email with tailored body and attached resume PDF.
        Returns a dict: {"success": bool, "message": str, "dry_run": bool}
        """
        if not recipient_email:
            return {"success": False, "message": "Recipient email is empty.", "dry_run": self.dry_run}

        if not os.path.exists(pdf_path):
            return {"success": False, "message": f"Attachment PDF not found at {pdf_path}", "dry_run": self.dry_run}

        filename = attachment_filename or os.path.basename(pdf_path)

        # Compose MIME Message
        msg = MIMEMultipart("mixed")
        msg["From"] = f"{self.sender_name} <{self.smtp_user}>" if self.smtp_user else self.sender_name
        msg["To"] = recipient_email
        msg["Subject"] = subject

        # Alternative container for text and html body
        alt_part = MIMEMultipart("alternative")
        alt_part.attach(MIMEText(body_text, "plain", "utf-8"))
        alt_part.attach(MIMEText(body_html, "html", "utf-8"))
        msg.attach(alt_part)

        # Attach PDF
        try:
            with open(pdf_path, "rb") as f:
                pdf_attachment = MIMEApplication(f.read(), _subtype="pdf")
                pdf_attachment.add_header(
                    "Content-Disposition",
                    "attachment",
                    filename=filename
                )
                msg.attach(pdf_attachment)
        except Exception as e:
            return {"success": False, "message": f"Failed reading PDF attachment: {e}", "dry_run": self.dry_run}

        if self.dry_run:
            print(f"[EmailRouter][DRY RUN] Simulated sending to '{recipient_email}' | Subject: '{subject}' | Attachment: '{filename}'")
            return {
                "success": True,
                "message": f"[DRY RUN] Email simulated successfully to {recipient_email}",
                "dry_run": True
            }

        if not self.smtp_user or not self.smtp_password:
            return {
                "success": False,
                "message": "SMTP_USER or SMTP_PASSWORD is not configured in .env.",
                "dry_run": False
            }

        # Dispatch via SMTP
        try:
            if self.smtp_port == 465:
                server = smtplib.SMTP_SSL(self.smtp_host, self.smtp_port, timeout=30)
            else:
                server = smtplib.SMTP(self.smtp_host, self.smtp_port, timeout=30)
                server.starttls()

            server.login(self.smtp_user, self.smtp_password)
            server.send_message(msg)
            server.quit()

            print(f"[EmailRouter] Successfully sent application to {recipient_email}")
            return {
                "success": True,
                "message": f"Sent email to {recipient_email}",
                "dry_run": False
            }
        except Exception as e:
            err = f"Failed to send email to {recipient_email}: {e}"
            print(f"[EmailRouter][ERROR] {err}")
            return {
                "success": False,
                "message": err,
                "dry_run": False
            }
