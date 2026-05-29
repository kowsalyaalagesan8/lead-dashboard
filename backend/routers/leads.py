from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from sqlalchemy import select, func
from typing import Optional
from database.db import get_db, Lead, Message
from datetime import datetime

router = APIRouter()


class LeadUpdate(BaseModel):
    name:        Optional[str] = None
    email:       Optional[str] = None
    phone:       Optional[str] = None
    status:      Optional[str] = None
    score:       Optional[float] = None
    category:    Optional[str] = None
    assigned_to: Optional[str] = None
    notes:       Optional[str] = None
    budget:      Optional[str] = None
    intent:      Optional[str] = None


class LeadCreate(BaseModel):
    name:    str
    phone:   str
    email:   Optional[str] = None
    channel: Optional[str] = "web"
    source:  Optional[str] = "manual"
    notes:   Optional[str] = None


# ─── Get All Leads ────────────────────────────────────────────────────────────

@router.get("/")
async def get_leads(status: Optional[str] = None, channel: Optional[str] = None):
    async for db in get_db():
        query = select(Lead).order_by(Lead.created_at.desc())
        if status:
            query = query.where(Lead.status == status)
        if channel:
            query = query.where(Lead.channel == channel)
        result = await db.execute(query)
        leads  = result.scalars().all()
        return [lead_to_dict(l) for l in leads]


# ─── Get Single Lead ──────────────────────────────────────────────────────────

@router.get("/{lead_id}")
async def get_lead(lead_id: int):
    async for db in get_db():
        result = await db.execute(select(Lead).where(Lead.id == lead_id))
        lead   = result.scalar_one_or_none()
        if not lead:
            raise HTTPException(status_code=404, detail="Lead not found")

        # Get messages
        msgs_result = await db.execute(
            select(Message).where(Message.lead_id == lead_id).order_by(Message.created_at)
        )
        messages = msgs_result.scalars().all()

        data = lead_to_dict(lead)
        data["messages"] = [
            {
                "id":        m.id,
                "direction": m.direction,
                "content":   m.content,
                "channel":   m.channel,
                "created_at": str(m.created_at)
            }
            for m in messages
        ]
        return data


# ─── Create Lead ──────────────────────────────────────────────────────────────

@router.post("/")
async def create_lead(body: LeadCreate):
    async for db in get_db():
        lead = Lead(**body.dict())
        db.add(lead)
        await db.commit()
        await db.refresh(lead)
        return lead_to_dict(lead)


# ─── Update Lead ──────────────────────────────────────────────────────────────

@router.put("/{lead_id}")
async def update_lead(lead_id: int, body: LeadUpdate):
    async for db in get_db():
        result = await db.execute(select(Lead).where(Lead.id == lead_id))
        lead   = result.scalar_one_or_none()
        if not lead:
            raise HTTPException(status_code=404, detail="Lead not found")

        for field, value in body.dict(exclude_none=True).items():
            setattr(lead, field, value)
        lead.updated_at = datetime.utcnow()
        await db.commit()
        return lead_to_dict(lead)


# ─── Delete Lead ──────────────────────────────────────────────────────────────

@router.delete("/{lead_id}")
async def delete_lead(lead_id: int):
    async for db in get_db():
        result = await db.execute(select(Lead).where(Lead.id == lead_id))
        lead   = result.scalar_one_or_none()
        if not lead:
            raise HTTPException(status_code=404, detail="Lead not found")
        await db.delete(lead)
        await db.commit()
        return {"message": "Lead deleted"}


# ─── Pipeline Stats ───────────────────────────────────────────────────────────

@router.get("/stats/pipeline")
async def pipeline_stats():
    stages = ["new", "qualified", "contacted", "meeting", "proposal", "converted", "lost"]
    async for db in get_db():
        result = {}
        for stage in stages:
            count = await db.execute(
                select(func.count(Lead.id)).where(Lead.status == stage)
            )
            result[stage] = count.scalar()
        return result


# ─── Helper ───────────────────────────────────────────────────────────────────

def lead_to_dict(l: Lead) -> dict:
    return {
        "id":          l.id,
        "name":        l.name,
        "phone":       l.phone,
        "email":       l.email,
        "channel":     l.channel,
        "status":      l.status,
        "score":       l.score,
        "category":    l.category,
        "intent":      l.intent,
        "budget":      l.budget,
        "source":      l.source,
        "assigned_to": l.assigned_to,
        "notes":       l.notes,
        "created_at":  str(l.created_at),
        "updated_at":  str(l.updated_at),
    }
