"""
Phase 2 — APScheduler scheduled jobs
"""
from core.logger import logger
from core.scheduler_utils import run_crawl_job, run_ai_job


async def job_crawl_tiktok_influencers():
    # 每日抓取各类目 TikTok 热门达人及 GMV 榜单数据。
    async def _do():
        from phase2_influencer.crawlers.influencer_crawler import TikTokInfluencerCrawler
        crawler    = TikTokInfluencerCrawler()
        categories = ["Beauty", "Fashion", "Fitness", "Home", "Tech"]
        total = 0
        for cat in categories:
            influencers = await crawler.search_influencers(category=cat, limit=30)
            gmv_top     = await crawler.get_gmv_leaderboard(category=cat, limit=20)
            total += len(influencers) + len(gmv_top)
        return f"{total} influencers"
    await run_crawl_job("tiktok_influencers", "phase2", "TikTok 达人抓取", _do())


async def job_crawl_youtube_channels():
    # 每日按关键词抓取 YouTube 相关频道数据。
    async def _do():
        from phase2_influencer.crawlers.influencer_crawler import YouTubeCrawler
        crawler  = YouTubeCrawler()
        keywords = ["beauty product review", "unboxing haul", "fitness gadgets", "home gadgets"]
        total = sum(
            len(await crawler.search_channels(keyword=kw, limit=20))
            for kw in keywords
        )
        return f"{total} channels"
    await run_crawl_job("youtube_channels", "phase2", "YouTube 频道抓取", _do())


async def job_ai_influencer_outreach():
    # 每日触发 AI 达人评分和自动招募流程。
    from phase2_influencer.agents.influencer_agent import InfluencerAgent
    await run_ai_job("ai_influencer_outreach", "phase2", "AI 达人招募", InfluencerAgent().run_daily_outreach())


async def job_check_outreach_replies():
    # 定期统计近 7 天内尚未回复的招募记录数量，写入任务日志。
    async def _do():
        from core.database import fetchone
        row = await fetchone("""
            SELECT COUNT(*) as pending
            FROM outreach_records
            WHERE replied = 0
              AND sent_at >= DATE_SUB(NOW(), INTERVAL 7 DAY)
        """)
        pending = row.get("pending", 0) if row else 0
        logger.info(f"[Scheduler] 待回复招募: {pending} 条")
        return f"Pending outreach replies: {pending}"
    await run_crawl_job("check_outreach_replies", "phase2", "检查招募回复", _do())
