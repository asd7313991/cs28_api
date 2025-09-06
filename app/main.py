# app/main.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.db.session import AsyncSessionLocal

from app.routers.lottery import router as lottery_router
from app.routers.user import router as user_router
from app.routers.orders import router as orders_router
import logging, sys

# 启动相关
from app.tasks.scheduler import start_scheduler
from app.services.bootstrap_service import (
    init_db,
    ensure_default_lottery,
    warmup_redis_from_db,
)

app = FastAPI(
    title=settings.APP_NAME,
    version=getattr(settings, "APP_VERSION", "0.1.0"),
    docs_url="/docs",
    redoc_url="/redoc",
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],         # 需要限制域名时改这里
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
logging.basicConfig(
    level=logging.WARNING,  # 根日志级别
    format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)

# 静音/降噪具体 logger
logging.getLogger("uvicorn").setLevel(logging.WARNING)
logging.getLogger("uvicorn.error").setLevel(logging.WARNING)
logging.getLogger("uvicorn.access").setLevel(logging.CRITICAL)  # 彻底关掉访问日志

logging.getLogger("apscheduler").setLevel(logging.ERROR)        # 只保留错误，不要 WARNING

# 保留你自己的结算成功日志
logging.getLogger("app.tasks.settlement").setLevel(logging.INFO)

# ✅ 注册路由（这里不再额外加 prefix，避免出现 /api/api/...）
app.include_router(lottery_router)
app.include_router(user_router)
app.include_router(orders_router)

# 启动初始化
@app.on_event("startup")
async def on_startup() -> None:
    await init_db()
    async with AsyncSessionLocal() as session:
        lot = await ensure_default_lottery(session)
        # 预热最近 200 条到 Redis
        await warmup_redis_from_db(session, lot.code, limit=200)
    # 启动调度器（定时采集/结算等任务）
    start_scheduler()

# 健康检查
@app.get("/ping")
async def ping():
    return {"ok": True, "env": settings.APP_ENV}

# 也可以提供 kubernetes/监控用探针
@app.get("/healthz")
async def healthz():
    return {"status": "healthy"}
