"""
Phase 1 — APScheduler scheduled jobs
"""
from core.logger import logger
from core.scheduler_utils import run_crawl_job, run_ai_job


async def job_crawl_tiktok_trending():
    # 抓取 TikTok 热销商品和病毒视频，将执行结果记录到任务日志。
    async def _do():
        from phase1_product_discovery.crawlers.tiktok_crawler import TikTokCrawler
        crawler  = TikTokCrawler()
        products = await crawler.get_trending_products(limit=100)
        videos   = await crawler.get_viral_videos(limit=50)
        return f"products:{len(products)}, videos:{len(videos)}"
    await run_crawl_job("tiktok_trending", "phase1", "TikTok 抓取", _do())


async def job_crawl_amazon_bsr():
    # 抓取 Amazon 多品类 BSR 榜单商品，将执行结果记录到任务日志。
    async def _do():
        from phase1_product_discovery.crawlers.amazon_crawler import AmazonCrawler
        crawler = AmazonCrawler()
        cats    = ["beauty", "electronics", "home", "sports"]
        total   = sum(
            len(await crawler.get_bsr_products(cat, limit=30))
            for cat in cats
        )
        return f"{total} products"
    await run_crawl_job("amazon_bsr", "phase1", "Amazon 抓取", _do())


async def job_crawl_shopee_trending():
    # 抓取 Shopee 热销商品列表，将执行结果记录到任务日志。
    async def _do():
        from phase1_product_discovery.crawlers.shopee_crawler import ShopeeCrawler
        products = await ShopeeCrawler().get_trending_products(limit=80)
        return f"{len(products)} products"
    await run_crawl_job("shopee_trending", "phase1", "Shopee 抓取", _do())


async def job_crawl_google_trends():
    # 抓取 Google Trends 热词并写入数据库，将执行结果记录到任务日志。
    async def _do():
        from phase1_product_discovery.crawlers.google_trends_crawler import GoogleTrendsCrawler
        from core.database import execute
        kws = await GoogleTrendsCrawler().get_trending_keywords(limit=30)
        for kw in kws:
            await execute(
                "INSERT INTO trending_keywords (keyword, platform, volume, trend, region) "
                "VALUES (:kw, :pl, :vol, :tr, :geo) ON DUPLICATE KEY UPDATE volume=VALUES(volume)",
                {"kw": kw["keyword"], "pl": "google", "vol": kw.get("volume", 0),
                 "tr": kw.get("trend", "rising"), "geo": kw.get("geo", "US")}
            )
        return f"{len(kws)} keywords"
    await run_crawl_job("google_trends", "phase1", "Google Trends", _do())


async def job_ai_discovery_analysis():
    # 运行 AI 选品分析 Agent，超时后强制终止并记录错误日志。
    from phase1_product_discovery.agents.discovery_agent import DiscoveryAgent
    await run_ai_job("ai_discovery", "phase1", "AI 选品分析", DiscoveryAgent().run_daily_discovery())
