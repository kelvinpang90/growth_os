"""
Shared scheduler utilities — job timing, DB logging, crawl/AI job wrappers
"""
import asyncio
import time

from core.database import execute
from core.logger import logger

# AI Agent 任务最长允许运行时间（秒）
# Claude API 最多 20 轮，每轮约 1–10s，给足裕量
_AI_TASK_TIMEOUT = 600


async def log_task(name: str, phase: str, status: str, detail: str, ms: int) -> None:
    # 将定时任务的执行结果（状态、耗时、详情）写入 task_logs 表。
    try:
        await execute(
            "INSERT INTO task_logs (task_name, phase, status, detail, duration_ms) VALUES (:n,:p,:s,:d,:ms)",
            {"n": name, "p": phase, "s": status, "d": detail[:2000], "ms": ms}
        )
    except Exception as e:
        logger.error(f"task_log 写入失败: {e}")


async def run_crawl_job(job_name: str, phase: str, label: str, coro) -> None:
    # 执行爬虫协程，计时并将成功/失败结果写入任务日志；失败时重新抛出异常。
    t0 = time.monotonic()
    logger.info(f"[Scheduler] {label} 开始")
    try:
        detail = await coro
        ms = int((time.monotonic() - t0) * 1000)
        await log_task(job_name, phase, "success", str(detail), ms)
        logger.info(f"[Scheduler] {label} 完成 | {ms}ms")
    except Exception as e:
        ms = int((time.monotonic() - t0) * 1000)
        await log_task(job_name, phase, "failed", str(e), ms)
        logger.error(f"[Scheduler] {label} 失败: {e}")


async def run_ai_job(job_name: str, phase: str, label: str, coro) -> None:
    # 执行 AI Agent 协程，支持超时控制，并将结果写入任务日志。
    t0 = time.monotonic()
    logger.info(f"[Scheduler] {label} 开始")
    try:
        result = await asyncio.wait_for(coro, timeout=_AI_TASK_TIMEOUT)
        ms = int((time.monotonic() - t0) * 1000)
        await log_task(job_name, phase, "success", str(result)[:500], ms)
        logger.info(f"[Scheduler] {label} 完成 | {ms}ms")
    except asyncio.TimeoutError:
        ms = int((time.monotonic() - t0) * 1000)
        await log_task(job_name, phase, "failed", f"Task timed out (>{_AI_TASK_TIMEOUT}s)", ms)
        logger.error(f"[Scheduler] {label} 超时（>{_AI_TASK_TIMEOUT}s），已终止")
    except Exception as e:
        ms = int((time.monotonic() - t0) * 1000)
        await log_task(job_name, phase, "failed", str(e), ms)
        logger.error(f"[Scheduler] {label} 失败: {e}")
