from fastapi import APIRouter, Request
from fastapi.responses import PlainTextResponse
from sqlalchemy import select
from database.db import get_db, Lead, Message
from services.facebook_service import (
    send_facebook_message,
    parse_facebook_webhook,
    verify_facebook_webhook
)
from services.ai_service import qualify_lead
from datetime import datetime
import traceback

router = APIRouter()

# In-memory conversation store
conversation_store: dict[str, list] = {}

print("🚀 Facebook Router Loaded", flush=True)


# ─── Webhook Verification ─────────────────────────────────────────────────────

@router.get("/webhook")
async def facebook_verify(request: Request):
    print("\n==============================", flush=True)
    print("📥 FACEBOOK VERIFICATION HIT", flush=True)
    print("==============================", flush=True)

    params = dict(request.query_params)
    print("Params:", params, flush=True)

    challenge = verify_facebook_webhook(
        params.get("hub.mode", ""),
        params.get("hub.verify_token", ""),
        params.get("hub.challenge", "")
    )

    if challenge:
        print("✅ Verification Success", flush=True)
        return PlainTextResponse(content=challenge)

    print("❌ Verification Failed", flush=True)
    return PlainTextResponse(content="Forbidden", status_code=403)


# ─── Receive Incoming Messages ────────────────────────────────────────────────

@router.post("/webhook")
async def facebook_webhook(request: Request):
    try:
        print("\n====================================================", flush=True)
        print("📩 FACEBOOK WEBHOOK RECEIVED", flush=True)
        print("====================================================", flush=True)

        payload = await request.json()
        print("📦 RAW PAYLOAD:", flush=True)
        print(payload, flush=True)

        data = parse_facebook_webhook(payload)
        print("\n📋 PARSED DATA:", flush=True)
        print(data, flush=True)

        if not data:
            print("⚠️ No Facebook message detected - ignored", flush=True)
            return {"status": "ignored"}

        sender_id = data["sender_id"]
        text = data["text"]

        print(f"\n👤 Sender ID : {sender_id}", flush=True)
        print(f"💬 Message   : {text}", flush=True)

        # ── Conversation History ──────────────────────────
        history = conversation_store.get(sender_id, [])
        print(f"\n📝 Conversation History ({len(history)} messages)", flush=True)

        # ── AI Qualification ──────────────────────────────
        print("\n🤖 Running AI Qualification", flush=True)
        ai_result = qualify_lead(history, text)
        print("AI Result:", ai_result, flush=True)

        # ── Update Memory ─────────────────────────────────
        history.append({"role": "user", "content": text})
        history.append({"role": "assistant", "content": ai_result["reply"]})
        conversation_store[sender_id] = history[-20:]
        print("✅ Conversation Memory Updated", flush=True)

        # ── Database ──────────────────────────────────────
        async for db in get_db():
            print("\n🔍 Searching Existing Lead", flush=True)

            result = await db.execute(
                select(Lead).where(Lead.phone == sender_id)
            )
            lead = result.scalar_one_or_none()

            if lead:
                print(f"✅ Existing Lead Found | ID={lead.id}", flush=True)
            else:
                print("🆕 New Lead Will Be Created", flush=True)

            if not lead:
                lead = Lead(
                    name=ai_result.get("name") or "Facebook User",
                    phone=sender_id,
                    email=ai_result.get("email"),
                    channel="facebook",
                    status="new",
                    score=ai_result.get("score", 0),
                    category=ai_result.get("category", "cold"),
                    intent=ai_result.get("intent"),
                    budget=ai_result.get("budget"),
                    source="facebook_dm"
                )
                db.add(lead)
                print("🆕 New Lead Added", flush=True)
            else:
                print("✏️ Updating Existing Lead", flush=True)
                if ai_result.get("name"):   lead.name   = ai_result["name"]
                if ai_result.get("email"):  lead.email  = ai_result["email"]
                if ai_result.get("budget"): lead.budget = ai_result["budget"]
                if ai_result.get("intent"): lead.intent = ai_result["intent"]
                lead.score    = ai_result.get("score", lead.score)
                lead.category = ai_result.get("category", lead.category)
                if ai_result.get("is_qualified"):
                    lead.status = "qualified"
                lead.updated_at = datetime.utcnow()

            print("\n💾 Saving Lead", flush=True)
            await db.commit()
            await db.refresh(lead)
            print(f"✅ Lead Saved | ID={lead.id}", flush=True)

            print("💬 Saving Inbound Message", flush=True)
            db.add(Message(
                lead_id=lead.id,
                sender_id=sender_id,
                channel="facebook",
                direction="inbound",
                content=text
            ))

            print("💬 Saving Outbound Message", flush=True)
            db.add(Message(
                lead_id=lead.id,
                sender_id=sender_id,
                channel="facebook",
                direction="outbound",
                content=ai_result["reply"]
            ))
            await db.commit()
            print("✅ Messages Saved", flush=True)

        # ── Send AI Reply ─────────────────────────────────
        print("\n📤 Sending AI Reply", flush=True)
        print(ai_result["reply"], flush=True)

        send_result = await send_facebook_message(
            sender_id,
            ai_result["reply"]
        )

        print("Facebook Send Result:", flush=True)
        print(send_result, flush=True)
        print("✅ Reply Sent Successfully", flush=True)

        return {"status": "ok"}

    except Exception as e:
        print("\n❌❌❌ FACEBOOK WEBHOOK ERROR ❌❌❌", flush=True)
        print(type(e).__name__, flush=True)
        print(str(e), flush=True)
        traceback.print_exc()
        raise
