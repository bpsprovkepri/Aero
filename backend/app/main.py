"""
Aero — Flight Price Scraper API

FastAPI application entry point.
"""

from contextlib import asynccontextmanager
import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.database import engine, Base
from app.routers import flights, auth, stats, settings, notifications, scheduler, routes
from app.models.user import User  # noqa: ensure users table is created
from app.models.token_blacklist import TokenBlacklist  # noqa: ensure blacklist table is created
from app.models.route import Route  # noqa: ensure routes table is created
from app.services.scheduler import start_scheduler, stop_scheduler

logging.basicConfig(level=logging.INFO)


def _seed_default_routes():
    """Seed default routes if routes table is empty."""
    from app.database import SessionLocal
    from app.models.route import Route, INDONESIA_AIRPORTS
    db = SessionLocal()
    try:
        if db.query(Route).count() == 0:
            defaults = [
                ("BTH", "CGK"), ("BTH", "KNO"), ("BTH", "SUB"),
                ("BTH", "PDG"), ("TNJ", "CGK"),
            ]
            for origin, dest in defaults:
                db.add(Route(
                    origin=origin, destination=dest,
                    origin_city=INDONESIA_AIRPORTS.get(origin, ""),
                    destination_city=INDONESIA_AIRPORTS.get(dest, ""),
                ))
            db.commit()
            logging.getLogger("aero").info("Seeded %d default routes.", len(defaults))
    finally:
        db.close()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Create tables on startup, seed data, start scheduler."""
    Base.metadata.create_all(bind=engine)
    _seed_default_routes()
    start_scheduler()
    yield
    stop_scheduler()


app = FastAPI(
    title="Aero — Flight Price Scraper API",
    description="Scraper harga tiket pesawat dari berbagai sumber API untuk rute domestik Indonesia.",
    version="1.0.0",
    lifespan=lifespan,
)

import os

# CORS — allow localhost + VPS IP
_vps_ip = os.getenv("VPS_IP", "")
_allowed_origins = [
    "http://localhost:3000",
    "http://localhost:8097",
    "https://aero.gurind.am",  # ✅ production domain
]

if _vps_ip:
    _allowed_origins.append(f"http://{_vps_ip}:3000")
    _allowed_origins.append(f"http://{_vps_ip}:8097")

app.add_middleware(
    CORSMiddleware,
    allow_origins=_allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routers
app.include_router(auth.router)
app.include_router(flights.router)
app.include_router(stats.router)
app.include_router(settings.router)
app.include_router(notifications.router)
app.include_router(scheduler.router)
app.include_router(routes.router)


@app.get("/")
def root():
    return {
        "app": "Aero Flight Price Scraper",
        "version": "1.0.0",
        "docs": "/docs",
    }
