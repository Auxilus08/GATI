"""
GATI Central Ingestion & Analytics API.
Integrated Command & Control Centre (ICCC) Gateway.
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from config.settings import load_global_settings
from central.api.routers import telemetry, junctions, corridor, analytics

settings = load_global_settings()

app = FastAPI(
    title="GATI - Governance-ready AI Traffic Intelligence Platform",
    description="Central ICCC aggregation, corridor synchronization, and predictive risk analytics API.",
    version="0.1.0",
)

# Enable CORS for React frontend dashboard
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API Routers
app.include_router(telemetry.router, prefix="/api/v1")
app.include_router(junctions.router, prefix="/api/v1")
app.include_router(corridor.router, prefix="/api/v1")
app.include_router(analytics.router, prefix="/api/v1")


@app.get("/")
async def root():
    return {
        "platform": "GATI",
        "description": "Governance-ready AI Traffic Intelligence Platform",
        "city": settings.system.city_name,
        "target_scale": f"{settings.system.target_junction_count} Junctions",
        "status": "ONLINE",
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host=settings.central_api_host, port=settings.central_api_port)
