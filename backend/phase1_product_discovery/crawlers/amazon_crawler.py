"""
Phase 1 — Amazon BSR Crawler
Fetches: Best Seller Rank products / new releases
Depends on: Rainforest API (https://www.rainforestapi.com)
"""
import random
from datetime import datetime

import httpx

from core.config import settings
from core.logger import logger


class AmazonCrawler:
    """Amazon Best Seller Rank + trending products crawler."""

    BSR_CATEGORIES = {
        "beauty":      "11055981",
        "electronics": "172282",
        "home":        "1055398",
        "sports":      "3375251",
        "toys":        "165793011",
        "pet":         "2619533011",
    }

    async def get_bsr_products(self, category: str = "beauty", limit: int = 50) -> list[dict]:
        # 通过 Rainforest API 抓取指定类目的 Amazon BSR 热销商品列表。
        if settings.mock_mode:
            return _mock_amazon_products(category, limit)
        try:
            async with httpx.AsyncClient(timeout=30) as c:
                r = await c.get("https://api.rainforestapi.com/request", params={
                    "api_key":       settings.amazon.access_key,
                    "type":          "bestsellers",
                    "amazon_domain": "amazon.com",
                    "category_id":   self.BSR_CATEGORIES.get(category, "11055981"),
                    "output":        "json",
                })
                r.raise_for_status()
                items = r.json().get("bestsellers", [])
                return [_normalize_amazon(item) for item in items[:limit]]
        except httpx.HTTPStatusError as e:
            logger.error(f"Amazon BSR 请求失败 (HTTP {e.response.status_code}) category={category}: {e}")
            raise
        except Exception as e:
            logger.error(f"Amazon BSR 抓取异常 category={category}: {e}")
            raise

    async def get_new_releases(self, category: str = "beauty", limit: int = 20) -> list[dict]:
        # 抓取 Amazon 指定类目的新品榜单。
        if settings.mock_mode:
            return _mock_amazon_products(category, limit)
        try:
            async with httpx.AsyncClient(timeout=30) as c:
                r = await c.get("https://api.rainforestapi.com/request", params={
                    "api_key":       settings.amazon.access_key,
                    "type":          "new_releases",
                    "amazon_domain": "amazon.com",
                    "category_id":   self.BSR_CATEGORIES.get(category, "11055981"),
                })
                r.raise_for_status()
                return [_normalize_amazon(i) for i in r.json().get("new_releases", [])[:limit]]
        except httpx.HTTPStatusError as e:
            logger.error(f"Amazon 新品榜请求失败 (HTTP {e.response.status_code}) category={category}: {e}")
            raise
        except Exception as e:
            logger.error(f"Amazon 新品榜抓取异常 category={category}: {e}")
            raise


# ── 数据标准化 ────────────────────────────────────────────────────────────
def _normalize_amazon(item: dict) -> dict:
    # 将 Rainforest API 返回的商品字段标准化为内部统一格式。
    return {
        "product_id":   item.get("asin", ""),
        "title":        item.get("title", ""),
        "price":        item.get("price", {}).get("value", 0),
        "currency":     "USD",
        "rating":       item.get("rating", 0),
        "review":       item.get("ratings_total", 0),
        "bsr_rank":     item.get("rank", 0),
        "sales_volume": 0,                                  # BSR API 无直接销量，由 rank 推算
        "gmv_estimate": 0,
        "trend_score":  max(0, 100 - item.get("rank", 100)),
        "platform":     "amazon",
        "image":        item.get("image", ""),
        "discovered_at": datetime.now().isoformat(),
    }


# ── Mock 数据 ─────────────────────────────────────────────────────────────
def _mock_amazon_products(category: str, limit: int) -> list[dict]:
    # 生成模拟的 Amazon 热销商品数据，用于 mock 模式测试。
    products = []
    for i in range(min(limit, 20)):
        price = round(random.uniform(8, 200), 2)
        sold  = random.randint(200, 30000)
        products.append({
            "product_id":   f"AMZ_{category.upper()}_{i+1:04d}",
            "title":        f"[Mock] Amazon {category.title()} Best Seller #{i+1}",
            "category":     category,
            "price":        price,
            "currency":     "USD",
            "sales_volume": sold,
            "gmv_estimate": round(price * sold * 0.6, 2),
            "rating":       round(random.uniform(3.5, 5.0), 1),
            "review":       random.randint(50, 20000),
            "bsr_rank":     i + 1,
            "trend_score":  round(random.uniform(50, 95), 1),
            "platform":     "amazon",
            "discovered_at": datetime.now().isoformat(),
        })
    return products
