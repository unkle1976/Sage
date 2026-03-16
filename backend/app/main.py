from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import HTMLResponse

from app.api import whatsapp as whatsapp_module
from app.api import twilio_whatsapp as twilio_whatsapp_module
from app.api.whatsapp import router as whatsapp_router
from app.api.twilio_whatsapp import router as twilio_whatsapp_router
from app.api.eval import router as eval_router
from app.core.config import settings
from app.services.queue import MessageQueue


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: connect the message queue
    queue = MessageQueue(redis_url=settings.redis_url)
    await queue.connect()
    whatsapp_module.message_queue = queue
    twilio_whatsapp_module.message_queue = queue
    yield
    # Shutdown: close the queue connection
    await queue.close()
    whatsapp_module.message_queue = None
    twilio_whatsapp_module.message_queue = None


app = FastAPI(title=settings.app_name, version="0.1.0", lifespan=lifespan)
app.include_router(whatsapp_router)
app.include_router(twilio_whatsapp_router)
app.include_router(eval_router)


@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "sage"}


@app.get("/eval/dashboard", response_class=HTMLResponse)
async def eval_dashboard():
    """Serve the eval dashboard HTML page."""
    dashboard_path = Path(__file__).parent / "eval" / "dashboard.html"
    if not dashboard_path.exists():
        return HTMLResponse("<h1>Dashboard not found</h1>", status_code=404)
    return HTMLResponse(dashboard_path.read_text())
