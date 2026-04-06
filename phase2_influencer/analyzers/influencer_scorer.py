"""
Phase 2 — 达人综合评分模型
维度：互动率 / GMV 带货力 / 粉丝质量 / 类目匹配度 / 内容活跃度
"""
from dataclasses import dataclass
from typing import Optional


# ── 达人分级定义 ──────────────────────────────────────────────────────────
INFLUENCER_TIERS = {
    "kol":  {"min": 1_000_000, "label": "KOL (Top-Tier)",            "commission_range": (8,  20)},
    "mid":  {"min": 100_000,   "label": "Mid-Tier",                  "commission_range": (10, 25)},
    "koc":  {"min": 10_000,    "label": "KOC (Key Opinion Consumer)", "commission_range": (15, 30)},
    "nano": {"min": 0,         "label": "Nano Influencer",            "commission_range": (15, 35)},
}

# 各平台平均互动率基准（用于相对评分）
PLATFORM_ER_BENCHMARK = {
    "tiktok":    3.0,
    "youtube":   4.0,
    "instagram": 2.5,
}


@dataclass
class InfluencerScore:
    influencer_id:        str
    platform:             str
    username:             str
    tier:                 str    # kol / mid / koc / nano
    tier_label:           str
    followers:            int
    er_score:             float  # 互动率评分 0-100
    gmv_score:            float  # 带货力评分 0-100
    audience_score:       float  # 粉丝质量评分 0-100
    activity_score:       float  # 内容活跃度评分 0-100
    ai_score:             float  # 综合 AI 评分 0-100
    contact_available:    bool
    recommended_commission: str
    verdict:              str
    outreach_priority:    str    # high / medium / low


def get_tier(followers: int) -> tuple[str, str]:
    if followers >= 1_000_000:
        return "kol", INFLUENCER_TIERS["kol"]["label"]
    elif followers >= 100_000:
        return "mid", INFLUENCER_TIERS["mid"]["label"]
    elif followers >= 10_000:
        return "koc", INFLUENCER_TIERS["koc"]["label"]
    else:
        return "nano", INFLUENCER_TIERS["nano"]["label"]


def score_influencer(
    influencer: dict,
    target_category: str = "",
) -> InfluencerScore:
    """对单个达人进行多维度评分"""

    platform  = influencer.get("platform", "tiktok")
    followers = int(influencer.get("followers", 0))
    avg_views = int(influencer.get("avg_views", 0))
    er        = float(influencer.get("avg_engagement", 0))
    gmv_30d   = float(influencer.get("gmv_30d", 0))
    category  = influencer.get("category", "")
    username  = influencer.get("username", "")
    inf_id    = influencer.get("influencer_id", "")

    tier_key, tier_label = get_tier(followers)

    # 1. 互动率评分（与平台基准比较）
    benchmark = PLATFORM_ER_BENCHMARK.get(platform, 3.0)
    er_ratio  = er / benchmark if benchmark > 0 else 0
    if er_ratio >= 3:
        er_score = 95
    elif er_ratio >= 2:
        er_score = 85
    elif er_ratio >= 1.5:
        er_score = 75
    elif er_ratio >= 1:
        er_score = 60
    elif er_ratio >= 0.5:
        er_score = 40
    else:
        er_score = 20

    # 2. GMV 带货力评分（TikTok 专用；其他平台无 GMV 数据时估算）
    if platform == "tiktok":
        if gmv_30d >= 100_000:
            gmv_score = 95
        elif gmv_30d >= 50_000:
            gmv_score = 85
        elif gmv_30d >= 10_000:
            gmv_score = 70
        elif gmv_30d >= 2_000:
            gmv_score = 50
        elif gmv_30d >= 500:
            gmv_score = 35
        else:
            gmv_score = 15
    else:
        # 非 TikTok 平台：用粉丝量 × 互动率估算
        gmv_score = min(95, er_score * 0.8 + min(followers / 20000, 20))

    # 3. 粉丝质量评分（基于 view/follower 比例）
    view_ratio = avg_views / max(followers, 1)
    if view_ratio >= 0.3:
        audience_score = 90
    elif view_ratio >= 0.15:
        audience_score = 75
    elif view_ratio >= 0.07:
        audience_score = 60
    elif view_ratio >= 0.03:
        audience_score = 45
    else:
        audience_score = 25

    # 4. 内容活跃度评分（从 performance 数据推断；无数据时用 er 代理）
    performance = influencer.get("performance", {})
    videos_30d  = int(performance.get("videos_30d", 0))
    if videos_30d >= 20:
        activity_score = 95
    elif videos_30d >= 12:
        activity_score = 80
    elif videos_30d >= 6:
        activity_score = 65
    elif videos_30d >= 2:
        activity_score = 50
    elif videos_30d > 0:
        activity_score = 35
    else:
        # 无活跃数据时用互动率代理
        activity_score = min(70, er_score * 0.7)

    # 5. 类目匹配加分（目标类目与达人类目相同时 +10）
    category_bonus = 10 if (
        target_category and category and
        target_category.lower() in category.lower()
    ) else 0

    # 综合加权评分
    ai_score = (
        er_score       * 0.30 +
        gmv_score      * 0.35 +
        audience_score * 0.20 +
        activity_score * 0.15 +
        category_bonus
    )
    ai_score = min(100, ai_score)

    has_email = bool(influencer.get("contact_email", "").strip())
    has_wa    = bool(influencer.get("contact_wa", "").strip())
    contact_available = has_email or has_wa

    comm_range = INFLUENCER_TIERS[tier_key]["commission_range"]
    recommended_commission = f"{comm_range[0]}%–{comm_range[1]}%"

    if ai_score >= 80:
        verdict  = "Highly Recommended — High Conversion Potential"
        priority = "high"
    elif ai_score >= 65:
        verdict  = "Recommended — Good ROI"
        priority = "high"
    elif ai_score >= 50:
        verdict  = "Neutral — Add to Watch List"
        priority = "medium"
    else:
        verdict  = "Not Recommended — Weak Sales Data"
        priority = "low"

    # 无联系方式降低优先级
    if not contact_available and priority == "high":
        priority = "medium"

    return InfluencerScore(
        influencer_id=inf_id,
        platform=platform,
        username=username,
        tier=tier_key,
        tier_label=tier_label,
        followers=followers,
        er_score=round(er_score, 1),
        gmv_score=round(gmv_score, 1),
        audience_score=round(audience_score, 1),
        activity_score=round(activity_score, 1),
        ai_score=round(ai_score, 1),
        contact_available=contact_available,
        recommended_commission=recommended_commission,
        verdict=verdict,
        outreach_priority=priority,
    )


def batch_score(
    influencers: list[dict],
    target_category: str = "",
    top_n: int = 20,
    min_score: float = 0,
) -> list[InfluencerScore]:
    """批量评分，按 AI 评分排序，返回 Top N"""
    scores = [score_influencer(inf, target_category) for inf in influencers]
    scores = [s for s in scores if s.ai_score >= min_score]
    scores.sort(key=lambda s: s.ai_score, reverse=True)
    return scores[:top_n]


def generate_outreach_brief(score: InfluencerScore, product_title: str = "") -> str:
    """生成达人招募简报（供 AI 生成话术时使用）"""
    lines = [
        f"Influencer: @{score.username} ({score.tier_label}, {score.followers:,} followers)",
        f"Platform: {score.platform.upper()}",
        f"AI Score: {score.ai_score} / 100 ({score.verdict})",
        f"Engagement: {score.er_score:.0f} | GMV: {score.gmv_score:.0f} | Audience Quality: {score.audience_score:.0f}",
        f"Recommended Commission: {score.recommended_commission}",
        f"Contact Available: {'Yes' if score.contact_available else 'Needs Research'}",
    ]
    if product_title:
        lines.append(f"Target Product: {product_title}")
    return "\n".join(lines)
