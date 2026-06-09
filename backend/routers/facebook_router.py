from fastapi import APIRouter, Request
from fastapi.responses import PlainTextResponse
from services.facebook_service import (
    send_facebook_message,
    parse_facebook_webhook,
    verify_facebook_webhook
)

router = APIRouter()

@router.get("/webhook")
async def verify(request: Request):
    params = dict(request.query_params)
    challenge = verify_facebook_webhook(
        params.get("hub.mode", ""),
        params.get("hub.verify_token", ""),
        params.get("hub.challenge", "")
    )
    if challenge:
        return PlainTextResponse(content=challenge)
    return PlainTextResponse(content="Forbidden", status_code=403)


@router.post("/webhook")
async def webhook(request: Request):
    payload = await request.json()
    print("Facebook Webhook:", payload)

    parsed = parse_facebook_webhook(payload)
    if not parsed:
        return {"status": "ignored"}

    sender_id = parsed["sender_id"]
    text = parsed["text"]
    print(f"Facebook Message from {sender_id}: {text}")

    # ── AI Reply (reuse your existing AI service) ──
    from app.services.ai_service import get_ai_reply
    ai_reply = await get_ai_reply(sender_id, text, channel="facebook")

    # ── Send Reply ──
    await send_facebook_message(sender_id, ai_reply)

    return {"status": "ok"}
