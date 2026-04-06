"""
Phase 1 — FastAPI 路由
"""
from dataclasses import asdict
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Query, HTTPException

from core.base_agent import _load_config
from core.database import fetchall, fetchone
from core.i18n import t
from core.logger import logger
from phase1_product_discovery.agents.discovery_agent import DiscoveryAgent
from phase1_product_discovery.analyzers.product_scorer import estimate_profit
from phase1_product_discovery.crawlers.tiktok_crawler        import TikTokCrawler
from phase1_product_discovery.crawlers.google_trends_crawler import GoogleTrendsCrawler

router = APIRouter(prefix="/api/phase1", tags=["Phase1 — 选品发现"])

# ── 从配置文件加载合法平台列表 ─────────────────────────────────────────────
_VALID_PLATFORMS_DISCOVERY: set = set(_load_config("valid_platforms_discovery"))
_VALID_PLATFORMS_PROFIT: set    = set(_load_config("valid_platforms_profit_calculator"))


@router.post("/run-discovery", summary="立即触发 AI 选品分析")
async def run_discovery(category: str = "", platforms: str = "tiktok,amazon,shopee,google"):
    agent = DiscoveryAgent()
    task  = (
        f"Run product discovery now. Category: {category or 'all'}, "
        f"platforms: {platforms}. "
        "Filter products with AI score >= 65, output Top 10 recommendations with launch plans, save to DB."
    )
    result = await agent.run(task, fresh=True)
    return {"status": "ok", "result": result}


@router.get("/recommendations", summary="获取 AI 推荐商品列表")
async def get_recommendations(
    days:      int   = Query(1, ge=1, le=90, description="Look-back window in days"),
    platform:  Optional[str] = Query(None),
    min_score: float = Query(65.0, ge=0, le=100),
    limit:     int   = Query(20, ge=1, le=200),
):
    # 平台参数白名单校验，完全杜绝 SQL 注入风险
    if platform and platform not in _VALID_PLATFORMS_DISCOVERY:
        raise HTTPException(
            status_code=400,
            detail=t("error.invalid_platform", platforms=sorted(_VALID_PLATFORMS_DISCOVERY)),
        )

    params: dict = {"min_score": min_score, "days": days, "limit": limit}

    if platform:
        params["platform"] = platform
        rows = await fetchall("""
            SELECT id, platform, product_id, title, category, price, sales_volume,
                   gmv_estimate, rating, review_count, trend_score, profit_rate,
                   competition, ai_score, ai_analysis, discovered_at
            FROM discovered_products
            WHERE ai_score >= :min_score
              AND discovered_at >= DATE_SUB(NOW(), INTERVAL :days DAY)
              AND platform = :platform
            ORDER BY ai_score DESC
            LIMIT :limit
        """, params)
    else:
        rows = await fetchall("""
            SELECT id, platform, product_id, title, category, price, sales_volume,
                   gmv_estimate, rating, review_count, trend_score, profit_rate,
                   competition, ai_score, ai_analysis, discovered_at
            FROM discovered_products
            WHERE ai_score >= :min_score
              AND discovered_at >= DATE_SUB(NOW(), INTERVAL :days DAY)
            ORDER BY ai_score DESC
            LIMIT :limit
        """, params)

    return {"count": len(rows), "data": rows}


@router.get("/trending-keywords", summary="获取趋势关键词")
async def get_trending_keywords(
    platform: Optional[str] = Query(None),
    limit:    int = Query(30, ge=1, le=200),
):
    if platform and platform not in _VALID_PLATFORMS_DISCOVERY:
        raise HTTPException(
            status_code=400,
            detail=t("error.invalid_platform", platforms=sorted(_VALID_PLATFORMS_DISCOVERY)),
        )

    params: dict = {"limit": limit}
    if platform:
        params["platform"] = platform
        rows = await fetchall(
            "SELECT * FROM trending_keywords WHERE platform = :platform "
            "ORDER BY captured_at DESC LIMIT :limit",
            params,
        )
    else:
        rows = await fetchall(
            "SELECT * FROM trending_keywords ORDER BY captured_at DESC LIMIT :limit",
            params,
        )
    return {"count": len(rows), "data": rows}


@router.post("/profit-calculator", summary="利润率估算")
async def profit_calculator(
    selling_price: float,
    cost_price:    Optional[float] = None,
    platform:      str = "tiktok",
    weight_kg:     float = 0.3,
):
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


@router.get("/tiktok-gmv", summary="今日 TikTok Shop GMV")
async def tiktok_gmv(
    start_date: str = Query(default_factory=lambda: datetime.now().strftime("%Y-%m-%d")),
    end_date:   str = Query(default_factory=lambda: datetime.now().strftime("%Y-%m-%d")),
):
    return await TikTokCrawler().get_shop_gmv(start_date, end_date)


@router.get("/google-trends", summary="Google 趋势关键词（实时抓取）")
async def google_trends_live(geo: str = "US", limit: int = Query(20, ge=1, le=100)):
    kws = await GoogleTrendsCrawler().get_trending_keywords(geo=geo, limit=limit)
    return {"count": len(kws), "data": kws}


@router.get("/google-trends/interest", summary="关键词兴趣趋势曲线")
async def google_trends_interest(
    keywords:  str = Query(..., description="Comma-separated, max 5"),
    geo:       str = Query("US"),
    timeframe: str = Query("today 3-m"),
):
    kw_list = [k.strip() for k in keywords.split(",") if k.strip()][:5]
    if not kw_list:
        raise HTTPException(status_code=400, detail=t("error.min_one_keyword"))
    data = await GoogleTrendsCrawler().get_interest_over_time(kw_list, timeframe, geo)
    return {"keywords": kw_list, "data": data}


@router.get("/task-logs", summary="查看定时任务执行日志")
async def task_logs(phase: str = "phase1", limit: int = Query(20, ge=1, le=100)):
    rows = await fetchall(
        "SELECT * FROM task_logs WHERE phase = :phase ORDER BY started_at DESC LIMIT :limit",
        {"phase": phase, "limit": limit},
    )
    return {"count": len(rows), "data": rows}
