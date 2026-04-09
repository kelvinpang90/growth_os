"""
Influencer Repository — all SQL for influencers, outreach_records, task_logs.
"""
from typing import Optional

from core.database import execute, fetchall, fetchone


_TIER_RANGES = {
    "kol":  (1_000_000, 99_999_999),
    "mid":  (100_000,   999_999),
    "koc":  (10_000,    99_999),
    "nano": (0,         9_999),
}


async def list_influencers(
    min_score: float,
    min_followers: int,
    limit: int,
    offset: int,
    platform: Optional[str] = None,
    status: Optional[str] = None,
    category: Optional[str] = None,
    tier: Optional[str] = None,
) -> list[dict]:
    conditions = ["ai_score >= :min_score", "followers >= :min_followers"]
    params: dict = {
        "min_score": min_score,
        "min_followers": min_followers,
        "limit": limit,
        "offset": offset,
    }

    if platform:
        conditions.append("platform = :platform")
        params["platform"] = platform
    if status:
        conditions.append("status = :status")
        params["status"] = status
    if category:
        conditions.append("category = :category")
        params["category"] = category
    if tier and tier in _TIER_RANGES:
        lo, hi = _TIER_RANGES[tier]
        conditions.append("followers BETWEEN :tier_lo AND :tier_hi")
        params["tier_lo"] = lo
        params["tier_hi"] = hi

    where = " AND ".join(conditions)
    return await fetchall(
        f"""
        SELECT id, platform, influencer_id, username, display_name,
               followers, avg_views, avg_engagement, gmv_30d, category,
               content_style, commission_rate, contact_email, contact_wa,
               ai_score, status, updated_at
        FROM influencers
        WHERE {where}
        ORDER BY ai_score DESC
        LIMIT :limit OFFSET :offset
        """,
        params,
    )


async def get_influencer_by_id(influencer_db_id: int) -> dict | None:
    return await fetchone(
        "SELECT * FROM influencers WHERE id = :id",
        {"id": influencer_db_id},
    )


async def get_outreach_history(influencer_db_id: int) -> list[dict]:
    return await fetchall(
        """
        SELECT channel, message, sent_at, replied, reply_content, replied_at
        FROM outreach_records WHERE influencer_id = :id ORDER BY sent_at DESC LIMIT 10
        """,
        {"id": influencer_db_id},
    )


async def insert_outreach_record(influencer_id: int, channel: str, message: str) -> None:
    await execute(
        """
        INSERT INTO outreach_records (influencer_id, channel, message, sent_at, replied)
        VALUES (:inf_id, :channel, :msg, NOW(), 0)
        """,
        {"inf_id": influencer_id, "channel": channel, "msg": message[:3000]},
    )


async def set_influencer_contacted(influencer_db_id: int) -> None:
    await execute(
        "UPDATE influencers SET status = 'contacted', updated_at = NOW() WHERE id = :id",
        {"id": influencer_db_id},
    )


async def mark_outreach_replied(record_id: int, reply_content: str) -> None:
    await execute(
        """
        UPDATE outreach_records
        SET replied = 1, reply_content = :content, replied_at = NOW()
        WHERE id = :id
        """,
        {"id": record_id, "content": reply_content[:3000]},
    )


async def get_outreach_record_influencer_id(record_id: int) -> dict | None:
    return await fetchone(
        "SELECT influencer_id FROM outreach_records WHERE id = :id",
        {"id": record_id},
    )


async def update_influencer_status(influencer_db_id: int, status: str) -> None:
    await execute(
        "UPDATE influencers SET status = :status, updated_at = NOW() WHERE id = :id",
        {"status": status, "id": influencer_db_id},
    )


async def get_pipeline_status_counts(days: int, platform: Optional[str] = None) -> list[dict]:
    params: dict = {"days": days}
    platform_clause = ""
    if platform:
        platform_clause = "AND platform = :platform"
        params["platform"] = platform
    return await fetchall(
        f"""
        SELECT status, COUNT(*) as count
        FROM influencers
        WHERE updated_at >= DATE_SUB(NOW(), INTERVAL :days DAY) {platform_clause}
        GROUP BY status
        """,
        params,
    )


async def get_outreach_summary(days: int) -> dict | None:
    return await fetchone(
        """
        SELECT COUNT(*) as sent, SUM(replied) as replied
        FROM outreach_records
        WHERE sent_at >= DATE_SUB(NOW(), INTERVAL :days DAY)
        """,
        {"days": days},
    )


async def get_outreach_records(
    limit: int,
    replied: Optional[int] = None,
    channel: Optional[str] = None,
) -> list[dict]:
    conditions: list[str] = []
    params: dict = {"limit": limit}

    if replied is not None:
        conditions.append("r.replied = :replied")
        params["replied"] = replied
    if channel:
        conditions.append("r.channel = :channel")
        params["channel"] = channel

    where = ("WHERE " + " AND ".join(conditions)) if conditions else ""
    return await fetchall(
        f"""
        SELECT r.id, r.channel, r.message, r.sent_at, r.replied,
               r.reply_content, r.replied_at,
               i.username, i.platform, i.followers, i.ai_score
        FROM outreach_records r
        JOIN influencers i ON i.id = r.influencer_id
        {where}
        ORDER BY r.sent_at DESC LIMIT :limit
        """,
        params,
    )


async def get_task_logs(limit: int) -> list[dict]:
    return await fetchall(
        "SELECT * FROM task_logs WHERE phase = 'phase2' ORDER BY started_at DESC LIMIT :limit",
        {"limit": limit},
    )
