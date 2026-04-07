"""
Phase 1 — TikTok Crawler
Fetches: trending products / Shop GMV / viral videos / comment keywords
"""
from datetime import datetime

import httpx

from core.logger import logger
from core.tiktok_client import TikTokSigner


class TikTokCrawler:
    BASE = "https://open-api.tiktokglobalshop.com"

    def __init__(self):
        self._signer = TikTokSigner()

    async def _get(self, path: str, params: dict = None) -> dict:
        # 向 TikTok API 发送带签名的 GET 请求并返回 JSON 响应。
        signed = self._signer.sign(path, params or {})
        async with httpx.AsyncClient(timeout=30) as c:
            r = await c.get(f"{self.BASE}{path}", params=signed)
            return r.json()

    # ── 公开接口 ──────────────────────────────────────────────────────────
    async def get_trending_products(self, category_id: str = "", limit: int = 100) -> list[dict]:
        # 抓取 TikTok Shop 按销量排序的热卖商品列表。
        if settings.mock_mode:
            return _mock_trending_products(limit)
        data = await self._get("/api/products/search", {
            "sort_type": "SOLD_COUNT_DESC", "page_size": min(limit, 100),
            "category_id": category_id,
        })
        return data.get("data", {}).get("products", [])

    async def get_shop_gmv(self, start_date: str, end_date: str) -> dict:
        # 抓取指定日期区间的 TikTok 店铺 GMV 及订单数据。
        if settings.mock_mode:
            return _mock_gmv(start_date, end_date)
        data = await self._get("/api/shop/performance", {
            "start_date": start_date, "end_date": end_date,
            "metrics": "gmv,orders,units_sold,conversion_rate",
        })
        return data.get("data", {})

    async def get_viral_videos(self, keyword: str = "", limit: int = 50) -> list[dict]:
        # 通过 TikTok Creative Center API 抓取近期爆款视频列表。
        if settings.mock_mode:
            return _mock_viral_videos(limit)
        # Creative Center 趋势视频
        async with httpx.AsyncClient(timeout=30) as c:
            r = await c.get("https://ads.tiktok.com/creative_radar_api/v1/popular_trend/list", params={
                "period": 7, "page": 1, "limit": limit,
                "keyword": keyword, "region_code": "US",
            }, headers={"Access-Token": self.token})
            return r.json().get("data", {}).get("list", [])

    async def get_video_comments_keywords(self, video_id: str) -> list[dict]:
        # 抓取指定视频的评论高频关键词，需要 TikTok Research API 权限。
        if settings.mock_mode:
            return _mock_comment_keywords()
        data = await self._get(f"/api/research/video/{video_id}/comments", {"count": 200})
        comments = data.get("data", {}).get("comments", [])
        return _extract_keywords(comments)


# ── Mock 数据 ─────────────────────────────────────────────────────────────
def _mock_trending_products(limit: int) -> list[dict]:
    # 生成模拟的 TikTok 热卖商品数据，用于 mock 模式测试。
    import random
    categories = ["Beauty", "Electronics", "Home & Garden", "Fashion", "Sports", "Pet Supplies"]
    products = []
    for i in range(min(limit, 20)):
        cat = random.choice(categories)
        price = round(random.uniform(5, 150), 2)
        sold  = random.randint(500, 50000)
        products.append({
            "product_id":   f"TT_PROD_{i+1:04d}",
            "title":        f"[Mock] {cat} Best Seller Item #{i+1}",
            "category":     cat,
            "price":        price,
            "currency":     "USD",
            "sales_volume": sold,
            "gmv_estimate": round(price * sold * 0.7, 2),
            "rating":       round(random.uniform(3.8, 5.0), 1),
            "review_count": random.randint(100, 8000),
            "trend_score":  round(random.uniform(60, 99), 1),
            "platform":     "tiktok",
            "discovered_at": datetime.now().isoformat(),
        })
    products.sort(key=lambda x: x["trend_score"], reverse=True)
    return products


def _mock_gmv(start: str, end: str) -> dict:
    # 生成模拟的店铺 GMV 汇总数据。
    import random
    return {
        "gmv": round(random.uniform(10000, 200000), 2),
        "orders": random.randint(200, 5000),
        "units_sold": random.randint(300, 8000),
        "conversion_rate": round(random.uniform(2.0, 9.0), 2),
        "period": f"{start} ~ {end}",
    }


def _mock_viral_videos(limit: int) -> list[dict]:
    # 生成模拟的爆款视频列表数据。
    import random
    return [{
        "video_id":     f"VID_{i:05d}",
        "title":        f"Viral product review #{i+1}",
        "views":        random.randint(100000, 10000000),
        "likes":        random.randint(5000, 500000),
        "shares":       random.randint(1000, 100000),
        "author":       f"creator_{i:04d}",
        "author_followers": random.randint(10000, 5000000),
        "gmv_driven":   round(random.uniform(1000, 100000), 2),
        "product_tags": [f"tag_{j}" for j in range(random.randint(1, 4))],
    } for i in range(min(limit, 15))]


def _mock_comment_keywords() -> list[dict]:
    # 生成模拟的视频评论关键词列表。
    kws = ["good quality", "fast shipping", "love it", "recommend", "value for money",
           "amazing", "worth it", "packaging nice", "exactly as described", "repurchase"]
    import random
    return [{"keyword": k, "count": random.randint(10, 500), "sentiment": random.choice(["positive", "positive", "neutral"])} for k in kws]


def _extract_keywords(comments: list) -> list[dict]:
    # 从评论列表中提取高频词，过滤停用词后返回词频统计。
    from collections import Counter
    import re
    words = []
    for c in comments:
        text = c.get("text", "").lower()
        words.extend(re.findall(r'\b[a-z]{3,}\b', text))
    counter = Counter(words)
    stop = {"the", "and", "for", "this", "that", "with", "are", "was", "but", "not", "have"}
    return [{"keyword": w, "count": c} for w, c in counter.most_common(30) if w not in stop]
