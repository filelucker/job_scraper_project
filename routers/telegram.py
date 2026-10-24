import os
import re
import requests
from typing import List, Dict, Any, Optional

class TelegramRouter:
    """Router to format and send job alerts and application updates to Telegram."""

    def __init__(self, bot_token: str, chat_id: str):
        self.bot_token = bot_token
        self.chat_id = chat_id

    @staticmethod
    def escape_markdown(text: str) -> str:
        """
        Escapes reserved characters for Telegram standard Markdown:
        asterisk (*), underscore (_), brackets ([ ]), and backticks (`).
        """
        if not text:
            return ""
        text = str(text)
        for char in ['*', '_', '[', ']', '`']:
            text = text.replace(char, f"\\{char}")
        return text

    def format_jobs_message(self, jobs: List[Dict[str, Any]]) -> str:
        """
        Format a list of jobs using the clean scannable layout
        with an explicit 'Applied or Not' indicator.
        """
        if not jobs:
            return "No new jobs found matching the criteria in the last 24 hours."

        lines = ["*🔔 New Job Postings Found (Last 24 Hours) *\n"]
        for idx, job in enumerate(jobs, 1):
            company = self.escape_markdown(job.get("Company", "Unknown"))
            title = self.escape_markdown(job.get("Title", "Unknown"))
            location = self.escape_markdown(job.get("Location", "Unknown"))
            url = job.get("URL", "")

            # Applied or Not indicator
            status = job.get("Status") or job.get("status")
            if status:
                status_str = str(status)
                status_lower = status_str.lower()
                if "applied" in status_lower:
                    clean_status = re.sub(r'^(applied\s*[\(\-:]?\s*|\s*)', '', status_str, flags=re.IGNORECASE).strip(' ()')
                    suffix = f" ({self.escape_markdown(clean_status)})" if clean_status else ""
                    applied_str = f"✅ Applied{suffix}"
                elif "draft" in status_lower or "review" in status_lower:
                    clean_status = re.sub(r'^(drafted\s*[\(\-:]?\s*|\s*)', '', status_str, flags=re.IGNORECASE).strip(' ()')
                    suffix = f" ({self.escape_markdown(clean_status)})" if clean_status else ""
                    applied_str = f"📝 Drafted{suffix}"
                else:
                    applied_str = f"⏳ {self.escape_markdown(status_str)}"
            else:
                applied_str = "❌ Not Applied"

            item_str = (
                f"{idx}. *{company}*\n"
                f"   • *Role*: {title}\n"
                f"   • *Location*: {location}\n"
                f"   • *Applied*: {applied_str}\n"
                f"   • [Apply Here]({url})\n"
            )
            lines.append(item_str)

        return "\n".join(lines)

    def format_auto_apply_update(self, job: Dict[str, Any], result: Dict[str, Any]) -> str:
        """
        Concise individual auto-apply update with Applied/Not indicator.
        """
        company = self.escape_markdown(job.get("Company", "Company"))
        title = self.escape_markdown(job.get("Title", "Job"))
        url = job.get("URL", "")
        channel = result.get("channel", "UNKNOWN")
        status_text = result.get("status", "Processed")

        is_applied = "applied" in str(status_text).lower()
        icon = "🚀" if is_applied else "📝"
        applied_str = "✅ Applied" if is_applied else "❌ Not Applied"

        return (
            f"{icon} *Auto-Apply Update:*\n"
            f"• *Company*: {company}\n"
            f"• *Role*: {title}\n"
            f"• *Applied*: {applied_str}\n"
            f"• *Channel*: `{channel}`\n"
            f"• *Status*: *{status_text}*\n"
            f"• *URL*: {url}"
        )

    def format_run_summary(
        self,
        duration_seconds: float,
        total_configured: int,
        scanned_count: int,
        skipped_count: int,
        failed_boards: List[tuple],
        total_found: int,
        total_new: int
    ) -> str:
        """Format execution run summary for Telegram."""
        if duration_seconds < 60:
            duration_str = f"{int(duration_seconds)}s"
        else:
            minutes = int(duration_seconds // 60)
            seconds = int(duration_seconds % 60)
            duration_str = f"{minutes}m {seconds}s"

        lines = [
            "📋 *Job Scraper Run Summary*",
            f"⏱️ *Duration*: {duration_str}",
            f"🔍 *Total Boards*: {total_configured}",
            f"   • *Scanned*: {scanned_count}",
            f"   • *Skipped*: {skipped_count}",
            f"   • *Failed*: {len(failed_boards)}",
            f"💼 *Jobs Matched*: {total_found}",
            f"🆕 *New Jobs Added*: {total_new}"
        ]

        if failed_boards:
            lines.append("\n❌ *Failed Boards:*")
            for company_name, err in failed_boards:
                esc_company = self.escape_markdown(company_name)
                err_str = str(err)
                if len(err_str) > 60:
                    err_str = err_str[:57] + "..."
                esc_err = self.escape_markdown(err_str)
                lines.append(f"• *{esc_company}*: {esc_err}")

        return "\n".join(lines)

    def send_message(self, message: str) -> bool:
        """Send formatted message to Telegram API with line-boundary splitting."""
        if not self.bot_token or not self.chat_id:
            print("[Telegram Router] Missing bot token or chat ID. Skipping notification.")
            return False

        url = f"https://api.telegram.org/bot{self.bot_token}/sendMessage"
        max_length = 3800
        message_chunks = []

        if len(message) <= max_length:
            message_chunks.append(message)
        else:
            current_chunk = []
            current_length = 0
            for line in message.split("\n"):
                line_len = len(line) + 1
                if current_length + line_len > max_length and current_chunk:
                    message_chunks.append("\n".join(current_chunk))
                    current_chunk = [line]
                    current_length = line_len
                else:
                    current_chunk.append(line)
                    current_length += line_len
            if current_chunk:
                message_chunks.append("\n".join(current_chunk))

        success = True
        for chunk in message_chunks:
            payload = {
                "chat_id": self.chat_id,
                "text": chunk,
                "parse_mode": "Markdown",
                "disable_web_page_preview": True
            }
            try:
                response = requests.post(url, json=payload, timeout=20)
                response.raise_for_status()
            except requests.RequestException:
                # Fallback to plain text if markdown formatting encountered an unescaped symbol
                try:
                    payload_plain = {
                        "chat_id": self.chat_id,
                        "text": chunk,
                        "disable_web_page_preview": True
                    }
                    response = requests.post(url, json=payload_plain, timeout=20)
                    response.raise_for_status()
                except requests.RequestException as e_inner:
                    print(f"[Telegram Router] Sending failed: {e_inner}")
                    success = False
        return success

    def send_document(self, document_path: str, caption: str = "") -> bool:
        """Send a local document (e.g. PDF resume or screenshot) to Telegram chat."""
        if not self.bot_token or not self.chat_id:
            return False

        if not os.path.exists(document_path):
            print(f"[Telegram Router] Document not found at {document_path}")
            return False

        url = f"https://api.telegram.org/bot{self.bot_token}/sendDocument"
        try:
            with open(document_path, "rb") as f:
                files = {"document": f}
                data = {
                    "chat_id": self.chat_id,
                    "caption": caption[:1024]
                }
                resp = requests.post(url, data=data, files=files, timeout=45)
                if resp.status_code == 200:
                    return True
                else:
                    print(f"[Telegram Router] Failed to send document: {resp.text}")
                    return False
        except Exception as e:
            print(f"[Telegram Router] Error sending document: {e}")
            return False
