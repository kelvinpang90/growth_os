"""
Phase 2 — FastAPI 路由
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

router = APIRouter(prefix="/api/phase2", tags=["Phase2 — 达人招募"])


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
@router.post("/run-outreach", summary="立即触发 AI 达人招募分析")
async def run_outreach(
    keyword: str = "",
    category: str = "",
    platforms: str = "tiktok",
):
    agent = InfluencerAgent()
    task = (
        f"请立即执行达人招募任务。\n"
        f"搜索关键词：{keyword or '（跟随今日推荐商品）'}\n"
        f"类目：{category or '（全类目）'}\n"
        f"平台：{platforms}\n"
        "完成评分、保存数据库、生成话术、自动发送，并输出报告。"
    )
    result = await agent.run(task, fresh=True)
    return {"status": "ok", "result": result}


@router.get("/influencers", summary="获取达人列表")
async def get_influencers(
    platform:   Optional[str] = Query(None),
    status:     Optional[str] = Query(None, description="discovered/contacted/negotiating/signed"),
    tier:       Optional[str] = Query(None, description="kol/mid/koc/nano"),
    min_score:  float = Query(0.0),
    min_followers: int = Query(0),
    limit:      int   = Query(30),
    offset:     int   = Query(0),
):
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


@router.get("/influencers/{influencer_db_id}", summary="获取达人详情")
async def get_influencer_detail(influencer_db_id: int):
    row = await fetchone(
        "SELECT * FROM influencers WHERE id = :id",
        {"id": influencer_db_id},
    )
    if not row:
        raise HTTPException(status_code=404, detail="达人不存在")

    # 同时返回招募历史
    outreach = await fetchall("""
        SELECT channel, message, sent_at, replied, reply_content, replied_at
        FROM outreach_records WHERE influencer_id = :id ORDER BY sent_at DESC LIMIT 10
    """, {"id": influencer_db_id})

    return {**row, "outreach_history": outreach}


@router.post("/influencers/score", summary="批量评分达人（不入库）")
async def score_influencers(req: ScoreRequest):
    scores = batch_score(
        req.influencers,
        target_category=req.target_category,
        top_n=req.top_n,
        min_score=req.min_score,
    )
    return {"count": len(scores), "data": [asdict(s) for s in scores]}


@router.post("/outreach/send", summary="向达人发送招募消息")
async def send_outreach(req: OutreachRequest):
    inf_row = await fetchone(
        "SELECT * FROM influencers WHERE id = :id",
        {"id": req.influencer_db_id},
    )
    if not inf_row:
        raise HTTPException(status_code=404, detail="达人不存在")

    recipient = inf_row.get("contact_email" if req.channel == "email" else "contact_wa", "")
    if not recipient:
        raise HTTPException(status_code=400, detail=f"该达人无 {req.channel} 联系方式")

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


@router.patch("/outreach/{record_id}/reply", summary="标记达人已回复")
async def mark_replied(record_id: int, reply_content: str = ""):
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


@router.patch("/influencers/{influencer_db_id}/status", summary="更新达人状态")
async def update_status(
    influencer_db_id: int,
    status: str = Query(..., description="discovered/contacted/negotiating/signed"),
):
    valid_statuses = {"discovered", "contacted", "negotiating", "signed"}
    if status not in valid_statuses:
        raise HTTPException(status_code=400, detail=f"无效状态，可选: {valid_statuses}")
    await execute(
        "UPDATE influencers SET status = :status, updated_at = NOW() WHERE id = :id",
        {"status": status, "id": influencer_db_id},
    )
    return {"success": True, "new_status": status}


@router.get("/pipeline", summary="达人招募管道状态总览")
async def get_pipeline(
    platform: Optional[str] = Query(None),
    days: int = Query(7),
):
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


@router.get("/search-live", summary="实时搜索达人（不入库）")
async def search_live(
    platform:     str = Query("tiktok"),
    keyword:      str = Query(""),
    category:     str = Query(""),
    min_followers: int = Query(10000),
    limit:        int = Query(20),
):
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
        raise HTTPException(status_code=400, detail=f"暂不支持平台: {platform}")

    scores = batch_score(influencers, target_category=category, top_n=limit)
    return {"count": len(scores), "data": [asdict(s) for s in scores]}


@router.get("/outreach-records", summary="查看招募消息记录")
async def get_outreach_records(
    replied:   Optional[int] = Query(None, description="0=未回复, 1=已回复"),
    channel:   Optional[str] = Query(None),
    limit:     int = Query(30),
):
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


@router.get("/task-logs", summary="查看定时任务日志")
async def task_logs(limit: int = 20):
    rows = await fetchall(
        "SELECT * FROM task_logs WHERE phase = 'phase2' ORDER BY started_at DESC LIMIT :limit",
        {"limit": limit},
    )
    return {"count": len(rows), "data": rows}
