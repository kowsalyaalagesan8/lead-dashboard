import httpx
import os
from dotenv import load_dotenv

load_dotenv()

INSTAGRAM_TOKEN   = os.getenv("INSTAGRAM_ACCESS_TOKEN")
PAGE_ID           = os.getenv("INSTAGRAM_PAGE_ID")
VERIFY_TOKEN      = os.getenv("WHATSAPP_VERIFY_TOKEN", "mytoken123")  # same verify token
BASE_URL          = "https://graph.facebook.com/v18.0"


# ─── Send Instagram DM ────────────────────────────────────────────────────────

async def send_instagram_message(recipient_id: str, message: str) -> dict:
    """Send a DM reply to an Instagram user."""
    url = f"{BASE_URL}/me/messages"
    headers = {
        "Authorization": f"Bearer {INSTAGRAM_TOKEN}",
        "Content-Type": "application/json"
    }
    payload = {
        "recipient": {"id": recipient_id},
        "message":   {"text": message}
    }
    async with httpx.AsyncClient() as client:
        response = await client.post(url, headers=headers, json=payload, timeout=10)
        return response.json()


# ─── Parse Instagram Webhook ──────────────────────────────────────────────────

def parse_instagram_webhook(payload: dict) -> dict | None:
    """
    Extract sender ID, message text from Instagram webhook payload.
    Returns None if not a valid DM event.
    """
    try:
        entry      = payload["entry"][0]
        messaging  = entry["messaging"][0]

        sender_id  = messaging["sender"]["id"]
        recipient  = messaging["recipient"]["id"]

        # Ignore messages sent by the page itself
        if sender_id == PAGE_ID:
            return None

        msg = messaging.get("message", {})
        if not msg or msg.get("is_echo"):
            return None

        text = msg.get("text", "")
        if not text:
            # Handle story replies or other types
            attachments = msg.get("attachments", [])
            if attachments:
                text = f"[{attachments[0]['type']} attachment]"
            else:
                return None

        return {
            "sender_id":   sender_id,
            "sender_name": "Instagram User",
            "text":        text,
            "message_id":  msg.get("mid", "")
        }

    except (KeyError, IndexError):
        return None


# ─── Verify Webhook ───────────────────────────────────────────────────────────

def verify_instagram_webhook(mode: str, token: str, challenge: str) -> str | None:
    if mode == "subscribe" and token == VERIFY_TOKEN:
        return challenge
    return None


# ─── Get User Profile ─────────────────────────────────────────────────────────

async def get_instagram_profile(user_id: str) -> dict:
    """Get Instagram user's name and profile if available."""
    url = f"{BASE_URL}/{user_id}"
    params = {
        "fields":       "name,profile_pic",
        "access_token": INSTAGRAM_TOKEN
    }
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(url, params=params, timeout=10)
            data     = response.json()
            return {
                "name":        data.get("name", "Instagram User"),
                "profile_pic": data.get("profile_pic", "")
            }
        except Exception:
            return {"name": "Instagram User", "profile_pic": ""}
