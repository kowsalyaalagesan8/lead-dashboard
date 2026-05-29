import httpx
import os
from dotenv import load_dotenv

load_dotenv()

WHATSAPP_TOKEN        = os.getenv("WHATSAPP_TOKEN")
PHONE_NUMBER_ID       = os.getenv("WHATSAPP_PHONE_NUMBER_ID")
VERIFY_TOKEN          = os.getenv("WHATSAPP_VERIFY_TOKEN", "my_verify_token")
BASE_URL              = f"https://graph.facebook.com/v18.0/{PHONE_NUMBER_ID}"


# ─── Send Text Message ────────────────────────────────────────────────────────

async def send_whatsapp_message(to: str, message: str) -> dict:
    """Send a text message via WhatsApp Cloud API."""
    url = f"{BASE_URL}/messages"
    headers = {
        "Authorization": f"Bearer {WHATSAPP_TOKEN}",
        "Content-Type": "application/json"
    }
    payload = {
        "messaging_product": "whatsapp",
        "recipient_type": "individual",
        "to": to,
        "type": "text",
        "text": {"preview_url": False, "body": message}
    }
    async with httpx.AsyncClient() as client:
        response = await client.post(url, headers=headers, json=payload, timeout=10)
        return response.json()


# ─── Send Template Message ────────────────────────────────────────────────────

async def send_template_message(to: str, template_name: str, language: str = "en_US") -> dict:
    """Send a pre-approved WhatsApp template message."""
    url = f"{BASE_URL}/messages"
    headers = {
        "Authorization": f"Bearer {WHATSAPP_TOKEN}",
        "Content-Type": "application/json"
    }
    payload = {
        "messaging_product": "whatsapp",
        "to": to,
        "type": "template",
        "template": {
            "name": template_name,
            "language": {"code": language}
        }
    }
    async with httpx.AsyncClient() as client:
        response = await client.post(url, headers=headers, json=payload, timeout=10)
        return response.json()


# ─── Send Button Message ──────────────────────────────────────────────────────

async def send_button_message(to: str, body: str, buttons: list) -> dict:
    """Send interactive buttons via WhatsApp."""
    url = f"{BASE_URL}/messages"
    headers = {
        "Authorization": f"Bearer {WHATSAPP_TOKEN}",
        "Content-Type": "application/json"
    }
    btn_list = [
        {"type": "reply", "reply": {"id": str(i), "title": btn}}
        for i, btn in enumerate(buttons)
    ]
    payload = {
        "messaging_product": "whatsapp",
        "to": to,
        "type": "interactive",
        "interactive": {
            "type": "button",
            "body": {"text": body},
            "action": {"buttons": btn_list}
        }
    }
    async with httpx.AsyncClient() as client:
        response = await client.post(url, headers=headers, json=payload, timeout=10)
        return response.json()


# ─── Parse Incoming Webhook ───────────────────────────────────────────────────

def parse_whatsapp_webhook(payload: dict) -> dict | None:
    """
    Extract sender phone, message text, and message ID from webhook payload.
    Returns None if not a valid message event.
    """
    try:
        entry   = payload["entry"][0]
        changes = entry["changes"][0]
        value   = changes["value"]

        if "messages" not in value:
            return None

        msg     = value["messages"][0]
        contact = value["contacts"][0]

        sender_phone = msg["from"]
        sender_name  = contact["profile"].get("name", "Unknown")
        message_id   = msg["id"]

        if msg["type"] == "text":
            text = msg["text"]["body"]
        elif msg["type"] == "interactive":
            text = msg["interactive"]["button_reply"]["title"]
        else:
            text = f"[{msg['type']} message]"

        return {
            "sender_phone": sender_phone,
            "sender_name":  sender_name,
            "message_id":   message_id,
            "text":         text,
            "type":         msg["type"]
        }
    except (KeyError, IndexError):
        return None


# ─── Verify Webhook ───────────────────────────────────────────────────────────

def verify_webhook(mode: str, token: str, challenge: str) -> str | None:
    """Return challenge string if token matches, else None."""
    if mode == "subscribe" and token == VERIFY_TOKEN:
        return challenge
    return None
