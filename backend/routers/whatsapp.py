from fastapi import APIRouter, Request, Query, HTTPException
from fastapi.responses import PlainTextResponse
from sqlalchemy import select
from database.db import get_db, Lead, Message
from services.whatsapp_service import (
    parse_whatsapp_webhook, verify_webhook, send_whatsapp_message
)
from services.ai_service import qualify_lead
from datetime import datetime

router = APIRouter()

# In-memory conversation store  { phone: [ {role, content} ] }
conversation_store: dict[str, list] = {}


# ─── Webhook Verification ─────────────────────────────────────────────────────

@router.get("/webhook")
async def whatsapp_verify(
    hub_mode: str      = Query(None, alias="hub.mode"),
    hub_token: str     = Query(None, alias="hub.verify_token"),
    hub_challenge: str = Query(None, alias="hub.challenge")
):
    result = verify_webhook(hub_mode, hub_token, hub_challenge)
    if result:
        return PlainTextResponse(content=result)
    raise HTTPException(status_code=403, detail="Verification failed")


# ─── Receive Incoming Messages ────────────────────────────────────────────────

@router.post("/webhook")
async def whatsapp_webhook(request: Request):
    payload = await request.json()
    data    = parse_whatsapp_webhook(payload)

    if not data:
        return {"status": "ignored"}

    phone   = data["sender_phone"]
    name    = data["sender_name"]
    text    = data["text"]

    # Get or init conversation history
    history = conversation_store.get(phone, [])

    # Call AI qualifier
    ai_result = qualify_lead(history, text)

    # Update conversation history
    history.append({"role": "user",      "content": text})
    history.append({"role": "assistant", "content": ai_result["reply"]})
    conversation_store[phone] = history[-20:]   # keep last 20 turns

    # Persist to DB
    async for db in get_db():
        # Check if lead exists
        result = await db.execute(select(Lead).where(Lead.phone == phone))
        lead   = result.scalar_one_or_none()

        if not lead:
            lead = Lead(
                name     = ai_result.get("name") or name,
                phone    = phone,
                email    = ai_result.get("email"),
                channel  = "whatsapp",
                status   = "new",
                score    = ai_result.get("score", 0),
                category = ai_result.get("category", "cold"),
                intent   = ai_result.get("intent"),
                budget   = ai_result.get("budget"),
                source   = "whatsapp_inbound"
            )
            db.add(lead)
        else:
            # Update existing lead with latest AI data
            if ai_result.get("name"):    lead.name     = ai_result["name"]
            if ai_result.get("email"):   lead.email    = ai_result["email"]
            if ai_result.get("budget"):  lead.budget   = ai_result["budget"]
            if ai_result.get("intent"):  lead.intent   = ai_result["intent"]
            lead.score    = ai_result.get("score", lead.score)
            lead.category = ai_result.get("category", lead.category)
            if ai_result.get("is_qualified"):
                lead.status = "qualified"
            lead.updated_at = datetime.utcnow()

        await db.commit()
        await db.refresh(lead)

        # Save inbound message
        db.add(Message(
            lead_id   = lead.id,
            sender_id = phone,
            channel   = "whatsapp",
            direction = "inbound",
            content   = text
        ))

        # Save outbound reply
        db.add(Message(
            lead_id   = lead.id,
            sender_id = phone,
            channel   = "whatsapp",
            direction = "outbound",
            content   = ai_result["reply"]
        ))
        await db.commit()

    # Send AI reply back to WhatsApp
    await send_whatsapp_message(phone, ai_result["reply"])

    return {"status": "ok"}


# ─── Manual Send Message ──────────────────────────────────────────────────────

@router.post("/send")
async def send_message_manual(phone: str, message: str):
    result = await send_whatsapp_message(phone, message)
    return {"status": "sent", "result": result}
