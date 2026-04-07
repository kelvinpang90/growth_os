"""
Phase 2 — FastAPI Router
"""
from dataclasses import asdict
from typing import Optional

from fastapi import APIRouter, Query, HTTPException
from pydantic import BaseModel

from core.database import fetchall, fetchone, execute
from core.logger import logger
from phase2_influencer.agents.influencer_agent import InfluencerAgent
from phase2_influencer.analyzers.influencer_scorer import batch_score, score_influencer
from phase2_influencer.crawlers.influencer_crawler import (
    TikTokInfluencerCrawler, YouTubeCrawler,
)

router = APIRouter(prefix="/api/phase2", tags=["Phase2 — Influencer Outreach"])


# ── 请求体 ────────────────────────────────────────────────────────────────
class OutreachRequest(BaseModel):
    influencer_db_id: int
    channel: str = "email"        # email / whatsapp / dm
    product_title: str = ""
    product_desc: str = ""
    custom_message: str = ""      # 为空时由 AI 生成


class ScoreRequest(BaseModel):
    influencers: list[dict]
    target_category: str = ""
    top_n: int = 20
    min_score: float = 50.0


# ── 路由 ──────────────────────────────────────────────────────────────────
@router.post("/run-outreach", summary="Trigger AI influencer outreach now")
async def run_outreach(
    keyword: str = "",
    category: str = "",
    platforms: str = "tiktok",
):
    # 立即触发 AI 达人招募流程，完成搜索、评分、发消息并输出报告。
    agent = InfluencerAgent()
    task = (
        f"Please run influencer outreach now.\n"
        f"Search keyword: {keyword or '(follow today recommended products)'}\n"
        f"Category: {category or '(all categories)'}\n"
        f"Platforms: {platforms}\n"
        "Complete scoring, save to database, generate messages, auto-send, and output report."
    )
    result = await agent.run(task, fresh=True)
    return {"status": "ok", "result": result}


@router.get("/influencers", summary="Get influencer list")
async def get_influencers(
    platform:   Optional[str] = Query(None),
    status:     Optional[str] = Query(None, description="discovered/contacted/negotiating/signed"),
    tier:       Optional[str] = Query(None, description="kol/mid/koc/nano"),
    min_score:  float = Query(0.0),
    min_followers: int = Query(0),
    limit:      int   = Query(30),
    offset:     int   = Query(0),
):
    # 按平台、状态、层级、最低评分等条件过滤并分页返回达人列表。
    conditions = ["ai_score >= :min_score", "followers >= :min_followers"]
    params: dict = {"min_score": min_score, "min_followers": min_followers,
                    "limit": limit, "offset": offset}

    if platform:
        conditions.append("platform = :platform")
        params["platform"] = platform
    if status:
        conditions.append("status = :status")
        params["status"] = status

    where = " AND ".join(conditions)
    rows = await fetchall(f"""
        SELECT id, platform, influencer_id, username, display_name,
               followers, avg_views, avg_engagement, gmv_30d, category,
               content_style, commission_rate, contact_email, contact_wa,
               ai_score, status, updated_at
        FROM influencers
        WHERE {where}
        ORDER BY ai_score DESC
        LIMIT :limit OFFSET :offset
    """, params)

    # 前端过滤 tier（数据库无 tier 字段，由 followers 推断）
    if tier:
        tier_ranges = {"kol": (1_000_000, 99_999_999), "mid": (100_000, 999_999),
                       "koc": (10_000, 99_999), "nano": (0, 9_999)}
        lo, hi = tier_ranges.get(tier, (0, 99_999_999))
        rows = [r for r in rows if lo <= r["followers"] <= hi]

    return {"count": len(rows), "data": rows}


@router.get("/influencers/{influencer_db_id}", summary="Get influencer detail")
async def get_influencer_detail(influencer_db_id: int):
    # 获取达人完整档案，同时返回最近 10 条招募历史记录。
    row = await fetchone(
        "SELECT * FROM influencers WHERE id = :id",
        {"id": influencer_db_id},
    )
    if not row:
        raise HTTPException(status_code=404, detail="Influencer not found")

    # 同时返回招募历史
    outreach = await fetchall("""
        SELECT channel, message, sent_at, replied, reply_content, replied_at
        FROM outreach_records WHERE influencer_id = :id ORDER BY sent_at DESC LIMIT 10
    """, {"id": influencer_db_id})

    return {**row, "outreach_history": outreach}


@router.post("/influencers/score", summary="Batch score influencers (no DB write)")
async def score_influencers(req: ScoreRequest):
    # 对传入的达人列表进行批量评分，仅返回结果不写入数据库。
    scores = batch_score(
        req.influencers,
        target_category=req.target_category,
        top_n=req.top_n,
        min_score=req.min_score,
    )
    return {"count": len(scores), "data": [asdict(s) for s in scores]}


@router.post("/outreach/send", summary="Send outreach message to influencer")
async def send_outreach(req: OutreachRequest):
    # 向指定达人发送招募消息（自定义话术或 AI 生成），并记录发送结果。
    inf_row = await fetchone(
        "SELECT * FROM influencers WHERE id = :id",
        {"id": req.influencer_db_id},
    )
    if not inf_row:
        raise HTTPException(status_code=404, detail="Influencer not found")

    recipient = inf_row.get("contact_email" if req.channel == "email" else "contact_wa", "")
    if not recipient:
        raise HTTPException(status_code=400, detail=f"Influencer has no {req.channel} contact")

    # 生成消息（自定义 > AI 生成）
    if req.custom_message:
        message = req.custom_message
    else:
        agent = InfluencerAgent()
        gen   = agent._generate_message({
            "influencer":    dict(inf_row),
            "product_title": req.product_title,
            "product_desc":  req.product_desc,
            "channel":       req.channel,
        })
        message = gen["message"]

    # 发送
    from phase2_influencer.agents.influencer_agent import _send_email, _send_whatsapp
    if req.channel == "email":
        sent = await _send_email(recipient, message)
    elif req.channel == "whatsapp":
        sent = await _send_whatsapp(recipient, message)
    else:
        sent = False

    # 记录
    try:
        await execute("""
            INSERT INTO outreach_records (influencer_id, channel, message, sent_at, replied)
            VALUES (:inf_id, :channel, :msg, NOW(), 0)
        """, {"inf_id": req.influencer_db_id, "channel": req.channel, "msg": message[:3000]})
        if sent:
            await execute(
                "UPDATE influencers SET status = 'contacted', updated_at = NOW() WHERE id = :id",
                {"id": req.influencer_db_id},
            )
    except Exception as e:
        logger.error(f"保存招募记录失败: {e}")

    return {"success": sent, "channel": req.channel, "recipient": recipient, "message": message}


@router.patch("/outreach/{record_id}/reply", summary="Mark influencer reply")
async def mark_replied(record_id: int, reply_content: str = ""):
    # 将指定招募记录标记为已回复，并将达人状态更新为 negotiating。
    await execute("""
        UPDATE outreach_records
        SET replied = 1, reply_content = :content, replied_at = NOW()
        WHERE id = :id
    """, {"id": record_id, "content": reply_content[:3000]})

    # 更新达人状态为 negotiating
    row = await fetchone("SELECT influencer_id FROM outreach_records WHERE id = :id", {"id": record_id})
    if row:
        await execute(
            "UPDATE influencers SET status = 'negotiating', updated_at = NOW() WHERE id = :id",
            {"id": row["influencer_id"]},
        )
    return {"success": True}


@router.patch("/influencers/{influencer_db_id}/status", summary="Update influencer status")
async def update_status(
    influencer_db_id: int,
    status: str = Query(..., description="discovered/contacted/negotiating/signed"),
):
    # 手动更新达人招募状态，验证状态值合法性后写入数据库。
    valid_statuses = {"discovered", "contacted", "negotiating", "signed"}
    if status not in valid_statuses:
        raise HTTPException(status_code=400, detail=f"Invalid status, allowed: {valid_statuses}")
    await execute(
        "UPDATE influencers SET status = :status, updated_at = NOW() WHERE id = :id",
        {"status": status, "id": influencer_db_id},
    )
    return {"success": True, "new_status": status}


@router.get("/pipeline", summary="Influencer recruitment pipeline overview")
async def get_pipeline(
    platform: Optional[str] = Query(None),
    days: int = Query(7),
):
    # 统计各招募阶段达人数量及外发消息的回复率，可按平台过滤。
    params: dict = {"days": days}
    platform_clause = ""
    if platform:
        platform_clause = "AND platform = :platform"
        params["platform"] = platform

    status_rows = await fetchall(f"""
        SELECT status, COUNT(*) as count
        FROM influencers
        WHERE updated_at >= DATE_SUB(NOW(), INTERVAL :days DAY) {platform_clause}
        GROUP BY status
    """, params)

    outreach_row = await fetchone("""
        SELECT COUNT(*) as sent, SUM(replied) as replied
        FROM outreach_records
        WHERE sent_at >= DATE_SUB(NOW(), INTERVAL :days DAY)
    """, {"days": days})

    return {
        "pipeline":          {r["status"]: r["count"] for r in status_rows},
        "outreach_sent":     outreach_row.get("sent", 0) if outreach_row else 0,
        "outreach_replied":  outreach_row.get("replied", 0) if outreach_row else 0,
    }


@router.get("/search-live", summary="Live influencer search (no DB write)")
async def search_live(
    platform:     str = Query("tiktok"),
    keyword:      str = Query(""),
    category:     str = Query(""),
    min_followers: int = Query(10000),
    limit:        int = Query(20),
):
    # 实时调用爬虫搜索达人并返回评分结果，不写入数据库。
    if platform == "tiktok":
        crawler = TikTokInfluencerCrawler()
        influencers = await crawler.search_influencers(
            keyword=keyword, category=category,
            min_followers=min_followers, limit=limit,
        )
    elif platform == "youtube":
        influencers = await YouTubeCrawler().search_channels(
            keyword=keyword or category, min_subscribers=min_followers, limit=limit,
        )
    else:
        raise HTTPException(status_code=400, detail=f"Unsupported platform: {platform}")

    scores = batch_score(influencers, target_category=category, top_n=limit)
    return {"count": len(scores), "data": [asdict(s) for s in scores]}


@router.get("/outreach-records", summary="View outreach message records")
async def get_outreach_records(
    replied:   Optional[int] = Query(None, description="0=unreplied, 1=replied"),
    channel:   Optional[str] = Query(None),
    limit:     int = Query(30),
):
    # 查询招募消息发送记录，支持按回复状态和渠道过滤。
    conditions = []
    params: dict = {"limit": limit}

    if replied is not None:
        conditions.append("r.replied = :replied")
        params["replied"] = replied
    if channel:
        conditions.append("r.channel = :channel")
        params["channel"] = channel

    where = ("WHERE " + " AND ".join(conditions)) if conditions else ""
    rows  = await fetchall(f"""
        SELECT r.id, r.channel, r.message, r.sent_at, r.replied,
               r.reply_content, r.replied_at,
               i.username, i.platform, i.followers, i.ai_score
        FROM outreach_records r
        JOIN influencers i ON i.id = r.influencer_id
        {where}
        ORDER BY r.sent_at DESC LIMIT :limit
    """, params)
    return {"count": len(rows), "data": rows}


@router.get("/task-logs", summary="View scheduled task logs")
async def task_logs(limit: int = 20):
    # 查询 Phase 2 定时任务执行历史，按时间倒序排列。
    rows = await fetchall(
        "SELECT * FROM task_logs WHERE phase = 'phase2' ORDER BY started_at DESC LIMIT :limit",
        {"limit": limit},
    )
    return {"count": len(rows), "data": rows}
