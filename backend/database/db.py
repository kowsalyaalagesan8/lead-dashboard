from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy import Column, Integer, String, Float, DateTime, Text
from datetime import datetime
import os
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///./leads.db")
# Convert sqlite:// to sqlite+aiosqlite://
if DATABASE_URL.startswith("sqlite:///"):
    DATABASE_URL = DATABASE_URL.replace("sqlite:///", "sqlite+aiosqlite:///")

engine = create_async_engine(DATABASE_URL, echo=False)
AsyncSessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
Base = declarative_base()


# ─── Models ──────────────────────────────────────────────────────────────────

class Lead(Base):
    __tablename__ = "leads"
    id              = Column(Integer, primary_key=True, index=True)
    name            = Column(String(100), nullable=True)
    phone           = Column(String(20), nullable=True)
    email           = Column(String(100), nullable=True)
    channel         = Column(String(30), default="whatsapp")   # whatsapp/instagram/web
    status          = Column(String(30), default="new")        # new/qualified/contacted/meeting/proposal/converted/lost
    score           = Column(Float, default=0.0)
    category        = Column(String(20), default="cold")       # hot/warm/cold
    intent          = Column(String(200), nullable=True)
    budget          = Column(String(50), nullable=True)
    source          = Column(String(50), nullable=True)
    assigned_to     = Column(String(100), nullable=True)
    notes           = Column(Text, nullable=True)
    created_at      = Column(DateTime, default=datetime.utcnow)
    updated_at      = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class Message(Base):
    __tablename__ = "messages"
    id          = Column(Integer, primary_key=True, index=True)
    lead_id     = Column(Integer, nullable=True)
    sender_id   = Column(String(50))                      # phone number or instagram id
    channel     = Column(String(30), default="whatsapp")
    direction   = Column(String(10))                      # inbound / outbound
    content     = Column(Text)
    msg_type    = Column(String(20), default="text")      # text/image/audio
    is_read     = Column(Integer, default=0)
    created_at  = Column(DateTime, default=datetime.utcnow)


class Appointment(Base):
    __tablename__ = "appointments"
    id          = Column(Integer, primary_key=True, index=True)
    lead_id     = Column(Integer)
    lead_name   = Column(String(100))
    # datetime    = Column(String(50))
    # datetime = Column(DateTime)
    # created_at = Column(DateTime, default=datetime.utcnow)
    duration    = Column(Integer, default=30)              # minutes
    status      = Column(String(20), default="scheduled") # scheduled/completed/cancelled
    zoom_link   = Column(String(200), nullable=True)
    notes       = Column(Text, nullable=True)
    created_at  = Column(DateTime, default=datetime.utcnow)


class Campaign(Base):
    __tablename__ = "campaigns"
    id          = Column(Integer, primary_key=True, index=True)
    name        = Column(String(100))
    channel     = Column(String(30))
    status      = Column(String(20), default="active")
    leads       = Column(Integer, default=0)
    conversions = Column(Integer, default=0)
    spend       = Column(Float, default=0.0)
    revenue     = Column(Float, default=0.0)
    created_at  = Column(DateTime, default=datetime.utcnow)


class FollowUp(Base):
    __tablename__ = "followups"
    id          = Column(Integer, primary_key=True, index=True)
    lead_id     = Column(Integer)
    message     = Column(Text)
    scheduled   = Column(String(50))
    status      = Column(String(20), default="pending")   # pending/sent/failed
    created_at  = Column(DateTime, default=datetime.utcnow)


# ─── Init ────────────────────────────────────────────────────────────────────

async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    print("✅ Database initialized")


async def get_db():
    async with AsyncSessionLocal() as session:
        yield session
