import httpx
import os
from dotenv import load_dotenv

load_dotenv()

INSTAGRAM_TOKEN = os.getenv("INSTAGRAM_ACCESS_TOKEN")
PAGE_ID = os.getenv("INSTAGRAM_PAGE_ID")
VERIFY_TOKEN = os.getenv("WHATSAPP_VERIFY_TOKEN", "mytoken123")
BASE_URL = "https://graph.facebook.com/v18.0"

print("=== Instagram Configuration ===")
print("INSTAGRAM_TOKEN:", INSTAGRAM_TOKEN[:20] + "..." if INSTAGRAM_TOKEN else "NOT FOUND")
print("PAGE_ID:", PAGE_ID)
print("VERIFY_TOKEN:", VERIFY_TOKEN)
print("===============================")


# ─── Send Instagram DM ────────────────────────────────────────────────────────


async def send_instagram_message(recipient_id: str, message: str) -> dict:
    
    PAGE_ID = os.getenv("INSTAGRAM_PAGE_ID")
    PAGE_TOKEN = os.getenv("INSTAGRAM_ACCESS_TOKEN")  # ← add this line
    url = f"https://graph.facebook.com/v18.0/{PAGE_ID}/messages"
    
    # ❌ Remove these headers entirely
    # headers = {
    #     "Authorization": f"Bearer {INSTAGRAM_TOKEN}",
    #     "Content-Type": "application/json"
    # }
    
    payload = {
        "recipient": {"id": recipient_id},
        "message":   {"text": message},
        "messaging_type": "RESPONSE",
        "access_token": PAGE_TOKEN        # ✅ token goes here in body
    }
    async with httpx.AsyncClient() as client:
        response = await client.post(
            url, json=payload, timeout=10  # ← no headers parameter
        )
        print("Instagram Send Response:", response.json())
        return response.json()

# ─── Parse Instagram Webhook ──────────────────────────────────────────────────

def parse_instagram_webhook(payload: dict) -> dict | None:
    print("\n[INSTAGRAM WEBHOOK RECEIVED]")
    print("Payload:", payload)

    try:
        entry = payload["entry"][0]
        messaging = entry["messaging"][0]

        sender_id = messaging["sender"]["id"]
        recipient = messaging["recipient"]["id"]

        print("Sender ID:", sender_id)
        print("Recipient ID:", recipient)

        # Ignore messages sent by the page itself
        if sender_id == PAGE_ID:
            print("Ignoring page self-message")
            return None

        msg = messaging.get("message", {})

        if not msg:
            print("No message object found")
            return None

        if msg.get("is_echo"):
            print("Ignoring echo message")
            return None

        text = msg.get("text", "")

        if not text:
            attachments = msg.get("attachments", [])

            if attachments:
                text = f"[{attachments[0]['type']} attachment]"
                print("Attachment detected:", text)
            else:
                print("No text or attachment found")
                return None

        parsed_data = {
            "sender_id": sender_id,
            "sender_name": "Instagram User",
            "text": text,
            "message_id": msg.get("mid", "")
        }

        print("Parsed Data:", parsed_data)

        return parsed_data

    except Exception as e:
        print("Webhook Parse Error:", str(e))
        return None


# ─── Verify Webhook ───────────────────────────────────────────────────────────

def verify_instagram_webhook(mode: str, token: str, challenge: str) -> str | None:

    print("\n[VERIFY WEBHOOK]")
    print("Mode:", mode)
    print("Token:", token)
    print("Expected Token:", VERIFY_TOKEN)

    if mode == "subscribe" and token == VERIFY_TOKEN:
        print("Webhook verification successful")
        return challenge

    print("Webhook verification failed")
    return None


# ─── Get User Profile ─────────────────────────────────────────────────────────

async def get_instagram_profile(user_id: str) -> dict:

    print(f"\n[GET INSTAGRAM PROFILE]")
    print("User ID:", user_id)

    url = f"{BASE_URL}/{user_id}"

    params = {
        "fields": "name,profile_pic",
        "access_token": INSTAGRAM_TOKEN
    }

    print("Request URL:", url)
    print("Params:", params)

    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(url, params=params, timeout=10)

            print("Status Code:", response.status_code)
            print("Response:", response.text)

            data = response.json()

            profile = {
                "name": data.get("name", "Instagram User"),
                "profile_pic": data.get("profile_pic", "")
            }

            print("Profile Data:", profile)

            return profile

        except Exception as e:
            print("Profile Fetch Error:", str(e))
            return {
                "name": "Instagram User",
                "profile_pic": ""
            }
