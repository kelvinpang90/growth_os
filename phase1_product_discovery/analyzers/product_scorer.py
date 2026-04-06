"""
Phase 1 — 利润率估算 + 商品综合评分模型
"""
from dataclasses import dataclass
from typing import Optional


# ── 平台费率配置 ──────────────────────────────────────────────────────────
PLATFORM_FEE = {
    "tiktok":  {"commission": 0.08, "fulfillment": 3.5,  "ads_ratio": 0.15},
    "shopee":  {"commission": 0.06, "fulfillment": 2.5,  "ads_ratio": 0.12},
    "lazada":  {"commission": 0.06, "fulfillment": 2.8,  "ads_ratio": 0.12},
    "amazon":  {"commission": 0.15, "fulfillment": 5.0,  "ads_ratio": 0.20},
    "shopify": {"commission": 0.02, "fulfillment": 4.0,  "ads_ratio": 0.18},
}


@dataclass
class ProfitResult:
    selling_price:  float
    cost_price:     float
    platform_fee:   float
    fulfillment:    float
    ads_cost:       float
    gross_profit:   float
    profit_rate:    float          # 百分比
    profit_grade:   str            # A/B/C/D
    recommendation: str


def estimate_profit(
    selling_price: float,
    cost_price: Optional[float] = None,
    platform: str = "tiktok",
    weight_kg: float = 0.3,
) -> ProfitResult:
    """
    估算商品利润率。
    cost_price 未知时，按行业均值（售价 30%）估算。
    """
    fees = PLATFORM_FEE.get(platform, PLATFORM_FEE["tiktok"])

    if cost_price is None:
        cost_price = selling_price * 0.30        # 默认采购成本 30%

    platform_fee  = selling_price * fees["commission"]
    fulfillment   = fees["fulfillment"] + weight_kg * 1.5
    ads_cost      = selling_price * fees["ads_ratio"]
    total_cost    = cost_price + platform_fee + fulfillment + ads_cost
    gross_profit  = selling_price - total_cost
    profit_rate   = (gross_profit / selling_price * 100) if selling_price > 0 else 0

    if profit_rate >= 40:
        grade, rec = "A", "利润优秀，强烈推荐"
    elif profit_rate >= 25:
        grade, rec = "B", "利润良好，建议推进"
    elif profit_rate >= 10:
        grade, rec = "C", "利润一般，需控成本"
    else:
        grade, rec = "D", "利润偏低，谨慎选品"

    return ProfitResult(
        selling_price=round(selling_price, 2),
        cost_price=round(cost_price, 2),
        platform_fee=round(platform_fee, 2),
        fulfillment=round(fulfillment, 2),
        ads_cost=round(ads_cost, 2),
        gross_profit=round(gross_profit, 2),
        profit_rate=round(profit_rate, 1),
        profit_grade=grade,
        recommendation=rec,
    )


# ── 商品综合评分模型 ──────────────────────────────────────────────────────
@dataclass
class ProductScore:
    product_id:     str
    platform:       str
    trend_score:    float          # 趋势热度
    profit_score:   float          # 利润潜力
    competition_score: float       # 竞争难度（越低越好）
    market_score:   float          # 市场容量
    ai_score:       float          # 综合 AI 评分
    competition:    str            # low / medium / high
    market_size:    str            # small / medium / large / huge
    verdict:        str


def score_product(product: dict, profit_result: Optional[ProfitResult] = None) -> ProductScore:
    """对单个商品进行多维度打分，输出 AI 综合评分"""

    # 1. 趋势分（已有）
    trend = float(product.get("trend_score", 50))

    # 2. 利润分
    if profit_result:
        profit_score = min(100, profit_result.profit_rate * 2)
    else:
        price = float(product.get("price", 30))
        p = estimate_profit(price, platform=product.get("platform", "tiktok"))
        profit_score = min(100, p.profit_rate * 2)

    # 3. 竞争度分（review_count 反映竞争激烈程度）
    reviews = int(product.get("review_count", 0))
    if reviews < 200:
        comp_score, competition = 90, "low"
    elif reviews < 2000:
        comp_score, competition = 65, "medium"
    elif reviews < 10000:
        comp_score, competition = 35, "high"
    else:
        comp_score, competition = 15, "very_high"

    # 4. 市场容量分（sales_volume）
    sales = int(product.get("sales_volume", 0))
    if sales > 20000:
        market_score, market_size = 95, "huge"
    elif sales > 5000:
        market_score, market_size = 80, "large"
    elif sales > 1000:
        market_score, market_size = 60, "medium"
    else:
        market_score, market_size = 35, "small"

    # 综合加权评分
    ai_score = (
        trend        * 0.35 +
        profit_score * 0.30 +
        comp_score   * 0.20 +
        market_score * 0.15
    )

    if ai_score >= 80:
        verdict = "强烈推荐 — 高潜力爆品"
    elif ai_score >= 65:
        verdict = "推荐 — 有较好机会"
    elif ai_score >= 50:
        verdict = "一般 — 可继续观察"
    else:
        verdict = "不推荐 — 竞争大或利润低"

    return ProductScore(
        product_id=product.get("product_id", ""),
        platform=product.get("platform", ""),
        trend_score=round(trend, 1),
        profit_score=round(profit_score, 1),
        competition_score=round(comp_score, 1),
        market_score=round(market_score, 1),
        ai_score=round(ai_score, 1),
        competition=competition,
        market_size=market_size,
        verdict=verdict,
    )


def batch_score(products: list[dict], platform: str = "tiktok", top_n: int = 20) -> list[ProductScore]:
    """批量评分，返回 Top N"""
    scores = [score_product({**p, "platform": platform}) for p in products]
    scores.sort(key=lambda s: s.ai_score, reverse=True)
    return scores[:top_n]
