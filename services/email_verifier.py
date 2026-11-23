import os
import re
import time
import email
from email.header import decode_header
from typing import Optional
import imaplib

def fetch_email_verification_code(
    email_user: Optional[str] = None,
    email_password: Optional[str] = None,
    imap_server: Optional[str] = None,
    max_wait_sec: int = 25,
    poll_interval: int = 4
) -> Optional[str]:
    """
    Connects to the candidate's email via IMAP to retrieve ATS 2FA/security verification codes
    (e.g., Greenhouse 8-digit security codes, Workable PINs).
    """
    user = email_user or os.getenv("IMAP_USER") or os.getenv("SMTP_USER")
    password = email_password or os.getenv("IMAP_PASSWORD") or os.getenv("SMTP_PASSWORD")
    server = imap_server or os.getenv("IMAP_SERVER")

    if not server:
        if user and ("gmail.com" in user.lower() or "googlemail.com" in user.lower()):
            server = "imap.gmail.com"
        else:
            server = "imap.gmail.com"

    if not user or not password:
        return None

    deadline = time.time() + max_wait_sec
    while time.time() < deadline:
        try:
            mail = imaplib.IMAP4_SSL(server)
            mail.login(user, password)
            mail.select("INBOX")

            # Search recent unread messages or greenhouse security emails
            status, messages = mail.search(None, '(OR (FROM "greenhouse") (SUBJECT "security code"))')
            if status != "OK" or not messages[0]:
                status, messages = mail.search(None, '(UNSEEN)')

            if status == "OK" and messages[0]:
                msg_ids = messages[0].split()
                for msg_id in reversed(msg_ids[-3:]):
                    res, msg_data = mail.fetch(msg_id, "(RFC822)")
                    for response_part in msg_data:
                        if isinstance(response_part, tuple):
                            msg = email.message_from_bytes(response_part[1])
                            body = ""
                            if msg.is_multipart():
                                for part in msg.walk():
                                    ctype = part.get_content_type()
                                    if ctype in ("text/plain", "text/html"):
                                        payload = part.get_payload(decode=True)
                                        if payload:
                                            body += payload.decode("utf-8", errors="ignore") + "\n"
                            else:
                                payload = msg.get_payload(decode=True)
                                if payload:
                                    body = payload.decode("utf-8", errors="ignore")

                            # Match Greenhouse / ATS patterns:
                            # e.g., "enter code 85592669 to resubmit", "security code: 85592669", "code: 123456"
                            code_match = re.search(r'\b(?:code|pin|security code|verification code)[:\s]+([A-Za-z0-9]{5,8})\b', body, re.IGNORECASE)
                            if not code_match:
                                code_match = re.search(r'\b([0-9]{6,8})\b', body)

                            if code_match:
                                code = code_match.group(1).strip()
                                mail.logout()
                                return code

            mail.logout()
        except Exception:
            pass

        time.sleep(poll_interval)

    return None
