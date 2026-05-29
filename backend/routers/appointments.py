from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from database.db import get_db, Appointment
from typing import Optional
from datetime import datetime

router = APIRouter()


class AppointmentCreate(BaseModel):
    lead_id:   int
    lead_name: str
    datetime:  str
    duration:  Optional[int] = 30
    zoom_link: Optional[str] = None
    notes:     Optional[str] = None


@router.get("/")
async def get_appointments():
    async for db in get_db():
        result = await db.execute(select(Appointment).order_by(Appointment.created_at.desc()))
        appts  = result.scalars().all()
        return [appt_to_dict(a) for a in appts]


@router.post("/")
async def create_appointment(body: AppointmentCreate):
    async for db in get_db():
        appt = Appointment(**body.dict())
        db.add(appt)
        await db.commit()
        await db.refresh(appt)
        return appt_to_dict(appt)


@router.put("/{appt_id}/status")
async def update_status(appt_id: int, status: str):
    async for db in get_db():
        result = await db.execute(select(Appointment).where(Appointment.id == appt_id))
        appt   = result.scalar_one_or_none()
        if not appt:
            raise HTTPException(status_code=404, detail="Appointment not found")
        appt.status = status
        await db.commit()
        return appt_to_dict(appt)


@router.delete("/{appt_id}")
async def delete_appointment(appt_id: int):
    async for db in get_db():
        result = await db.execute(select(Appointment).where(Appointment.id == appt_id))
        appt   = result.scalar_one_or_none()
        if not appt:
            raise HTTPException(status_code=404, detail="Not found")
        await db.delete(appt)
        await db.commit()
        return {"message": "Deleted"}


def appt_to_dict(a: Appointment) -> dict:
    return {
        "id":         a.id,
        "lead_id":    a.lead_id,
        "lead_name":  a.lead_name,
        "datetime":   a.datetime,
        "duration":   a.duration,
        "status":     a.status,
        "zoom_link":  a.zoom_link,
        "notes":      a.notes,
        "created_at": str(a.created_at)
    }
