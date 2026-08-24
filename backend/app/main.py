from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.agent.router import router as agent_router
from app.api.router import router
from app.auth.router import organization_router, router as auth_router
from app.core.config import get_settings

settings = get_settings()

app = FastAPI(
    title="Global Automotive KD Intelligence System",
    version="0.2.0",
    description=(
        "Deterministic, version-aware automotive KD customs, tax and profit comparison backend."
    ),
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)
app.include_router(router)
app.include_router(auth_router)
app.include_router(organization_router)
app.include_router(agent_router)


@app.get("/health", tags=["system"])
def health() -> dict[str, str]:
    return {"status": "ok", "environment": settings.environment}
