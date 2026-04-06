"""
Phase 2 — APScheduler 定时任务
"""
import asyncio
import time

from core.database import execute
from core.logger import logger

# AI Agent 任务最长允许运行时间（秒）
_AI_TASK_TIMEOUT = 600


async def _log_task(name: str, phase: str, status: str, detail: str, ms: int):
    try:
        await execute(
            "INSERT INTO task_logs (task_name, phase, status, detail, duration_ms) VALUES (:n,:p,:s,:d,:ms)",
            {"n": name, "p": phase, "s": status, "d": detail[:2000], "ms": ms}
        )
    except Exception as e:
        logger.error(f"task_log 写入失败: {e}")


async def job_crawl_tiktok_influencers():
    """每日抓取 TikTok 热门达人 + GMV 榜单"""
    t0 = time.monotonic()
    logger.info("[Scheduler] job_crawl_tiktok_influencers 开始")
    try:
        from phase2_influencer.crawlers.influencer_crawler import TikTokInfluencerCrawler
        crawler = TikTokInfluencerCrawler()
        categories = ["Beauty", "Fashion", "Fitness", "Home", "Tech"]
        total = 0
        for cat in categories:
            influencers = await crawler.search_influencers(category=cat, limit=30)
            gmv_top     = await crawler.get_gmv_leaderboard(category=cat, limit=20)
            total += len(influencers) + len(gmv_top)

        ms = int((time.monotonic() - t0) * 1000)
        await _log_task("tiktok_influencers", "phase2", "success", f"共 {total} 位达人", ms)
        logger.info(f"[Scheduler] TikTok 达人抓取完成: {total} 位 | {ms}ms")
    except Exception as e:
        ms = int((time.monotonic() - t0) * 1000)
        await _log_task("tiktok_influencers", "phase2", "failed", str(e), ms)
        logger.error(f"[Scheduler] TikTok 达人抓取失败: {e}")


async def job_crawl_youtube_channels():
    """每日抓取 YouTube 相关频道"""
    t0 = time.monotonic()
    logger.info("[Scheduler] job_crawl_youtube_channels 开始")
    try:
        from phase2_influencer.crawlers.influencer_crawler import YouTubeCrawler
        crawler  = YouTubeCrawler()
        keywords = ["beauty product review", "unboxing haul", "fitness gadgets", "home gadgets"]
        total    = 0
        for kw in keywords:
            channels = await crawler.search_channels(keyword=kw, limit=20)
            total   += len(channels)

        ms = int((time.monotonic() - t0) * 1000)
        await _log_task("youtube_channels", "phase2", "success", f"共 {total} 个频道", ms)
        logger.info(f"[Scheduler] YouTube 频道抓取完成: {total} 个 | {ms}ms")
    except Exception as e:
        ms = int((time.monotonic() - t0) * 1000)
        await _log_task("youtube_channels", "phase2", "failed", str(e), ms)
        logger.error(f"[Scheduler] YouTube 频道抓取失败: {e}")


async def job_ai_influencer_outreach():
    """每日 AI 达人评分 + 自动招募"""
    t0 = time.monotonic()
    logger.info("[Scheduler] job_ai_influencer_outreach 开始")
    try:
        from phase2_influencer.agents.influencer_agent import InfluencerAgent
        agent  = InfluencerAgent()
        result = await asyncio.wait_for(
            agent.run_daily_outreach(),
            timeout=_AI_TASK_TIMEOUT,
        )
        ms = int((time.monotonic() - t0) * 1000)
        await _log_task("ai_influencer_outreach", "phase2", "success", result[:500], ms)
        logger.info(f"[Scheduler] AI 达人招募完成 | {ms}ms")
    except asyncio.TimeoutError:
        ms = int((time.monotonic() - t0) * 1000)
        await _log_task("ai_influencer_outreach", "phase2", "failed",
                        f"任务超时（>{_AI_TASK_TIMEOUT}s）", ms)
        logger.error(f"[Scheduler] AI 达人招募超时（>{_AI_TASK_TIMEOUT}s），已终止")
    except Exception as e:
        ms = int((time.monotonic() - t0) * 1000)
        await _log_task("ai_influencer_outreach", "phase2", "failed", str(e), ms)
        logger.error(f"[Scheduler] AI 达人招募失败: {e}")


async def job_check_outreach_replies():
    """定期检查招募回复情况，更新达人状态"""
    t0 = time.monotonic()
    logger.info("[Scheduler] job_check_outreach_replies 开始")
    try:
        # 查询最近 7 天内尚未回复的招募记录数量
        from core.database import fetchone
        row = await fetchone("""
            SELECT COUNT(*) as pending
            FROM outreach_records
            WHERE replied = 0
              AND sent_at >= DATE_SUB(NOW(), INTERVAL 7 DAY)
        """)
        pending = row.get("pending", 0) if row else 0
        ms = int((time.monotonic() - t0) * 1000)
        await _log_task("check_outreach_replies", "phase2", "success",
                        f"待回复招募记录: {pending} 条", ms)
        logger.info(f"[Scheduler] 待回复招募: {pending} 条 | {ms}ms")
    except Exception as e:
        ms = int((time.monotonic() - t0) * 1000)
        await _log_task("check_outreach_replies", "phase2", "failed", str(e), ms)
        logger.error(f"[Scheduler] 检查招募回复失败: {e}")
