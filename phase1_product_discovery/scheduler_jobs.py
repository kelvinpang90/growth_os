"""
Phase 1 — APScheduler 定时任务
"""
import time

from core.database import execute
from core.logger import logger


async def _log_task(name: str, phase: str, status: str, detail: str, ms: int):
    try:
        await execute(
            "INSERT INTO task_logs (task_name, phase, status, detail, duration_ms) VALUES (:n,:p,:s,:d,:ms)",
            {"n": name, "p": phase, "s": status, "d": detail[:2000], "ms": ms}
        )
    except Exception as e:
        logger.error(f"task_log 写入失败: {e}")


async def job_crawl_tiktok_trending():
    t0 = time.monotonic()
    logger.info("[Scheduler] job_crawl_tiktok_trending 开始")
    try:
        from phase1_product_discovery.crawlers.tiktok_crawler import TikTokCrawler
        crawler  = TikTokCrawler()
        products = await crawler.get_trending_products(limit=100)
        videos   = await crawler.get_viral_videos(limit=50)
        ms = int((time.monotonic() - t0) * 1000)
        await _log_task("tiktok_trending", "phase1", "success",
                        f"商品:{len(products)}, 视频:{len(videos)}", ms)
        logger.info(f"[Scheduler] TikTok 抓取完成: {len(products)} 商品 | {ms}ms")
    except Exception as e:
        ms = int((time.monotonic() - t0) * 1000)
        await _log_task("tiktok_trending", "phase1", "failed", str(e), ms)
        logger.error(f"[Scheduler] TikTok 抓取失败: {e}")


async def job_crawl_amazon_bsr():
    t0 = time.monotonic()
    logger.info("[Scheduler] job_crawl_amazon_bsr 开始")
    try:
        from phase1_product_discovery.crawlers.amazon_crawler import AmazonCrawler
        crawler = AmazonCrawler()
        cats    = ["beauty", "electronics", "home", "sports"]
        total   = 0
        for cat in cats:
            products = await crawler.get_bsr_products(cat, limit=30)
            total   += len(products)
        ms = int((time.monotonic() - t0) * 1000)
        await _log_task("amazon_bsr", "phase1", "success", f"共 {total} 商品", ms)
        logger.info(f"[Scheduler] Amazon 抓取完成: {total} 商品 | {ms}ms")
    except Exception as e:
        ms = int((time.monotonic() - t0) * 1000)
        await _log_task("amazon_bsr", "phase1", "failed", str(e), ms)
        logger.error(f"[Scheduler] Amazon 抓取失败: {e}")


async def job_crawl_shopee_trending():
    t0 = time.monotonic()
    logger.info("[Scheduler] job_crawl_shopee_trending 开始")
    try:
        from phase1_product_discovery.crawlers.shopee_crawler import ShopeeCrawler
        products = await ShopeeCrawler().get_trending_products(limit=80)
        ms = int((time.monotonic() - t0) * 1000)
        await _log_task("shopee_trending", "phase1", "success", f"{len(products)} 商品", ms)
        logger.info(f"[Scheduler] Shopee 抓取完成: {len(products)} 商品 | {ms}ms")
    except Exception as e:
        ms = int((time.monotonic() - t0) * 1000)
        await _log_task("shopee_trending", "phase1", "failed", str(e), ms)
        logger.error(f"[Scheduler] Shopee 抓取失败: {e}")


async def job_crawl_google_trends():
    t0 = time.monotonic()
    logger.info("[Scheduler] job_crawl_google_trends 开始")
    try:
        from phase1_product_discovery.crawlers.google_trends_crawler import GoogleTrendsCrawler
        kws = await GoogleTrendsCrawler().get_trending_keywords(limit=30)
        for kw in kws:
            await execute(
                "INSERT INTO trending_keywords (keyword, platform, volume, trend, region) "
                "VALUES (:kw, :pl, :vol, :tr, :geo) ON DUPLICATE KEY UPDATE volume=VALUES(volume)",
                {"kw": kw["keyword"], "pl": "google", "vol": kw.get("volume", 0),
                 "tr": kw.get("trend", "rising"), "geo": kw.get("geo", "US")}
            )
        ms = int((time.monotonic() - t0) * 1000)
        await _log_task("google_trends", "phase1", "success", f"{len(kws)} 关键词", ms)
        logger.info(f"[Scheduler] Google Trends 完成: {len(kws)} 关键词 | {ms}ms")
    except Exception as e:
        ms = int((time.monotonic() - t0) * 1000)
        await _log_task("google_trends", "phase1", "failed", str(e), ms)
        logger.error(f"[Scheduler] Google Trends 失败: {e}")


async def job_ai_discovery_analysis():
    t0 = time.monotonic()
    logger.info("[Scheduler] job_ai_discovery_analysis 开始")
    try:
        from phase1_product_discovery.agents.discovery_agent import DiscoveryAgent
        agent  = DiscoveryAgent()
        result = await agent.run_daily_discovery()
        ms     = int((time.monotonic() - t0) * 1000)
        await _log_task("ai_discovery", "phase1", "success", result[:500], ms)
        logger.info(f"[Scheduler] AI 选品分析完成 | {ms}ms")
    except Exception as e:
        ms = int((time.monotonic() - t0) * 1000)
        await _log_task("ai_discovery", "phase1", "failed", str(e), ms)
        logger.error(f"[Scheduler] AI 选品分析失败: {e}")
