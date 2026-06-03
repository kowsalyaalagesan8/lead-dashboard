from fastapi import APIRouter, Request, Query, HTTPException
from fastapi.responses import PlainTextResponse
from sqlalchemy import select
from database.db import get_db, Lead, Message, Appointment
from services.instagram_service import (
    parse_instagram_webhook, verify_instagram_webhook,
    send_instagram_message, get_instagram_profile
)
from services.ai_service import qualify_lead
from datetime import datetime

router = APIRouter()

# In-memory conversation store { instagram_id: [ {role, content} ] }
conversation_store: dict[str, list] = {}

ZOOM_LINK = "https://zoom.us/j/your-zoom-room"


# ─── Webhook Verification ─────────────────────────────────────────────────────

@router.get("/webhook")
async def instagram_verify(
    hub_mode:      str = Query(None, alias="hub.mode"),
    hub_token:     str = Query(None, alias="hub.verify_token"),
    hub_challenge: str = Query(None, alias="hub.challenge")
):
    result = verify_instagram_webhook(hub_mode, hub_token, hub_challenge)
    if result:
        return PlainTextResponse(content=result)
    raise HTTPException(status_code=403, detail="Verification failed")


# ─── Receive Instagram DMs ────────────────────────────────────────────────────

@router.post("/webhook")
async def instagram_webhook(request: Request):
    payload = await request.json()
    data    = parse_instagram_webhook(payload)

    if not data:
        return {"status": "ignored"}

    sender_id   = data["sender_id"]
    text        = data["text"]

    # Fetch Instagram profile name
    profile     = await get_instagram_profile(sender_id)
    sender_name = profile.get("name", "Instagram User")

    # Get or init conversation history
    history   = conversation_store.get(sender_id, [])
    ai_result = qualify_lead(history, text)

    # Update conversation history
    history.append({"role": "user",      "content": text})
    history.append({"role": "assistant", "content": ai_result["reply"]})
    conversation_store[sender_id] = history[-20:]

    # ── Save to DB ─────────────────────────────────────────────
    async for db in get_db():
        # Check if lead already exists by instagram sender_id stored in phone field
        result = await db.execute(
            select(Lead).where(Lead.phone == sender_id)
        )
        lead = result.scalar_one_or_none()

        if not lead:
            lead = Lead(
                name     = ai_result.get("name") or sender_name,
                phone    = sender_id,        # store instagram ID here
                email    = ai_result.get("email"),
                channel  = "instagram",
                status   = "new",
                score    = ai_result.get("score", 0),
                category = ai_result.get("category", "cold"),
                intent   = ai_result.get("intent"),
                budget   = ai_result.get("budget"),
                source   = "instagram_dm"
            )
            db.add(lead)
        else:
            if ai_result.get("name"):   lead.name   = ai_result["name"]
            if ai_result.get("email"):  lead.email  = ai_result["email"]
            if ai_result.get("budget"): lead.budget = ai_result["budget"]
            if ai_result.get("intent"): lead.intent = ai_result["intent"]
            lead.score      = ai_result.get("score", lead.score)
            lead.category   = ai_result.get("category", lead.category)
            if ai_result.get("is_qualified"):
                lead.status = "qualified"
            lead.updated_at = datetime.utcnow()

        await db.commit()
        await db.refresh(lead)

        # Save messages
        db.add(Message(
            lead_id   = lead.id,
            sender_id = sender_id,
            channel   = "instagram",
            direction = "inbound",
            content   = text
        ))
        db.add(Message(
            lead_id   = lead.id,
            sender_id = sender_id,
            channel   = "instagram",
            direction = "outbound",
            content   = ai_result["reply"]
        ))
        await db.commit()

        # ── AUTO BOOK MEETING ──────────────────────────────────
        if ai_result.get("meeting_requested"):
            meeting_dt = ai_result.get("meeting_datetime") or "To be confirmed"

            appt = Appointment(
                lead_id   = lead.id,
                lead_name = lead.name or sender_name,
                datetime  = meeting_dt,
                duration  = 30,
                status    = "scheduled",
                zoom_link = ZOOM_LINK,
                notes     = f"Booked via Instagram DM. Intent: {lead.intent}"
            )
            db.add(appt)
            lead.status = "meeting"
            await db.commit()

            confirm_msg = (
                f"✅ Meeting Confirmed!\n\n"
                f"📅 Date/Time: {meeting_dt}\n"
                f"⏱ Duration: 30 minutes\n"
                f"🎥 Zoom Link: {ZOOM_LINK}\n\n"
                f"We'll remind you before the meeting. Talk soon! 🙌"
            )
            await send_instagram_message(sender_id, confirm_msg)

            db.add(Message(
                lead_id   = lead.id,
                sender_id = sender_id,
                channel   = "instagram",
                direction = "outbound",
                content   = confirm_msg
            ))
            await db.commit()
            return {"status": "ok", "meeting_booked": True}

    # Send normal AI reply
    await send_instagram_message(sender_id, ai_result["reply"])
    return {"status": "ok"}


# ─── Manual Send ──────────────────────────────────────────────────────────────

@router.post("/send")
async def send_instagram_manual(instagram_id: str, message: str):
    result = await send_instagram_message(instagram_id, message)
    return {"status": "sent", "result": result}
