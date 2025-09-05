from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.db.session import AsyncSessionLocal
from app.routers.lottery import router as lottery_router
from app.routers.user import router as user_router
from app.routers.orders import router as orders_router
from app.tasks.scheduler import start_scheduler
from app.services.bootstrap_service import init_db, ensure_default_lottery, warmup_redis_from_db

app = FastAPI(title=settings.APP_NAME)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"]
)

app.include_router(lottery_router)
app.include_router(user_router)
app.include_router(orders_router)

@app.on_event("startup")
async def on_startup():
    await init_db()
    async with AsyncSessionLocal() as session:
        lot = await ensure_default_lottery(session)
        await warmup_redis_from_db(session, lot.code, limit=200)
    start_scheduler()

@app.get("/ping")
async def ping():
    return {"ok": True, "env": settings.APP_ENV}
