from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from database.db import get_db, Campaign
from services.ai_service import generate_campaign_summary
from typing import Optional

router = APIRouter()


class CampaignCreate(BaseModel):
    name:        str
    channel:     str
    leads:       Optional[int]  = 0
    conversions: Optional[int]  = 0
    spend:       Optional[float] = 0.0
    revenue:     Optional[float] = 0.0


@router.get("/")
async def get_campaigns():
    async for db in get_db():
        result    = await db.execute(select(Campaign).order_by(Campaign.created_at.desc()))
        campaigns = result.scalars().all()
        return [camp_to_dict(c) for c in campaigns]


@router.post("/")
async def create_campaign(body: CampaignCreate):
    async for db in get_db():
        c = Campaign(**body.dict())
        db.add(c)
        await db.commit()
        await db.refresh(c)
        return camp_to_dict(c)


@router.get("/{camp_id}/summary")
async def campaign_ai_summary(camp_id: int):
    async for db in get_db():
        result = await db.execute(select(Campaign).where(Campaign.id == camp_id))
        camp   = result.scalar_one_or_none()
        if not camp:
            raise HTTPException(status_code=404, detail="Campaign not found")
        data    = camp_to_dict(camp)
        summary = generate_campaign_summary(data)
        return {"summary": summary, "campaign": data}


def camp_to_dict(c: Campaign) -> dict:
    roi = round(((c.revenue - c.spend) / c.spend * 100), 1) if c.spend else 0
    cvr = round((c.conversions / c.leads * 100), 1) if c.leads else 0
    return {
        "id":          c.id,
        "name":        c.name,
        "channel":     c.channel,
        "status":      c.status,
        "leads":       c.leads,
        "conversions": c.conversions,
        "spend":       c.spend,
        "revenue":     c.revenue,
        "roi":         roi,
        "cvr":         cvr,
        "created_at":  str(c.created_at)
    }
