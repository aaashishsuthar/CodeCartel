from fastapi import FastAPI, Request, HTTPException, status
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware

from .database import engine, Base
from .api import health, projects, metrics, ingestion, audits, vendors, evidence, reports, auth, harvester, esakshi, cleaner, scraper, interceptor
from .services.scheduler import scheduler_daemon
from .config import settings
from .models import project, ingestion as ingestion_model, audit as audit_model, user as user_model

# Create database tables
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title=settings.APP_NAME,
    description="Autonomous Forensic Intelligence Suite - Agent Kautilya Backend API",
    version="1.0.0"
)

# CORS Middleware to support Streamlit and frontend clients
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Centralized Exception Handlers for API Hardening
@app.exception_handler(HTTPException)
async def custom_http_exception_handler(request: Request, exc: HTTPException):
    return JSONResponse(
        status_code=exc.status_code,
        headers=getattr(exc, "headers", None),
        content={
            "success": False,
            "detail": exc.detail,
            "error": {
                "status_code": exc.status_code,
                "message": str(exc.detail)
            }
        }
    )

@app.exception_handler(RequestValidationError)
async def custom_validation_exception_handler(request: Request, exc: RequestValidationError):
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "success": False,
            "detail": "Input validation error",
            "error": {
                "status_code": 422,
                "message": "Invalid request parameters or payload",
                "details": exc.errors()
            }
        }
    )

# Routers
app.include_router(auth.router, prefix="/api/auth", tags=["auth"])
app.include_router(health.router, prefix="/api", tags=["health"])
app.include_router(projects.router, prefix="/api", tags=["projects"])
app.include_router(metrics.router, prefix="/api", tags=["metrics"])
app.include_router(ingestion.router, prefix="/api", tags=["ingestion"])
app.include_router(audits.router, prefix="/api/audits", tags=["audits"])
app.include_router(vendors.router, prefix="/api/vendors", tags=["vendors"])
app.include_router(evidence.router, prefix="/api/evidence", tags=["evidence"])
app.include_router(reports.router, prefix="/api/reports", tags=["reports"])
app.include_router(harvester.router, prefix="/api/harvester", tags=["harvester"])
app.include_router(esakshi.router, prefix="/api/esakshi", tags=["esakshi"])
app.include_router(cleaner.router, prefix="/api/cleaner", tags=["cleaner"])
app.include_router(scraper.router, prefix="/api/scraper", tags=["scraper"])
app.include_router(interceptor.router, prefix="/api/interceptor", tags=["interceptor"])

@app.on_event("startup")
def startup_scheduler():
    scheduler_daemon.start()

@app.on_event("shutdown")
def shutdown_scheduler():
    scheduler_daemon.stop()

@app.get("/")
def read_root():
    return {
        "service": "Agent Kautilya Backend API",
        "status": "online",
        "docs_url": "/docs"
    }
