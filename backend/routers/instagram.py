from fastapi import APIRouter, Request, Query, HTTPException
from fastapi.responses import PlainTextResponse
from sqlalchemy import select
from database.db import get_db, Lead, Message, Appointment
from services.instagram_services import (
    parse_instagram_webhook,
    verify_instagram_webhook,
    send_instagram_message,
    get_instagram_profile
)
from services.ai_service import qualify_lead
from datetime import datetime
import traceback

router = APIRouter()

# In-memory conversation store
conversation_store: dict[str, list] = {}

ZOOM_LINK = "https://zoom.us/j/your-zoom-room"

print("🚀 Instagram Router Loaded")


# ─────────────────────────────────────────────────────────────
# WEBHOOK VERIFICATION
# ─────────────────────────────────────────────────────────────

@router.get("/webhook")
async def instagram_verify(
    hub_mode: str = Query(None, alias="hub.mode"),
    hub_token: str = Query(None, alias="hub.verify_token"),
    hub_challenge: str = Query(None, alias="hub.challenge")
):
    print("\n==============================")
    print("📥 INSTAGRAM VERIFICATION HIT")
    print("==============================")
    print(f"hub_mode      : {hub_mode}")
    print(f"hub_token     : {hub_token}")
    print(f"hub_challenge : {hub_challenge}")

    result = verify_instagram_webhook(
        hub_mode,
        hub_token,
        hub_challenge
    )

    print(f"Verification Result: {result}")

    if result:
        print("✅ Verification Success")
        return PlainTextResponse(content=result)

    print("❌ Verification Failed")
    raise HTTPException(status_code=403, detail="Verification failed")


# ─────────────────────────────────────────────────────────────
# RECEIVE INSTAGRAM DM
# ─────────────────────────────────────────────────────────────

@router.post("/webhook")
async def instagram_webhook(request: Request):

    try:
        print("\n====================================================")
        print("📩 INSTAGRAM WEBHOOK RECEIVED")
        print("====================================================")

        payload = await request.json()

        print("📦 RAW PAYLOAD:")
        print(payload)

        data = parse_instagram_webhook(payload)

        print("\n📋 PARSED DATA:")
        print(data)

        if not data:
            print("⚠️ No Instagram message detected")
            return {"status": "ignored"}

        sender_id = data["sender_id"]
        text = data["text"]

        print(f"\n👤 Sender ID : {sender_id}")
        print(f"💬 Message   : {text}")

        # --------------------------------------------------
        # GET PROFILE
        # --------------------------------------------------

        print("\n🔍 Fetching Instagram Profile")

        profile = await get_instagram_profile(sender_id)

        print("Profile Response:")
        print(profile)

        sender_name = profile.get("name", "Instagram User")

        print(f"👤 Sender Name: {sender_name}")

        # --------------------------------------------------
        # CONVERSATION HISTORY
        # --------------------------------------------------

        history = conversation_store.get(sender_id, [])

        print("\n📝 Conversation History:")
        print(history)

        print("\n🤖 Running AI Qualification")

        ai_result = qualify_lead(history, text)

        print("AI Result:")
        print(ai_result)

        # --------------------------------------------------
        # UPDATE MEMORY
        # --------------------------------------------------

        history.append({
            "role": "user",
            "content": text
        })

        history.append({
            "role": "assistant",
            "content": ai_result["reply"]
        })

        conversation_store[sender_id] = history[-20:]

        print("\n✅ Conversation Memory Updated")

        # --------------------------------------------------
        # DATABASE
        # --------------------------------------------------

        async for db in get_db():

            print("\n🔍 Searching Existing Lead")

            result = await db.execute(
                select(Lead).where(
                    Lead.phone == sender_id
                )
            )

            lead = result.scalar_one_or_none()

            if lead:
                print(
                    f"✅ Existing Lead Found | "
                    f"ID={lead.id}"
                )
            else:
                print("🆕 New Lead Will Be Created")

            # ----------------------------------------------
            # CREATE LEAD
            # ----------------------------------------------

            if not lead:

                lead = Lead(
                    name=ai_result.get("name") or sender_name,
                    phone=sender_id,
                    email=ai_result.get("email"),
                    channel="instagram",
                    status="new",
                    score=ai_result.get("score", 0),
                    category=ai_result.get("category", "cold"),
                    intent=ai_result.get("intent"),
                    budget=ai_result.get("budget"),
                    source="instagram_dm"
                )

                db.add(lead)

                print("🆕 New Lead Added")

            else:

                print("✏️ Updating Existing Lead")

                if ai_result.get("name"):
                    lead.name = ai_result["name"]

                if ai_result.get("email"):
                    lead.email = ai_result["email"]

                if ai_result.get("budget"):
                    lead.budget = ai_result["budget"]

                if ai_result.get("intent"):
                    lead.intent = ai_result["intent"]

                lead.score = ai_result.get(
                    "score",
                    lead.score
                )

                lead.category = ai_result.get(
                    "category",
                    lead.category
                )

                if ai_result.get("is_qualified"):
                    lead.status = "qualified"

                lead.updated_at = datetime.utcnow()

            print("\n💾 Saving Lead")

            await db.commit()
            await db.refresh(lead)

            print(f"✅ Lead Saved | ID={lead.id}")

            # ----------------------------------------------
            # SAVE INBOUND MESSAGE
            # ----------------------------------------------

            print("💬 Saving Inbound Message")

            db.add(
                Message(
                    lead_id=lead.id,
                    sender_id=sender_id,
                    channel="instagram",
                    direction="inbound",
                    content=text
                )
            )

            # ----------------------------------------------
            # SAVE OUTBOUND MESSAGE
            # ----------------------------------------------

            print("💬 Saving Outbound Message")

            db.add(
                Message(
                    lead_id=lead.id,
                    sender_id=sender_id,
                    channel="instagram",
                    direction="outbound",
                    content=ai_result["reply"]
                )
            )

            await db.commit()

            print("✅ Messages Saved")

            # ----------------------------------------------
            # AUTO MEETING BOOKING
            # ----------------------------------------------

            if ai_result.get("meeting_requested"):

                print("\n📅 Meeting Requested")

                meeting_dt = (
                    ai_result.get("meeting_datetime")
                    or "To be confirmed"
                )

                print(
                    f"Meeting Datetime: "
                    f"{meeting_dt}"
                )

                appt = Appointment(
                    lead_id=lead.id,
                    lead_name=lead.name or sender_name,
                    datetime=meeting_dt,
                    duration=30,
                    status="scheduled",
                    zoom_link=ZOOM_LINK,
                    notes=f"Booked via Instagram DM. Intent: {lead.intent}"
                )

                db.add(appt)

                lead.status = "meeting"

                await db.commit()

                print("✅ Appointment Saved")

                confirm_msg = (
                    f"✅ Meeting Confirmed!\n\n"
                    f"📅 Date/Time: {meeting_dt}\n"
                    f"⏱ Duration: 30 minutes\n"
                    f"🎥 Zoom Link: {ZOOM_LINK}\n\n"
                    f"We'll remind you before the meeting. Talk soon! 🙌"
                )

                print("\n📤 Sending Meeting Confirmation")
                print(confirm_msg)

                send_result = await send_instagram_message(
                    sender_id,
                    confirm_msg
                )

                print("Instagram Send Result:")
                print(send_result)

                db.add(
                    Message(
                        lead_id=lead.id,
                        sender_id=sender_id,
                        channel="instagram",
                        direction="outbound",
                        content=confirm_msg
                    )
                )

                await db.commit()

                print("✅ Meeting Confirmation Stored")

                return {
                    "status": "ok",
                    "meeting_booked": True
                }

        # --------------------------------------------------
        # NORMAL AI RESPONSE
        # --------------------------------------------------

        print("\n📤 Sending AI Reply")
        print(ai_result["reply"])

        send_result = await send_instagram_message(
            sender_id,
            ai_result["reply"]
        )

        print("Instagram Send Result:")
        print(send_result)

        print("✅ Reply Sent Successfully")

        return {"status": "ok"}

    except Exception as e:

        print("\n")
        print("❌❌❌ WEBHOOK ERROR ❌❌❌")
        print(type(e).__name__)
        print(str(e))

        traceback.print_exc()

        raise
