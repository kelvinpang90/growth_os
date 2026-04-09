"""
Product Repository — all SQL for discovered_products, trending_keywords, task_logs.
"""
from typing import Optional

from core.database import fetchall


async def get_recommendations(
    min_score: float,
    days: int,
    limit: int,
    platform: Optional[str] = None,
) -> list[dict]:
    params: dict = {"min_score": min_score, "days": days, "limit": limit}
    if platform:
        params["platform"] = platform
        return await fetchall(
            """
            SELECT id, platform, title, category, price, sales_volume,
                   gmv_estimate, rating, review, trend_score, profit_rate,
                   competition, ai_score, ai_analysis, discovered_at
            FROM discovered_products
            WHERE ai_score >= :min_score
              AND discovered_at >= DATE_SUB(NOW(), INTERVAL :days DAY)
              AND platform = :platform
            ORDER BY ai_score DESC
            LIMIT :limit
            """,
            params,
        )
    return await fetchall(
        """
        SELECT id, platform, title, category, price, sales_volume,
                   gmv_estimate, rating, review, trend_score, profit_rate,
                   competition, ai_score, ai_analysis, discovered_at
        FROM discovered_products
        WHERE ai_score >= :min_score
          AND discovered_at >= DATE_SUB(NOW(), INTERVAL :days DAY)
        ORDER BY ai_score DESC
        LIMIT :limit
        """,
        params,
    )


async def get_trending_keywords(
    limit: int,
    platform: Optional[str] = None,
) -> list[dict]:
    params: dict = {"limit": limit}
    if platform:
        params["platform"] = platform
        return await fetchall(
            "SELECT * FROM trending_keywords WHERE platform = :platform "
            "ORDER BY captured_at DESC LIMIT :limit",
            params,
        )
    return await fetchall(
        "SELECT * FROM trending_keywords ORDER BY captured_at DESC LIMIT :limit",
        params,
    )


async def get_task_logs(phase: str, limit: int) -> list[dict]:
    return await fetchall(
        "SELECT * FROM task_logs WHERE phase = :phase ORDER BY started_at DESC LIMIT :limit",
        {"phase": phase, "limit": limit},
    )
