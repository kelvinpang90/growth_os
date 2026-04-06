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

    # ── 公共参数 ──────────────────────────────────────────────────────────
    # max_instances=1  : 同一任务不允许并发运行，防止重叠执行写入重复数据
    # misfire_grace_time: 服务重启后，错过执行窗口在此秒数内仍可补跑
    _common   = {"replace_existing": True, "max_instances": 1}
    _grace_1h = {**_common, "misfire_grace_time": 3600}   # 爬虫任务：补跑窗口 1 小时
    _grace_2h = {**_common, "misfire_grace_time": 7200}   # AI 任务：补跑窗口 2 小时

    # Phase 1 — 每日抓取（UTC+8）
    _scheduler.add_job(job_crawl_tiktok_trending,  CronTrigger(hour=2,  minute=0),  id="tiktok_crawl",           **_grace_1h)
    _scheduler.add_job(job_crawl_amazon_bsr,       CronTrigger(hour=2,  minute=30), id="amazon_crawl",           **_grace_1h)
    _scheduler.add_job(job_crawl_shopee_trending,  CronTrigger(hour=3,  minute=0),  id="shopee_crawl",           **_grace_1h)
    _scheduler.add_job(job_crawl_google_trends,    CronTrigger(hour=3,  minute=30), id="google_crawl",           **_grace_1h)
    _scheduler.add_job(job_ai_discovery_analysis,  CronTrigger(hour=5,  minute=0),  id="ai_analysis",            **_grace_2h)

    # Phase 2 — 达人招募（Phase 1 选品完成后执行）
    _scheduler.add_job(job_crawl_tiktok_influencers, CronTrigger(hour=6,  minute=0),  id="tiktok_influencers",   **_grace_1h)
    _scheduler.add_job(job_crawl_youtube_channels,   CronTrigger(hour=6,  minute=30), id="youtube_channels",     **_grace_1h)
    _scheduler.add_job(job_ai_influencer_outreach,   CronTrigger(hour=7,  minute=0),  id="ai_outreach",          **_grace_2h)
    _scheduler.add_job(job_check_outreach_replies,   CronTrigger(hour=12, minute=0),  id="outreach_reply_check", **_grace_1h)

    logger.info(f"已注册 {len(_scheduler.get_jobs())} 个定时任务")


async def start_scheduler() -> None:
    register_all_jobs()
    _scheduler.start()
    logger.info("定时调度器启动")


async def stop_scheduler() -> None:
    _scheduler.shutdown(wait=False)
    logger.info("定时调度器已停止")
