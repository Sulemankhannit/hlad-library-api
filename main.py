from fastapi import FastAPI
from app.core.congfig import settings
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