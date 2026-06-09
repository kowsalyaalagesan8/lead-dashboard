import httpx
import os
from dotenv import load_dotenv

load_dotenv()

PAGE_TOKEN = os.getenv("FACEBOOK_PAGE_TOKEN")
PAGE_ID = os.getenv("FACEBOOK_PAGE_ID")
VERIFY_TOKEN = os.getenv("WHATSAPP_VERIFY_TOKEN", "Agnel")


async def send_facebook_message(recipient_id: str, message: str) -> dict:
    url = f"https://graph.facebook.com/v18.0/{PAGE_ID}/messages"
    payload = {
        "recipient": {"id": recipient_id},
        "message": {"text": message},
        "messaging_type": "RESPONSE",
        "access_token": PAGE_TOKEN
    }
    async with httpx.AsyncClient() as client:
        response = await client.post(url, json=payload, timeout=10)
        print("Facebook Send Response:", response.json())
        return response.json()


def parse_facebook_webhook(payload: dict) -> dict | None:
    try:
        entry = payload["entry"][0]
        messaging = entry["messaging"][0]

        sender_id = messaging["sender"]["id"]

        # Ignore page's own messages
        if sender_id == PAGE_ID:
            return None

        msg = messaging.get("message", {})

        if not msg or msg.get("is_echo"):
            return None

        text = msg.get("text", "")
        if not text:
            return None

        return {
            "sender_id": sender_id,
            "sender_name": "Facebook User",
            "text": text,
            "message_id": msg.get("mid", "")
        }

    except Exception as e:
        print("Facebook Webhook Parse Error:", e)
        return None


def verify_facebook_webhook(mode: str, token: str, challenge: str):
    if mode == "subscribe" and token == VERIFY_TOKEN:
        return challenge
    return None
