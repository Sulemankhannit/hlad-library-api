from fastapi import FastAPI
from app.core.config import settings
from app.api.routes import books,user,request,mock_auth,ledger

app=FastAPI(title=settings.PROJECT_NAME)
@app.get("/")
async def start():
    return {"message":"library online"}

@app.get("/health")
async def check_health():
    return {
        "status":"running",
        "project":settings.PROJECT_NAME,
        "database_configed":bool(settings.DATABASE_URL)
    }
app.include_router(user.router)
app.include_router(books.router)
app.include_router(request.router)
app.include_router(ledger.router)
app.include_router(mock_auth.router)