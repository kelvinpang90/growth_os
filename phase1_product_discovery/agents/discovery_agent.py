"""
Phase 1 — AI 选品决策 Agent
输入：多平台抓取数据 → 输出：推荐商品 + 完整起盘方案
"""
import json
from dataclasses import asdict
from datetime import datetime

from core.base_agent import BaseAgent, _load_prompt
from core.database import execute, fetchall
from core.logger import logger
from phase1_product_discovery.analyzers.product_scorer import (
    batch_score, estimate_profit, score_product,
)
from phase1_product_discovery.crawlers.tiktok_crawler        import TikTokCrawler
from phase1_product_discovery.crawlers.amazon_crawler        import AmazonCrawler
from phase1_product_discovery.crawlers.shopee_crawler        import ShopeeCrawler
from phase1_product_discovery.crawlers.google_trends_crawler import GoogleTrendsCrawler

# ── Tool Schemas ──────────────────────────────────────────────────────────
_TOOLS = [
    {
        "name": "fetch_trending_data",
        "description": "从各平台抓取当日热销商品和趋势数据",
        "input_schema": {
            "type": "object",
            "properties": {
                "platforms": {
                    "type": "array",
                    "items": {"type": "string", "enum": ["tiktok", "amazon", "shopee", "google"]},
                    "description": "要抓取的平台列表",
                    "default": ["tiktok", "amazon", "shopee", "google"]
                },
                "category": {"type": "string", "description": "商品类目", "default": ""},
                "limit_per_platform": {"type": "integer", "default": 30}
            },
            "required": []
        }
    },
    {
        "name": "score_and_filter_products",
        "description": "对抓取的商品进行多维度评分，筛选出高潜力商品",
        "input_schema": {
            "type": "object",
            "properties": {
                "products": {"type": "array", "description": "商品列表"},
                "top_n": {"type": "integer", "description": "返回 Top N", "default": 10},
                "min_score": {"type": "number", "description": "最低 AI 评分门槛", "default": 60}
            },
            "required": ["products"]
        }
    },
    {
        "name": "calculate_profit",
        "description": "估算某商品在各平台的利润率",
        "input_schema": {
            "type": "object",
            "properties": {
                "selling_price": {"type": "number", "description": "预计售价（USD）"},
                "cost_price":    {"type": "number", "description": "采购成本（USD）"},
                "platform":      {"type": "string", "default": "tiktok"},
                "weight_kg":     {"type": "number", "default": 0.3}
            },
            "required": ["selling_price"]
        }
    },
    {
        "name": "save_recommendations",
        "description": "将 AI 推荐商品和起盘方案保存到数据库",
        "input_schema": {
            "type": "object",
            "properties": {
                "recommendations": {
                    "type": "array",
                    "description": "推荐商品列表，含完整分析",
                    "items": {"type": "object"}
                }
            },
            "required": ["recommendations"]
        }
    },
    {
        "name": "get_historical_recommendations",
        "description": "查询历史推荐记录，避免重复推荐",
        "input_schema": {
            "type": "object",
            "properties": {
                "days": {"type": "integer", "description": "查询最近 N 天", "default": 7}
            },
            "required": []
        }
    }
]


class DiscoveryAgent(BaseAgent):

    @property
    def system_prompt(self) -> str:
        return _load_prompt("discovery_system").format(
            date=datetime.now().strftime('%Y-%m-%d')
        )

    @property
    def tools(self) -> list[dict]:
        return _TOOLS

    async def dispatch_tool(self, name: str, params: dict):
        if name == "fetch_trending_data":
            return await self._fetch_trending(params)
        elif name == "score_and_filter_products":
            return self._score_filter(params)
        elif name == "calculate_profit":
            return self._calc_profit(params)
        elif name == "save_recommendations":
            return await self._save_recs(params)
        elif name == "get_historical_recommendations":
            return await self._get_history(params)
        return {"error": f"未知工具: {name}"}

    # ── Tool 实现 ──────────────────────────────────────────────────────────
    async def _fetch_trending(self, params: dict) -> dict:
        platforms = params.get("platforms", ["tiktok", "amazon", "shopee", "google"])
        limit     = params.get("limit_per_platform", 30)
        category  = params.get("category", "")
        all_products, keywords = [], []

        for platform in platforms:
            try:
                if platform == "tiktok":
                    tt       = TikTokCrawler()
                    products = await tt.get_trending_products(category, limit)
                    videos   = await tt.get_viral_videos(limit=20)
                    all_products.extend(products)
                    logger.info(f"TikTok: {len(products)} 商品, {len(videos)} 爆款视频")

                elif platform == "amazon":
                    products = await AmazonCrawler().get_bsr_products(category or "beauty", limit)
                    all_products.extend(products)
                    logger.info(f"Amazon: {len(products)} 商品")

                elif platform == "shopee":
                    products = await ShopeeCrawler().get_trending_products(limit)
                    all_products.extend(products)
                    logger.info(f"Shopee: {len(products)} 商品")

                elif platform == "google":
                    kws = await GoogleTrendsCrawler().get_trending_keywords()
                    keywords.extend(kws)
                    logger.info(f"Google Trends: {len(kws)} 关键词")

            except Exception as e:
                logger.error(f"{platform} 抓取出错: {e}")

        return {
            "total_products": len(all_products),
            "platforms": platforms,
            "products": all_products[:100],          # 限制传给 Claude 的数量
            "trending_keywords": keywords[:20],
            "fetched_at": datetime.now().isoformat(),
        }

    def _score_filter(self, params: dict) -> dict:
        products  = params.get("products", [])
        top_n     = params.get("top_n", 10)
        min_score = params.get("min_score", 60)

        scored = batch_score(products, top_n=len(products))
        filtered = [s for s in scored if s.ai_score >= min_score][:top_n]

        results = []
        for s in filtered:
            original = next((p for p in products if p.get("product_id") == s.product_id), {})
            results.append({
                **asdict(s),
                "title":        original.get("title", ""),
                "price":        original.get("price", 0),
                "sales_volume": original.get("sales_volume", 0),
                "rating":       original.get("rating", 0),
                "review_count": original.get("review_count", 0),
            })

        return {
            "total_scored":    len(scored),
            "qualified_count": len(filtered),
            "top_products":    results,
        }

    def _calc_profit(self, params: dict) -> dict:
        result = estimate_profit(
            selling_price=params["selling_price"],
            cost_price=params.get("cost_price"),
            platform=params.get("platform", "tiktok"),
            weight_kg=params.get("weight_kg", 0.3),
        )
        return asdict(result)

    async def _save_recs(self, params: dict) -> dict:
        recs   = params.get("recommendations", [])
        saved  = 0
        for rec in recs:
            try:
                # upsert discovered_products
                await execute("""
                    INSERT INTO discovered_products
                        (platform, product_id, title, category, price, sales_volume,
                         gmv_estimate, rating, review_count, trend_score, profit_rate,
                         competition, ai_score, ai_analysis)
                    VALUES
                        (:platform, :pid, :title, :cat, :price, :sales, :gmv,
                         :rating, :reviews, :trend, :profit, :comp, :ai_score, :analysis)
                    ON DUPLICATE KEY UPDATE
                        ai_score=VALUES(ai_score), ai_analysis=VALUES(ai_analysis),
                        trend_score=VALUES(trend_score), updated_at=CURRENT_TIMESTAMP
                """, {
                    "platform": rec.get("platform", "tiktok"),
                    "pid":      rec.get("product_id", ""),
                    "title":    rec.get("title", "")[:500],
                    "cat":      rec.get("category", ""),
                    "price":    rec.get("price", 0),
                    "sales":    rec.get("sales_volume", 0),
                    "gmv":      rec.get("gmv_estimate", 0),
                    "rating":   rec.get("rating", 0),
                    "reviews":  rec.get("review_count", 0),
                    "trend":    rec.get("trend_score", 0),
                    "profit":   rec.get("profit_rate", 0),
                    "comp":     rec.get("competition", "medium"),
                    "ai_score": rec.get("ai_score", 0),
                    "analysis": json.dumps(rec.get("launch_plan", {}), ensure_ascii=False),
                })
                saved += 1
            except Exception as e:
                logger.error(f"保存推荐商品失败: {e}")

        return {"saved": saved, "total": len(recs)}

    async def _get_history(self, params: dict) -> dict:
        days = params.get("days", 7)
        rows = await fetchall("""
            SELECT product_id, title, platform, ai_score, discovered_at
            FROM discovered_products
            WHERE discovered_at >= DATE_SUB(NOW(), INTERVAL :days DAY)
            ORDER BY ai_score DESC LIMIT 50
        """, {"days": days})
        return {"count": len(rows), "products": rows}

    # ── 便捷入口 ──────────────────────────────────────────────────────────
    async def run_daily_discovery(self) -> str:
        """每日选品任务入口"""
        logger.info("开始每日 AI 选品分析...")
        return await self.run(
            "请立即执行今日选品分析：\n"
            "1. 抓取 TikTok/Amazon/Shopee/Google 今日趋势数据\n"
            "2. 对所有商品评分，筛选 AI 评分 ≥ 65 的商品\n"
            "3. 为 Top 10 商品计算利润率并生成完整起盘方案\n"
            "4. 保存到数据库\n"
            "5. 输出今日推荐报告",
            fresh=True
        )
