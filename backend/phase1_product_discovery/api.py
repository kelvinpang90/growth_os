"""
Phase 1 — FastAPI Router
"""
from dataclasses import asdict
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Query, HTTPException

from core.base_agent import _load_config
from core.i18n import t
from phase1_product_discovery.agents.discovery_agent import DiscoveryAgent
from phase1_product_discovery.analyzers.product_scorer import estimate_profit
from phase1_product_discovery.crawlers.tiktok_crawler        import TikTokCrawler
from phase1_product_discovery.crawlers.google_trends_crawler import GoogleTrendsCrawler
from phase1_product_discovery.repositories.product_repository import (
    get_recommendations,
    get_trending_keywords,
    get_task_logs,
)

router = APIRouter(prefix="/api/phase1", tags=["Phase1 — Product Discovery"])

# ── 从配置文件加载合法平台列表 ─────────────────────────────────────────────
_VALID_PLATFORMS_DISCOVERY: set = set(_load_config("valid_platforms_discovery"))
_VALID_PLATFORMS_PROFIT: set    = set(_load_config("valid_platforms_profit_calculator"))


@router.post("/run-discovery", summary="Trigger AI product discovery now")
async def run_discovery(category: str = "", platforms: str = "tiktok,amazon,shopee,google"):
    # 立即触发 AI 选品分析流程，对指定类目和平台执行完整的发现与推荐任务。
    agent = DiscoveryAgent()
    task  = (
        f"Run product discovery now. Category: {category or 'all'}, "
        f"platforms: {platforms}. "
        "Filter products with AI score >= 65, output Top 10 recommendations with launch plans, save to DB."
    )
    result = await agent.run(task, fresh=True)
    return {"status": "ok", "result": result}


@router.get("/recommendations", summary="Get AI-recommended product list")
async def get_recommendations_route(
    days:      int   = Query(1, ge=1, le=90, description="Look-back window in days"),
    platform:  Optional[str] = Query(None),
    min_score: float = Query(65.0, ge=0, le=100),
    limit:     int   = Query(20, ge=1, le=200),
):
    # 查询数据库中 AI 评分满足阈值的推荐商品，支持按平台和时间窗口过滤。
    if platform and platform not in _VALID_PLATFORMS_DISCOVERY:
        raise HTTPException(
            status_code=400,
            detail=t("error.invalid_platform", platforms=sorted(_VALID_PLATFORMS_DISCOVERY)),
        )

    rows = await get_recommendations(
        min_score=min_score,
        days=days,
        limit=limit,
        platform=platform,
    )
    return {"count": len(rows), "data": rows}


@router.get("/trending-keywords", summary="Get trending keywords")
async def get_trending_keywords_route(
    platform: Optional[str] = Query(None),
    limit:    int = Query(30, ge=1, le=200),
):
    # 从数据库获取各平台最新趋势关键词，可按平台筛选。
    if platform and platform not in _VALID_PLATFORMS_DISCOVERY:
        raise HTTPException(
            status_code=400,
            detail=t("error.invalid_platform", platforms=sorted(_VALID_PLATFORMS_DISCOVERY)),
        )

    rows = await get_trending_keywords(limit=limit, platform=platform)
    return {"count": len(rows), "data": rows}


@router.post("/profit-calculator", summary="Profit margin estimator")
async def profit_calculator(
    selling_price: float,
    cost_price:    Optional[float] = None,
    platform:      str = "tiktok",
    weight_kg:     float = 0.3,
):
    # 根据售价、成本和平台计算预估利润率，成本未知时按行业均值估算。
    if selling_price <= 0:
        raise HTTPException(status_code=400, detail=t("error.selling_price_positive"))
    if cost_price is not None and cost_price < 0:
        raise HTTPException(status_code=400, detail=t("error.cost_price_negative"))
    if weight_kg < 0:
        raise HTTPException(status_code=400, detail=t("error.weight_negative"))
    if platform not in _VALID_PLATFORMS_PROFIT:
        raise HTTPException(status_code=400, detail=t("error.unsupported_platform"))

    result = estimate_profit(selling_price, cost_price, platform, weight_kg)
    return asdict(result)


@router.get("/tiktok-gmv", summary="Today's TikTok Shop GMV")
async def tiktok_gmv(
    start_date: str = Query(default_factory=lambda: datetime.now().strftime("%Y-%m-%d")),
    end_date:   str = Query(default_factory=lambda: datetime.now().strftime("%Y-%m-%d")),
):
    # 调用 TikTok Shop 爬虫获取指定日期区间的店铺 GMV 数据。
    return await TikTokCrawler().get_shop_gmv(start_date, end_date)


@router.get("/google-trends", summary="Google trending keywords (live fetch)")
async def google_trends_live(geo: str = "US", limit: int = Query(20, ge=1, le=100)):
    # 实时抓取 Google Trends 热门关键词，按地区过滤。
    kws = await GoogleTrendsCrawler().get_trending_keywords(geo=geo, limit=limit)
    return {"count": len(kws), "data": kws}


@router.get("/google-trends/interest", summary="Keyword interest trend curve")
async def google_trends_interest(
    keywords:  str = Query(..., description="Comma-separated, max 5"),
    geo:       str = Query("US"),
    timeframe: str = Query("today 3-m"),
):
    # 获取最多 5 个关键词在指定时间段和地区内的 Google 搜索兴趣趋势曲线。
    kw_list = [k.strip() for k in keywords.split(",") if k.strip()][:5]
    if not kw_list:
        raise HTTPException(status_code=400, detail=t("error.min_one_keyword"))
    data = await GoogleTrendsCrawler().get_interest_over_time(kw_list, timeframe, geo)
    return {"keywords": kw_list, "data": data}


@router.get("/task-logs", summary="View scheduled task logs")
async def task_logs_route(phase: str = "phase1", limit: int = Query(20, ge=1, le=100)):
    # 查询定时任务执行历史记录，按 phase 和时间倒序排列。
    rows = await get_task_logs(phase=phase, limit=limit)
    return {"count": len(rows), "data": rows}
