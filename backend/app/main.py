"""OLC Talent Matching POC -- FastAPI entrypoint."""
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .database import DATABASE_URL, IS_POSTGRES, init_db
from .routers import (
    analytics,
    audit,
    bookings,
    catalog,
    copilot,
    edges,
    export,
    jobs,
    marketing,
    matches,
    reports,
    search,
    stagelync,
    whatif,
)
from .seed import seed_db


@asynccontextmanager
async def lifespan(_: FastAPI):
    init_db()
    seed_db()
    yield


app = FastAPI(
    title="OLC Talent Matching API",
    description="Explainable talent matching POC + executive reports + StageLync discovery",
    version="0.5.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(catalog.router, prefix="/api")
app.include_router(matches.router, prefix="/api")
app.include_router(search.router, prefix="/api")
app.include_router(audit.router, prefix="/api")
app.include_router(whatif.router, prefix="/api")
app.include_router(analytics.router, prefix="/api")
app.include_router(reports.router, prefix="/api")
app.include_router(stagelync.router, prefix="/api")
app.include_router(export.router, prefix="/api")
app.include_router(copilot.router, prefix="/api")
app.include_router(edges.router, prefix="/api")
app.include_router(jobs.router, prefix="/api")
app.include_router(bookings.router, prefix="/api")
app.include_router(marketing.router, prefix="/api")


@app.get("/api/health")
def health():
    return {
        "status": "ok",
        "product": "OLC Talent Matching",
        "database": "postgresql+pgvector" if IS_POSTGRES else "sqlite",
        "database_url_scheme": DATABASE_URL.split("://", 1)[0],
    }
