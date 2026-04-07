"""
AI Growth OS — FastAPI entry point
Integrates all Phase 1–5 modules
"""
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from core.database import init_db, close_db
from core.i18n.middleware import LocaleMiddleware
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
    # 应用生命周期管理：启动时初始化数据库和调度器，关闭时优雅停止。
    logger.info("AI Growth OS 启动中...")
    await init_db()
    await start_scheduler()
    logger.info("系统就绪 ✓  访问 http://localhost:8000/docs 查看 API 文档")
    yield
    await stop_scheduler()
    await close_db()
    logger.info("AI Growth OS 已关闭")


app = FastAPI(
    title="AI Growth OS — Cross-border E-commerce Growth Operating System",
    description=(
        "**Phase 1**: AI Product Discovery  \n"
        "**Phase 2**: AI Influencer Outreach Agent  \n"
        "**Phase 3**: Product Listing + Multi-platform Sync  \n"
        "**Phase 4**: AI Customer Service + After-sales Automation  \n"
        "**Phase 5**: Boss Dashboard"
    ),
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(LocaleMiddleware)
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
    # 返回系统概览，包含各 Phase 的名称和主要接口路径。
    return {
        "system": "AI Growth OS",
        "version": "1.0.0",
        "phases": {
            "phase1": {"name": "AI Product Discovery",    "endpoints": ["/api/phase1/run-discovery", "/api/phase1/recommendations"]},
            "phase2": {"name": "Influencer Outreach",     "endpoints": ["/api/phase2/run-outreach",  "/api/phase2/influencers"]},
            "phase3": {"name": "Multi-platform Listing",  "endpoints": ["/api/phase3/sync-product",  "/api/phase3/listings"]},
            "phase4": {"name": "AI Customer Service",     "endpoints": ["/api/phase4/ticket",         "/api/phase4/tickets"]},
            "phase5": {"name": "Boss Dashboard",          "endpoints": ["/api/phase5/dashboard",      "/api/phase5/insights"]},
        },
        "docs": "/docs",
        "health": "/health",
    }


@app.get("/health", tags=["System"])
async def health():
    # 健康检查接口，返回服务运行状态。
    return {"status": "ok"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
