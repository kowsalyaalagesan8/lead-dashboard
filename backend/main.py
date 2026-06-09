from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import uvicorn

from routers import leads, whatsapp, messages, analytics, appointments, campaigns,instagram
from database.db import init_db
from routers.facebook_router import router as facebook_router

app = FastAPI(title="Lead Qualification Dashboard API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
    "http://localhost:3000",
    "https://lead-dashboard-3jqn.onrender.com",
    "https://web-leads.onrender.com",
    "https://lead-dashboard-3.onrender.com",
],
    # allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include all routers
app.include_router(leads.router, prefix="/api/leads", tags=["Leads"])
app.include_router(whatsapp.router, prefix="/api/whatsapp", tags=["WhatsApp"])
app.include_router(messages.router, prefix="/api/messages", tags=["Messages"])
app.include_router(analytics.router, prefix="/api/analytics", tags=["Analytics"])
app.include_router(appointments.router, prefix="/api/appointments", tags=["Appointments"])
app.include_router(campaigns.router, prefix="/api/campaigns", tags=["Campaigns"])
app.include_router(instagram.router,    prefix="/api/instagram",    tags=["Instagram"])
app.include_router(facebook_router, prefix="/api/facebook", tags=["Facebook"])
@app.on_event("startup")
async def startup():
    await init_db()

@app.get("/")
async def root():
    return {"message": "Lead Dashboard API Running", "status": "ok"}

@app.get("/health")
async def health():
    return {"status": "healthy"}

if __name__ == "__main__":
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)
