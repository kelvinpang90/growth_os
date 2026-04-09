"""
Phase 1 — Shopee Crawler
Fetches: trending product list
Depends on: Shopee Open Platform API v2 (HMAC-SHA256 signing)
"""
import hashlib
import hmac
import random
import time
from datetime import datetime

import httpx

from core.config import settings
from core.logger import logger


class ShopeeCrawler:
    BASE = "https://partner.shopeemobile.com/api/v2"

    async def get_trending_products(self, limit: int = 50) -> list[dict]:
        # 通过 Shopee Open Platform API 抓取热销商品列表，使用 HMAC-SHA256 签名。
        if settings.mock_mode:
            return _mock_shopee_products(limit)
        try:
            ts         = int(time.time())
            partner_id = int(settings.shopee.partner_id)
            path       = "/product/get_item_list"
            base_str   = f"{partner_id}{path}{ts}"
            sign       = hmac.new(
                settings.shopee.partner_key.encode(),
                base_str.encode(),
                hashlib.sha256,
            ).hexdigest()

            async with httpx.AsyncClient(timeout=30) as c:
                r = await c.get(f"{self.BASE}{path}", params={
                    "partner_id":   partner_id,
                    "timestamp":    ts,
                    "sign":         sign,
                    "access_token": settings.shopee.access_token,
                    "shop_id":      settings.shopee.shop_id,
                    "offset":       0,
                    "page_size":    min(limit, 100),
                    "item_status":  "NORMAL",
                })
                r.raise_for_status()
                items = r.json().get("response", {}).get("item", [])
                return [_normalize_shopee(i) for i in items]
        except httpx.HTTPStatusError as e:
            logger.error(f"Shopee API 请求失败 (HTTP {e.response.status_code}): {e}")
            raise
        except Exception as e:
            logger.error(f"Shopee 抓取异常: {e}")
            raise

    async def get_item_detail(self, item_id: int, shop_id: int) -> dict:
        # 获取单个 Shopee 商品的详细信息。
        if settings.mock_mode:
            return {}
        try:
            ts         = int(time.time())
            partner_id = int(settings.shopee.partner_id)
            path       = "/product/get_item_base_info"
            base_str   = f"{partner_id}{path}{ts}"
            sign       = hmac.new(
                settings.shopee.partner_key.encode(),
                base_str.encode(),
                hashlib.sha256,
            ).hexdigest()

            async with httpx.AsyncClient(timeout=30) as c:
                r = await c.get(f"{self.BASE}{path}", params={
                    "partner_id":   partner_id,
                    "timestamp":    ts,
                    "sign":         sign,
                    "access_token": settings.shopee.access_token,
                    "shop_id":      shop_id,
                    "item_id_list": item_id,
                })
                r.raise_for_status()
                items = r.json().get("response", {}).get("item_list", [])
                return _normalize_shopee(items[0]) if items else {}
        except Exception as e:
            logger.error(f"Shopee 商品详情获取失败 item_id={item_id}: {e}")
            raise


# ── 数据标准化 ────────────────────────────────────────────────────────────
def _normalize_shopee(item: dict) -> dict:
    # 将 Shopee API 返回的商品字段标准化为内部统一格式（价格单位转换为 USD）。
    return {
        "product_id":   str(item.get("item_id", "")),
        "title":        item.get("item_name", ""),
        "price":        item.get("current_price", 0) / 100000,  # Shopee 价格单位为 1/100000
        "currency":     "USD",
        "sales_volume": item.get("sold", 0),
        "rating":       item.get("item_rating", {}).get("rating_star", 0),
        "review":       item.get("item_rating", {}).get("rating_count", [0])[-1]
                        if item.get("item_rating", {}).get("rating_count") else 0,
        "gmv_estimate": 0,
        "trend_score":  round(random.uniform(40, 90), 1),
        "platform":     "shopee",
        "discovered_at": datetime.now().isoformat(),
    }


# ── Mock 数据 ─────────────────────────────────────────────────────────────
def _mock_shopee_products(limit: int) -> list[dict]:
    # 生成模拟的 Shopee 热销商品数据，用于 mock 模式测试。
    cats = ["Health", "Beauty", "Home Living", "Women Clothes", "Men Clothes", "Electronics"]
    return [{
        "product_id":   f"SPE_{i+1:05d}",
        "title":        f"[Mock] Shopee {random.choice(cats)} Product #{i+1}",
        "category":     random.choice(cats),
        "price":        round(random.uniform(3, 80), 2),
        "currency":     "USD",
        "sales_volume": random.randint(100, 20000),
        "rating":       round(random.uniform(3.5, 5.0), 1),
        "review":       random.randint(20, 5000),
        "gmv_estimate": 0,
        "trend_score":  round(random.uniform(40, 90), 1),
        "platform":     "shopee",
        "discovered_at": datetime.now().isoformat(),
    } for i in range(min(limit, 20))]
