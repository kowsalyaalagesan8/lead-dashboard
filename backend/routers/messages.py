from fastapi import APIRouter
from pydantic import BaseModel
from sqlalchemy import select
from database.db import get_db, Message
from typing import Optional

router = APIRouter()


class MessageCreate(BaseModel):
    lead_id:   int
    sender_id: str
    channel:   str
    direction: str
    content:   str
    msg_type:  Optional[str] = "text"


@router.get("/")
async def get_messages(lead_id: Optional[int] = None, channel: Optional[str] = None):
    async for db in get_db():
        query = select(Message).order_by(Message.created_at.desc())
        if lead_id:
            query = query.where(Message.lead_id == lead_id)
        if channel:
            query = query.where(Message.channel == channel)
        result   = await db.execute(query)
        messages = result.scalars().all()
        return [
            {
                "id":         m.id,
                "lead_id":    m.lead_id,
                "sender_id":  m.sender_id,
                "channel":    m.channel,
                "direction":  m.direction,
                "content":    m.content,
                "msg_type":   m.msg_type,
                "is_read":    m.is_read,
                "created_at": str(m.created_at)
            }
            for m in messages
        ]


@router.post("/")
async def create_message(body: MessageCreate):
    async for db in get_db():
        msg = Message(**body.dict())
        db.add(msg)
        await db.commit()
        await db.refresh(msg)
        return {"id": msg.id, "status": "saved"}


@router.put("/{msg_id}/read")
async def mark_read(msg_id: int):
    async for db in get_db():
        result = await db.execute(select(Message).where(Message.id == msg_id))
        msg    = result.scalar_one_or_none()
        if msg:
            msg.is_read = 1
            await db.commit()
        return {"status": "ok"}
