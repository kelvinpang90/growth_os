"""
定时任务调度器 — APScheduler AsyncIO
"""
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from core.logger import logger

_scheduler = AsyncIOScheduler(timezone="Asia/Shanghai")


def get_scheduler() -> AsyncIOScheduler:
    return _scheduler


def register_all_jobs() -> None:
    """注册所有 Phase 定时任务"""
    from phase1_product_discovery.scheduler_jobs import (
        job_crawl_tiktok_trending,
        job_crawl_amazon_bsr,
        job_crawl_shopee_trending,
        job_crawl_google_trends,
        job_ai_discovery_analysis,
    )
    from phase2_influencer.scheduler_jobs import (
        job_crawl_tiktok_influencers,
        job_crawl_youtube_channels,
        job_ai_influencer_outreach,
        job_check_outreach_replies,
    )

    # Phase 1 — 每日抓取（UTC+8）
    _scheduler.add_job(job_crawl_tiktok_trending,  CronTrigger(hour=2,  minute=0),  id="tiktok_crawl",          replace_existing=True)
    _scheduler.add_job(job_crawl_amazon_bsr,       CronTrigger(hour=2,  minute=30), id="amazon_crawl",          replace_existing=True)
    _scheduler.add_job(job_crawl_shopee_trending,  CronTrigger(hour=3,  minute=0),  id="shopee_crawl",          replace_existing=True)
    _scheduler.add_job(job_crawl_google_trends,    CronTrigger(hour=3,  minute=30), id="google_crawl",          replace_existing=True)
    _scheduler.add_job(job_ai_discovery_analysis,  CronTrigger(hour=5,  minute=0),  id="ai_analysis",           replace_existing=True)

    # Phase 2 — 达人招募（Phase 1 选品完成后执行）
    _scheduler.add_job(job_crawl_tiktok_influencers, CronTrigger(hour=6,  minute=0),  id="tiktok_influencers",  replace_existing=True)
    _scheduler.add_job(job_crawl_youtube_channels,   CronTrigger(hour=6,  minute=30), id="youtube_channels",    replace_existing=True)
    _scheduler.add_job(job_ai_influencer_outreach,   CronTrigger(hour=7,  minute=0),  id="ai_outreach",         replace_existing=True)
    _scheduler.add_job(job_check_outreach_replies,   CronTrigger(hour=12, minute=0),  id="outreach_reply_check", replace_existing=True)

    logger.info(f"已注册 {len(_scheduler.get_jobs())} 个定时任务")


async def start_scheduler() -> None:
    register_all_jobs()
    _scheduler.start()
    logger.info("定时调度器启动")


async def stop_scheduler() -> None:
    _scheduler.shutdown(wait=False)
    logger.info("定时调度器已停止")
