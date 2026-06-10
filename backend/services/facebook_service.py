import httpx
import os
from dotenv import load_dotenv

load_dotenv()

PAGE_TOKEN = os.getenv("FACEBOOK_PAGE_TOKEN")
PAGE_ID = os.getenv("FACEBOOK_PAGE_ID")
VERIFY_TOKEN = os.getenv("WHATSAPP_VERIFY_TOKEN", "Agnel")

print("=== Facebook Configuration ===", flush=True)
print("PAGE_TOKEN:", PAGE_TOKEN[:20] + "..." if PAGE_TOKEN else "NOT FOUND", flush=True)
print("PAGE_ID:", PAGE_ID, flush=True)
print("VERIFY_TOKEN:", VERIFY_TOKEN, flush=True)
print("==============================", flush=True)


async def send_facebook_message(recipient_id: str, message: str) -> dict:
    print("\n📤 Sending Facebook Message", flush=True)
    print(f"Recipient ID : {recipient_id}", flush=True)
    print(f"Message      : {message}", flush=True)

    # Truncate to 2000 chars (Facebook limit)
    if len(message) > 2000:
        message = message[:1997] + "..."
        print("⚠️ Message truncated to 2000 chars", flush=True)

    url = f"https://graph.facebook.com/v18.0/{PAGE_ID}/messages"
    print(f"URL: {url}", flush=True)

    payload = {
        "recipient": {"id": recipient_id},
        "message": {"text": message},
        "messaging_type": "RESPONSE",
        "access_token": PAGE_TOKEN
    }

    async with httpx.AsyncClient() as client:
        response = await client.post(url, json=payload, timeout=10)
        result = response.json()
        print("Facebook Send Response:", result, flush=True)

        if "error" in result:
            print(f"❌ Send Error: {result['error']['message']}", flush=True)
        else:
            print("✅ Message Sent Successfully", flush=True)

        return result


def parse_facebook_webhook(payload: dict) -> dict | None:
    print("\n[FACEBOOK WEBHOOK PARSE]", flush=True)
    print("Payload:", payload, flush=True)

    try:
        entry = payload["entry"][0]
        messaging = entry["messaging"][0]

        sender_id = messaging["sender"]["id"]
        recipient_id = messaging["recipient"]["id"]

        print(f"Sender ID    : {sender_id}", flush=True)
        print(f"Recipient ID : {recipient_id}", flush=True)

        # Ignore page's own messages
        if sender_id == PAGE_ID:
            print("⚠️ Ignoring page self-message", flush=True)
            return None

        msg = messaging.get("message", {})

        if not msg:
            print("⚠️ No message object found", flush=True)
            return None

        if msg.get("is_echo"):
            print("⚠️ Ignoring echo message", flush=True)
            return None

        text = msg.get("text", "")

        if not text:
            attachments = msg.get("attachments", [])
            if attachments:
                text = f"[{attachments[0]['type']} attachment]"
                print(f"📎 Attachment detected: {text}", flush=True)
            else:
                print("⚠️ No text or attachment found", flush=True)
                return None

        parsed_data = {
            "sender_id": sender_id,
            "sender_name": "Facebook User",
            "text": text,
            "message_id": msg.get("mid", "")
        }

        print("✅ Parsed Data:", parsed_data, flush=True)
        return parsed_data

    except Exception as e:
        print(f"❌ Facebook Webhook Parse Error: {e}", flush=True)
        return None


def verify_facebook_webhook(mode: str, token: str, challenge: str):
    print("\n[FACEBOOK VERIFY WEBHOOK]", flush=True)
    print(f"Mode           : {mode}", flush=True)
    print(f"Token          : {token}", flush=True)
    print(f"Expected Token : {VERIFY_TOKEN}", flush=True)
    print(f"Challenge      : {challenge}", flush=True)

    if mode == "subscribe" and token == VERIFY_TOKEN:
        print("✅ Verification Successful", flush=True)
        return challenge

    print("❌ Verification Failed", flush=True)
    return None
