"""
AI Growth OS — FastAPI 主入口
整合 Phase 1-5 所有模块
"""
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from core.database import init_db, close_db
from core.scheduler import start_scheduler, stop_scheduler
from core.logger import logger

from core.auth.router            import router as auth_router
from phase1_product_discovery.api import router as phase1_router
from phase2_influencer.api        import router as phase2_router
# from phase3_listing.api           import router as phase3_router
# from phase4_customer_service.api  import router as phase4_router
# from phase5_dashboard.dashboard   import router as phase5_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("AI Growth OS 启动中...")
    await init_db()
    await start_scheduler()
    logger.info("系统就绪 ✓  访问 http://localhost:8000/docs 查看 API 文档")
    yield
    await stop_scheduler()
    await close_db()
    logger.info("AI Growth OS 已关闭")


app = FastAPI(
    title="AI Growth OS — 跨境电商增长操作系统",
    description=(
        "**Phase 1**: AI 选品 + 爆品发现  \n"
        "**Phase 2**: AI 达人开发 Agent  \n"
        "**Phase 3**: 商品发布 + 多平台同步  \n"
        "**Phase 4**: AI 客服 + 售后自动化  \n"
        "**Phase 5**: 老板驾驶舱"
    ),
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router)
app.include_router(phase1_router)
app.include_router(phase2_router)
# app.include_router(phase3_router)
# app.include_router(phase4_router)
# app.include_router(phase5_router)


@app.get("/", tags=["System"])
async def root():
    return {
        "system": "AI Growth OS",
        "version": "1.0.0",
        "phases": {
            "phase1": {"name": "AI 选品发现", "endpoints": ["/api/phase1/run-discovery", "/api/phase1/recommendations"]},
            "phase2": {"name": "达人开发",    "endpoints": ["/api/phase2/run-outreach",  "/api/phase2/influencers"]},
            "phase3": {"name": "多平台发品",   "endpoints": ["/api/phase3/sync-product",  "/api/phase3/listings"]},
            "phase4": {"name": "AI 客服",     "endpoints": ["/api/phase4/ticket",         "/api/phase4/tickets"]},
            "phase5": {"name": "老板驾驶舱",   "endpoints": ["/api/phase5/dashboard",      "/api/phase5/insights"]},
        },
        "docs": "/docs",
        "health": "/health",
    }


@app.get("/health", tags=["System"])
async def health():
    return {"status": "ok"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
