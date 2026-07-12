import requests
from typing import List, Dict, Any

class TelegramRouter:
    """Router to format and send job alerts to a Telegram chat/channel."""
    
    def __init__(self, bot_token: str, chat_id: str):
        self.bot_token = bot_token
        self.chat_id = chat_id

    def escape_markdown(self, text: str) -> str:
        """
        Escapes reserved characters for Telegram's MarkdownV2.
        For standard Markdown, escaping is simpler. Let's escape characters 
        to ensure standard Markdown doesn't fail.
        """
        if not text:
            return ""
        # For standard Markdown parse_mode='Markdown':
        # Escape characters that might trigger markdown formatting incorrectly
        reserved_chars = ['*', '_', '[', ']']
        for char in reserved_chars:
            text = text.replace(char, f"\\{char}")
        return text

    def format_jobs_message(self, jobs: List[Dict[str, Any]]) -> str:
        """Format a list of jobs into a scannable Markdown message."""
        if not jobs:
            return "No new jobs found matching the criteria in the last 24 hours."

        lines = ["*🔔 New Job Postings Found (Last 24 Hours) *\n"]
        for idx, job in enumerate(jobs, 1):
            company = self.escape_markdown(job.get("Company", "Unknown"))
            title = self.escape_markdown(job.get("Title", "Unknown"))
            location = self.escape_markdown(job.get("Location", "Unknown"))
            url = job.get("URL", "")

            # Formats: *Company Name* - Title (Location)
            # Link: [Apply Here](url)
            item_str = (
                f"{idx}. *{company}*\n"
                f"   • *Role*: {title}\n"
                f"   • *Location*: {location}\n"
                f"   • [Apply Here]({url})\n"
            )
            lines.append(item_str)
            
        return "\n".join(lines)

    def send_message(self, message: str) -> bool:
        """Send formatted message to Telegram API with character limit splitting."""
        if not self.bot_token or not self.chat_id:
            print("[Telegram Router] Missing bot token or chat ID. Skipping notification.")
            return False

        url = f"https://api.telegram.org/bot{self.bot_token}/sendMessage"
        
        # Telegram max length for sendMessage is 4096 characters.
        # Split message if it exceeds the limit.
        max_length = 4000
        message_chunks = [message[i:i + max_length] for i in range(0, len(message), max_length)]
        
        success = True
        for chunk in message_chunks:
            payload = {
                "chat_id": self.chat_id,
                "text": chunk,
                "parse_mode": "Markdown",
                "disable_web_page_preview": True
            }
            try:
                response = requests.post(url, json=payload, timeout=15)
                response.raise_for_status()
            except requests.RequestException as e:
                print(f"[Telegram Router] Failed to send message: {e}")
                # Try fallback as plain text if markdown formatting caused an error
                try:
                    payload["parse_mode"] = ""  # Plain text
                    response = requests.post(url, json=payload, timeout=15)
                    response.raise_for_status()
                except requests.RequestException as e_inner:
                    print(f"[Telegram Router] Fallback sending failed: {e_inner}")
                    success = False
        return success

    def send_document(self, file_path: str, caption: str = "") -> bool:
        """Send a local file as a document via Telegram API."""
        if not self.bot_token or not self.chat_id:
            print("[Telegram Router] Missing bot token or chat ID. Skipping document upload.")
            return False

        url = f"https://api.telegram.org/bot{self.bot_token}/sendDocument"
        try:
            with open(file_path, "rb") as f:
                files = {"document": f}
                data = {
                    "chat_id": self.chat_id,
                    "caption": caption[:1024]  # Telegram limits caption to 1024 chars
                }
                response = requests.post(url, data=data, files=files, timeout=30)
                response.raise_for_status()
                return True
        except Exception as e:
            print(f"[Telegram Router] Failed to send document: {e}")
            return False

