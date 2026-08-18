"""
GATI Central ICCC API — Application Entry Point.

Deliberately thin: this file only wires together routers and startup hooks.
All business logic lives in the edge/controller/, central/analytics/ modules.
"""
import time
import os
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from config.settings import load_all_junction_configs, load_global_settings
from central.api.state_store import junction_store
from central.api.routers import telemetry, junctions, corridor, analytics, field_override, emergency, safety_events

# ─────────────────────────────────────────────────────────────
# Application lifecycle
# ─────────────────────────────────────────────────────────────
_startup_time: float = time.time()
settings = load_global_settings()
FRONTEND_DIST_DIR = Path(__file__).resolve().parents[2] / "frontend" / "dist"
FRONTEND_INDEX_FILE = FRONTEND_DIST_DIR / "index.html"
SERVE_FRONTEND = os.getenv("VERCEL") == "1"


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Pre-warm JunctionStateStore from all YAML configs on startup."""
    junction_store.prewarm()
    dummy_feed_enabled = await telemetry.start_dummy_telemetry_feed()
    configured = load_all_junction_configs()
    print(
        f"\n[GATI API] Started. "
        f"Pre-warmed {len(junction_store.all_junction_ids())} junction(s) "
        f"({len(configured)} configured). "
        f"City: {settings.system.city_name}. "
        f"Dummy feed: {'enabled' if dummy_feed_enabled else 'disabled'}\n"
    )
    try:
        yield
    finally:
        await telemetry.stop_dummy_telemetry_feed()
        print("[GATI API] Shutting down.")


# ─────────────────────────────────────────────────────────────
# FastAPI application
# ─────────────────────────────────────────────────────────────
app = FastAPI(
    title="GATI — Governance-ready AI Traffic Intelligence Platform",
    description=(
        "Central ICCC data-serving API. "
        "Ingests edge telemetry → runs MaxPressure + Analytics in-process → "
        "serves REST + WebSocket endpoints for the operator dashboard. "
        "Multi-junction: new junction = new YAML in config/junctions/, zero code change."
    ),
    version="0.2.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

# CORS — allow React dashboard and local development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],   # Restrict to dashboard origin in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ─────────────────────────────────────────────────────────────
# Routers
# ─────────────────────────────────────────────────────────────
app.include_router(telemetry.router, prefix="/api/v1")
app.include_router(junctions.router, prefix="/api/v1")
app.include_router(corridor.router, prefix="/api/v1")
app.include_router(analytics.router, prefix="/api/v1")
app.include_router(field_override.router, prefix="/api/v1")
app.include_router(emergency.router, prefix="/api/v1")
app.include_router(safety_events.router, prefix="/api/v1")

if SERVE_FRONTEND and (FRONTEND_DIST_DIR / "assets").exists():
    app.mount(
        "/assets",
        StaticFiles(directory=FRONTEND_DIST_DIR / "assets"),
        name="frontend-assets",
    )


# ─────────────────────────────────────────────────────────────
# Root & Health endpoints
# ─────────────────────────────────────────────────────────────

@app.get("/", tags=["Meta"])
async def root():
    """API root — returns platform identity and live junction count."""
    if SERVE_FRONTEND and FRONTEND_INDEX_FILE.exists():
        return FileResponse(FRONTEND_INDEX_FILE)

    configured = load_all_junction_configs()
    return {
        "platform": "GATI",
        "description": "Governance-ready AI Traffic Intelligence Platform",
        "version": "0.2.0",
        "city": settings.system.city_name,
        "target_scale": f"{settings.system.target_junction_count} Junctions",
        "configured_junctions": len(configured),
        "active_junctions": len(junction_store.all_junction_ids()),
        "docs": "/docs",
        "status": "ONLINE",
    }


@app.get("/health", tags=["Meta"])
@app.get("/api/v1/health", tags=["Meta"])
async def health():
    """Health check endpoint for load-balancer / k8s probes."""
    configured = load_all_junction_configs()
    return {
        "status": "ok",
        "version": "0.2.0",
        "city": settings.system.city_name,
        "active_junctions": len(junction_store.all_junction_ids()),
        "configured_junctions": len(configured),
        "uptime_sec": round(time.time() - _startup_time, 1),
    }


@app.get("/{full_path:path}", include_in_schema=False)
async def serve_frontend(full_path: str):
    """Serve the built React app when Vercel routes frontend paths to FastAPI."""
    if full_path.startswith("api/"):
        raise HTTPException(status_code=404, detail="Not Found")

    if SERVE_FRONTEND and FRONTEND_INDEX_FILE.exists():
        candidate = (FRONTEND_DIST_DIR / full_path).resolve()
        try:
            candidate.relative_to(FRONTEND_DIST_DIR.resolve())
        except ValueError:
            candidate = FRONTEND_INDEX_FILE

        if candidate.is_file():
            return FileResponse(candidate)
        return FileResponse(FRONTEND_INDEX_FILE)

    raise HTTPException(status_code=404, detail="Not Found")


# ─────────────────────────────────────────────────────────────
# Direct execution
# ─────────────────────────────────────────────────────────────
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "central.api.main:app",
        host=settings.central_api_host,
        port=settings.central_api_port,
        reload=True,
        log_level="info",
    )
