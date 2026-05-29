from fastapi import APIRouter
from sqlalchemy import select, func
from database.db import get_db, Lead, Message, Appointment, Campaign
from services.ai_service import generate_analytics_insight

router = APIRouter()


@router.get("/overview")
async def get_overview():
    async for db in get_db():
        total_leads = (await db.execute(select(func.count(Lead.id)))).scalar()
        converted   = (await db.execute(select(func.count(Lead.id)).where(Lead.status == "converted"))).scalar()
        hot_leads   = (await db.execute(select(func.count(Lead.id)).where(Lead.category == "hot"))).scalar()
        warm_leads  = (await db.execute(select(func.count(Lead.id)).where(Lead.category == "warm"))).scalar()
        cold_leads  = (await db.execute(select(func.count(Lead.id)).where(Lead.category == "cold"))).scalar()
        meetings    = (await db.execute(select(func.count(Appointment.id)))).scalar()
        messages    = (await db.execute(select(func.count(Message.id)))).scalar()

        conversion_rate = round((converted / total_leads * 100), 1) if total_leads else 0

        return {
            "total_leads":       total_leads,
            "converted":         converted,
            "conversion_rate":   conversion_rate,
            "hot_leads":         hot_leads,
            "warm_leads":        warm_leads,
            "cold_leads":        cold_leads,
            "total_meetings":    meetings,
            "total_messages":    messages,
        }


@router.get("/channels")
async def channel_breakdown():
    async for db in get_db():
        channels = ["whatsapp", "instagram", "web", "email", "facebook"]
        result   = {}
        for ch in channels:
            count = (await db.execute(
                select(func.count(Lead.id)).where(Lead.channel == ch)
            )).scalar()
            result[ch] = count
        return result


@router.get("/funnel")
async def funnel_data():
    stages = ["new", "qualified", "contacted", "meeting", "proposal", "converted"]
    async for db in get_db():
        result = []
        for stage in stages:
            count = (await db.execute(
                select(func.count(Lead.id)).where(Lead.status == stage)
            )).scalar()
            result.append({"stage": stage, "count": count})
        return result


@router.get("/ai-insight")
async def ai_insight():
    async for db in get_db():
        total     = (await db.execute(select(func.count(Lead.id)))).scalar()
        converted = (await db.execute(select(func.count(Lead.id)).where(Lead.status == "converted"))).scalar()
        hot       = (await db.execute(select(func.count(Lead.id)).where(Lead.category == "hot"))).scalar()

        wa_leads  = (await db.execute(select(func.count(Lead.id)).where(Lead.channel == "whatsapp"))).scalar()
        ig_leads  = (await db.execute(select(func.count(Lead.id)).where(Lead.channel == "instagram"))).scalar()

        data = {
            "total_leads": total,
            "converted": converted,
            "hot_leads": hot,
            "whatsapp_leads": wa_leads,
            "instagram_leads": ig_leads,
            "conversion_rate": round(converted / total * 100, 1) if total else 0
        }
        insight = generate_analytics_insight(data)
        return {"insight": insight, "data": data}
