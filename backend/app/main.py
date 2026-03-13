from fastapi import FastAPI

from app.api.whatsapp import router as whatsapp_router
from app.core.config import settings

app = FastAPI(title=settings.app_name, version="0.1.0")
app.include_router(whatsapp_router)


@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "sage"}
