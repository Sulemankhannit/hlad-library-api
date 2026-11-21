from fastapi import FastAPI
from app.core.config import settings
from app.api.routes import books, user, request, ledger, admin

is_prod = settings.ENVIRONMENT.lower() == "production"

app = FastAPI(
    title=settings.PROJECT_NAME,
    docs_url=None if is_prod else "/docs",
    redoc_url=None if is_prod else "/redoc",
    openapi_url=None if is_prod else "/openapi.json",
)

@app.get("/")
async def start():
    return {"message": "library online"}

@app.get("/health")
async def check_health():
    return {
        "status": "running",
        "project": settings.PROJECT_NAME,
        "environment": settings.ENVIRONMENT,
        "database_configed": bool(settings.DATABASE_URL),
    }

# Core production routers
app.include_router(user.router)
app.include_router(books.router)
app.include_router(request.router)
app.include_router(ledger.router)
app.include_router(admin.router)

# Mock Authentication ONLY available in non-production environments
if not is_prod:
    from app.api.routes import mock_auth
    app.include_router(mock_auth.router)
