import os
from dotenv import load_dotenv

load_dotenv()

import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from services.apply_dispatcher import AutoApplyDispatcher
from routers.telegram import TelegramRouter

def main():
    dispatcher = AutoApplyDispatcher(
        mode="review",
        gemini_api_key=os.getenv("GEMINI_API_KEY")
    )

    test_job = {
        "Company": "Monzo",
        "Title": "Senior Mobile Engineer (Android/iOS)",
        "Location": "Remote / London, UK",
        "URL": "https://job-boards.greenhouse.io/monzo/jobs/6635595",
        "description": "We are looking for a Senior Mobile Engineer with experience in Kotlin, Jetpack Compose, Swift, and building secure FinTech applications.",
        "tags": ["Mobile", "Fintech", "Kotlin", "Swift"]
    }

    print(f"=== Starting Test Run for {test_job['Company']} - {test_job['Title']} ===")
    result = dispatcher.process_job(test_job)

    print("\nResult Summary:")
    print("  Channel:", result.get("channel"))
    print("  Success:", result.get("success"))
    print("  Status:", result.get("status"))
    print("  PDF Path:", result.get("pdf_path"))

    token = os.getenv("TELEGRAM_BOT_TOKEN")
    chat_id = os.getenv("TELEGRAM_CHAT_ID")
    if token and chat_id:
        tg = TelegramRouter(token, chat_id)
        status_text = result.get("status", "Processed")
        pdf_path = result.get("pdf_path")
        msg = (
            f"🧪 *Auto-Apply Test Run Complete:*\n\n"
            f"• *Company*: {test_job['Company']}\n"
            f"• *Role*: {test_job['Title']}\n"
            f"• *Channel*: `{result.get('channel')}`\n"
            f"• *Status*: *{status_text}*\n"
            f"• *Target URL*: {test_job['URL']}\n\n"
            f"Tailored PDF resume generated and attached below for your review!"
        )
        tg.send_message(msg)
        if pdf_path and os.path.exists(pdf_path):
            tg.send_document(pdf_path, caption=f"Tailored CV - {test_job['Company']}")
            print("Tailored PDF resume dispatched to Telegram!")

if __name__ == "__main__":
    main()
